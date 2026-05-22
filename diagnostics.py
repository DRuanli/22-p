"""
DGP Diagnostics
================

Validation utilities for synthetic data quality:
    - Positivity / overlap checks
    - Varsortability check (Reisach et al. 2021)
    - ICC verification for hierarchical DGPs
    - Ground truth recovery via oracle estimation
    - Visualization helpers

These diagnostics should be run BEFORE using synthetic data for benchmarking.
A failing diagnostic indicates the DGP may not stress-test the algorithm
as intended.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestRegressor

# Import from sibling module
try:
    from .dgp import SyntheticData, BaseDGP
except ImportError:
    from dgp import SyntheticData, BaseDGP


# =========================================================================
# CORE DIAGNOSTIC CHECKS
# =========================================================================

def check_positivity(
    data: SyntheticData,
    threshold: float = 0.05,
    verbose: bool = True
) -> Dict[str, any]:
    """Check positivity (overlap) of protected attribute.
    
    Positivity requires P(A=1 | X, S) ∈ (threshold, 1-threshold) for all units.
    Violations indicate certain (X, S) combinations have no counterfactuals.
    
    Returns
    -------
    dict with keys: 'pass', 'min_prop', 'max_prop', 'violations_pct'
    """
    # Estimate P(A | X, S) using simple logistic
    valid = ~np.isnan(data.A) if data.A.dtype == float else np.ones(len(data.A), dtype=bool)
    
    if valid.sum() < 100:
        return {'pass': False, 'reason': 'Too few observed A values'}
    
    # Include cluster as feature
    X_with_S = np.column_stack([data.X[valid], data.S[valid].reshape(-1, 1)])
    A_obs = data.A[valid].astype(int)
    
    if len(np.unique(A_obs)) < 2:
        return {'pass': False, 'reason': 'No variation in A'}
    
    lr = LogisticRegression(max_iter=500, C=1.0)
    lr.fit(X_with_S, A_obs)
    p_hat = lr.predict_proba(X_with_S)[:, 1]
    
    violations = (p_hat < threshold) | (p_hat > 1 - threshold)
    pct_violations = violations.mean()
    
    result = {
        'pass': pct_violations < 0.05,
        'min_prop': float(p_hat.min()),
        'max_prop': float(p_hat.max()),
        'mean_prop': float(p_hat.mean()),
        'violations_pct': float(pct_violations),
        'threshold': threshold,
    }
    
    if verbose:
        print(f"\n=== Positivity Check ===")
        print(f"  P(A=1|X,S) range: [{result['min_prop']:.3f}, {result['max_prop']:.3f}]")
        print(f"  Violations (prop. outside [{threshold}, {1-threshold}]): "
              f"{result['violations_pct']:.2%}")
        print(f"  Status: {'✓ PASS' if result['pass'] else '✗ FAIL'}")
    
    return result


def check_varsortability(
    data: SyntheticData,
    verbose: bool = True
) -> Dict[str, any]:
    """Check varsortability (Reisach et al. 2021).
    
    In ANM-generated data, ordering nodes by marginal variance often
    matches the causal ordering — a confound that can make causal
    discovery look spuriously good.
    
    We assess: does marginal variance order match expected causal order
    (X → A → M → Y)?
    
    Returns
    -------
    dict with 'varsortability_score' ∈ [0, 1]:
        - 0.5 = random (good)
        - 1.0 = perfect varsortability (bad — indicates artifact)
    """
    # Aggregate features in expected causal order
    # X precedes A precedes M precedes Y
    var_X = data.X.var(axis=0).mean()  # Average X variance
    var_A = data.A[~np.isnan(data.A)].var() if data.A.dtype == float else data.A.var()
    var_M = data.M.var(axis=0).mean()
    var_Y = data.Y.var()
    
    # Check pairwise ordering matches causal order
    pairs_correct = 0
    pairs_total = 0
    
    # Expected: var_X < var_A < var_M < var_Y is NOT required for correctness,
    # but if it perfectly matches, that's varsortability.
    # We check if marginal variance is informative about causal position.
    
    ordering = [('X', var_X), ('A', var_A), ('M', var_M), ('Y', var_Y)]
    
    # For each pair, does the downstream variable have higher variance?
    for i in range(len(ordering)):
        for j in range(i+1, len(ordering)):
            pairs_total += 1
            if ordering[j][1] > ordering[i][1]:
                pairs_correct += 1
    
    varsort_score = pairs_correct / pairs_total
    
    # Score interpretation:
    # > 0.85 = strong varsortability (problematic)
    # 0.6-0.85 = moderate (acceptable for our purpose, since we test estimation not discovery)
    # < 0.6 = low (good — variance not informative about causal order)
    
    result = {
        'varsortability_score': varsort_score,
        'variances': {'X': var_X, 'A': var_A, 'M': var_M, 'Y': var_Y},
        'pass': varsort_score < 0.85,
        'interpretation': (
            'High' if varsort_score > 0.85 else
            'Moderate' if varsort_score > 0.6 else
            'Low'
        )
    }
    
    if verbose:
        print(f"\n=== Varsortability Check (Reisach et al. 2021) ===")
        print(f"  Variances: X={var_X:.3f}, A={var_A:.3f}, M={var_M:.3f}, Y={var_Y:.3f}")
        print(f"  Varsortability score: {varsort_score:.2f}")
        print(f"  Interpretation: {result['interpretation']}")
        if not result['pass']:
            print(f"  ⚠ High varsortability — consider further standardization")
    
    return result


def check_icc(
    data: SyntheticData,
    expected_icc: Optional[float] = None,
    verbose: bool = True
) -> Dict[str, any]:
    """Check intra-class correlation coefficient (ICC) for hierarchical data.
    
    ICC = σ²_between / (σ²_between + σ²_within)
    
    For HC-DML to be necessary (vs single-level DML), ICC should be ≥ 0.05.
    """
    if data.n_clusters <= 1:
        return {'pass': True, 'icc': 0.0, 'note': 'Single cluster, ICC not applicable'}
    
    # Compute ICC via ANOVA decomposition
    df = pd.DataFrame({'Y': data.Y, 'S': data.S})
    cluster_means = df.groupby('S')['Y'].mean()
    grand_mean = df['Y'].mean()
    
    # Between-cluster variance
    cluster_sizes = df.groupby('S').size()
    ss_between = (cluster_sizes * (cluster_means - grand_mean)**2).sum()
    df_between = data.n_clusters - 1
    ms_between = ss_between / df_between
    
    # Within-cluster variance
    ss_within = sum(
        ((df[df['S'] == s]['Y'] - cluster_means[s])**2).sum()
        for s in df['S'].unique()
    )
    df_within = data.n - data.n_clusters
    ms_within = ss_within / df_within
    
    # ICC formula (one-way random effects)
    # Use harmonic mean of cluster sizes for unbalanced
    n_harmonic = stats.hmean(cluster_sizes)
    icc = (ms_between - ms_within) / (ms_between + (n_harmonic - 1) * ms_within)
    icc = max(0.0, icc)  # Clip negative ICC to 0
    
    result = {
        'icc': float(icc),
        'ms_between': float(ms_between),
        'ms_within': float(ms_within),
        'n_clusters': data.n_clusters,
        'n_harmonic': float(n_harmonic),
    }
    
    if expected_icc is not None:
        result['expected_icc'] = expected_icc
        result['icc_recovery_error'] = abs(icc - expected_icc)
        result['pass'] = abs(icc - expected_icc) < 0.05
    else:
        result['pass'] = icc >= 0.05
    
    if verbose:
        print(f"\n=== ICC Check ===")
        print(f"  Estimated ICC: {icc:.3f}")
        if expected_icc is not None:
            print(f"  Expected ICC:  {expected_icc:.3f}")
            print(f"  Error:         {result['icc_recovery_error']:.3f}")
        print(f"  Status: {'✓ PASS' if result['pass'] else '✗ FAIL'}")
    
    return result


def check_cluster_balance(
    data: SyntheticData,
    verbose: bool = True
) -> Dict[str, any]:
    """Check cluster size balance.
    
    Highly unbalanced clusters cause variance issues in HC-DML.
    """
    sizes = pd.Series(data.S).value_counts()
    
    result = {
        'n_clusters': len(sizes),
        'min_size': int(sizes.min()),
        'max_size': int(sizes.max()),
        'mean_size': float(sizes.mean()),
        'median_size': float(sizes.median()),
        'imbalance_ratio': float(sizes.max() / sizes.min()),
        'pass': (sizes.min() >= 5) and (sizes.max() / sizes.min() <= 10),
    }
    
    if verbose:
        print(f"\n=== Cluster Balance Check ===")
        print(f"  N clusters: {result['n_clusters']}")
        print(f"  Sizes: min={result['min_size']}, max={result['max_size']}, "
              f"median={result['median_size']:.0f}")
        print(f"  Imbalance ratio: {result['imbalance_ratio']:.2f}x")
        print(f"  Status: {'✓ PASS' if result['pass'] else '✗ WARN'}")
    
    return result


def check_missingness(
    data: SyntheticData,
    verbose: bool = True
) -> Dict[str, any]:
    """Check missingness pattern in A.
    
    Tests:
        1. Marginal missing rate
        2. MAR assumption: A ⊥ R | X (informal check via partial correlation)
    """
    if data.R is None:
        return {'pass': True, 'note': 'No missingness in this DGP'}
    
    missing_rate = 1 - data.R.mean()
    
    # MAR ASSESSMENT (informational only; cannot definitively test MAR)
    # Full MAR test impossible without external validation or MNAR sensitivity.
    
    valid_A = ~np.isnan(data.A) if data.A.dtype == float else np.ones(len(data.A), dtype=bool)
    
    if valid_A.sum() < 100:
        return {'pass': False, 'reason': 'Too few observed A'}
    
    # Diagnostic 1: How well do observed covariates (X, Z) predict R?
    features_R = data.X if data.Z is None else np.column_stack([data.X, data.Z])
    
    lr_R = LogisticRegression(max_iter=500).fit(features_R, data.R)
    r_prediction_acc = lr_R.score(features_R, data.R)
    
    # Diagnostic 2: Standardized mean differences in X between R=1 and R=0
    smd_results = []
    for j in range(data.X.shape[1]):
        x_R1 = data.X[data.R == 1, j]
        x_R0 = data.X[data.R == 0, j]
        if len(x_R0) > 0 and len(x_R1) > 0:
            mean_diff = x_R1.mean() - x_R0.mean()
            pooled_sd = np.sqrt(0.5 * (x_R1.var() + x_R0.var()))
            if pooled_sd > 1e-6:
                smd_results.append(abs(mean_diff) / pooled_sd)
    
    max_smd = max(smd_results) if smd_results else 0.0
    mean_smd = float(np.mean(smd_results)) if smd_results else 0.0
    
    result = {
        'missing_rate': float(missing_rate),
        'r_prediction_accuracy': float(r_prediction_acc),
        'max_smd_X': float(max_smd),
        'mean_smd_X': float(mean_smd),
        'note': 'MAR cannot be directly tested; rely on substantive knowledge',
        'pass': True,  # Informational diagnostic
    }
    
    if verbose:
        print(f"\n=== Missingness Check ===")
        print(f"  Missing rate in A: {missing_rate:.2%}")
        print(f"  R predictable by (X,Z): {r_prediction_acc:.3f} accuracy")
        print(f"  Max SMD in X between R=1/R=0: {max_smd:.3f}")
        print(f"  Mean SMD in X: {mean_smd:.3f}")
        print(f"  Note: MAR requires substantive justification, not just data check")
    
    return result


# =========================================================================
# GROUND TRUTH RECOVERY VIA ORACLE
# =========================================================================

def oracle_path_specific_effects(
    data: SyntheticData,
    dgp: BaseDGP,
    use_unobserved_U: bool = True,
    n_mc: int = 50_000,
    verbose: bool = True
) -> Dict[str, float]:
    """Recover path-specific effects via oracle estimation.
    
    Uses the TRUE DGP knowledge (including U if present) to estimate
    path-specific effects via plug-in estimator. This provides a
    "best possible" benchmark to compare against HC-DML.
    
    Should match the analytical/MC ground truth from dgp.true_pj_cf().
    """
    # Compute ground truth for default psi (all paths unjustified)
    truth = dgp.true_pj_cf(psi={'direct': 0.0, 'via_M': 0.0}, n_mc=n_mc)
    
    # Oracle estimation: fit perfect outcome model with U if available
    if use_unobserved_U and data.U is not None:
        features = np.column_stack([data.X, data.M, data.U.reshape(-1, 1)])
    else:
        features = np.column_stack([data.X, data.M])
    
    valid_A = ~np.isnan(data.A) if data.A.dtype == float else np.ones(len(data.A), dtype=bool)
    
    # Fit Y ~ X + A + M (+ U)
    full_features = np.column_stack([features[valid_A], data.A[valid_A].reshape(-1, 1)])
    oracle_lr = LinearRegression().fit(full_features, data.Y[valid_A])
    
    # Recover alpha_A as last coefficient
    recovered_alpha_A = oracle_lr.coef_[-1]
    
    result = {
        'truth': truth,
        'oracle_recovered_alpha_A': float(recovered_alpha_A),
        'true_alpha_A': float(getattr(dgp, 'alpha_A', np.nan)),
        'recovery_error': float(abs(recovered_alpha_A - getattr(dgp, 'alpha_A', 0))),
    }
    
    if verbose:
        print(f"\n=== Oracle Ground Truth Recovery ===")
        print(f"  True PSE_direct (α_A):       {result['true_alpha_A']:.4f}")
        print(f"  Oracle recovered:             {result['oracle_recovered_alpha_A']:.4f}")
        print(f"  Recovery error:               {result['recovery_error']:.4f}")
        print(f"  True PSE_via_M:               {truth['PSE_via_M']:.4f}")
    
    return result


# =========================================================================
# FULL DIAGNOSTIC SUITE
# =========================================================================

def run_full_diagnostics(
    data: SyntheticData,
    dgp: Optional[BaseDGP] = None,
    verbose: bool = True
) -> Dict[str, Dict]:
    """Run complete diagnostic suite on synthetic data.
    
    Returns dictionary of all diagnostic results.
    """
    if verbose:
        print("=" * 60)
        print(f"DIAGNOSTIC SUITE for {data.metadata.get('dgp_name', 'Unknown DGP')}")
        print(f"n = {data.n}, n_clusters = {data.n_clusters}")
        print("=" * 60)
    
    results = {
        'positivity': check_positivity(data, verbose=verbose),
        'varsortability': check_varsortability(data, verbose=verbose),
        'cluster_balance': check_cluster_balance(data, verbose=verbose),
    }
    
    # ICC if hierarchical
    if data.n_clusters > 1:
        expected_icc = data.metadata.get('icc')
        results['icc'] = check_icc(data, expected_icc, verbose=verbose)
    
    # Missingness if applicable
    if data.R is not None and data.R.mean() < 1.0:
        results['missingness'] = check_missingness(data, verbose=verbose)
    
    # Oracle recovery if DGP provided
    if dgp is not None:
        results['oracle'] = oracle_path_specific_effects(data, dgp, verbose=verbose)
    
    # Summary
    n_pass = sum(1 for r in results.values() if r.get('pass', True))
    n_total = len(results)
    
    if verbose:
        print("\n" + "=" * 60)
        print(f"SUMMARY: {n_pass}/{n_total} diagnostics passed")
        print("=" * 60)
    
    return results


__all__ = [
    'check_positivity',
    'check_varsortability',
    'check_icc',
    'check_cluster_balance',
    'check_missingness',
    'oracle_path_specific_effects',
    'run_full_diagnostics',
]
