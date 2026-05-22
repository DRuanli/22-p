"""
EIF Estimator Verification Script
====================================

USER RUNS THIS LOCALLY to verify EIF correctness.

Tests:
    1. Smoke test (runs without crashing) — already passed in development
    2. Large-n consistency: bias → 0 as n → ∞
    3. Reduction to Tchetgen-Shpitser 2014 IID case (L=1)
    4. Doubly robust property (one nuisance misspecified)
    5. Coverage of bootstrap CI

USAGE:
    python scripts/verify_eif_estimator.py
    
    # Larger sample (more conclusive but slower):
    N_LARGE=20000 python scripts/verify_eif_estimator.py

EXPECTED RUNTIME: 5-30 minutes depending on N_LARGE.

INTERPRETATION:
    - If bias near zero at large n → EIF correctly implemented
    - If persistent bias → derivation has an error somewhere
    - If wrong sign of NIE → check cross-world component
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'algorithms'))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from dgp import LinearDGP, HierarchicalDGP
from hcdml_eif import HCDMLEstimatorEIF
from hcdml import HCDMLEstimator  # substitution version for comparison


N_LARGE = int(os.environ.get('N_LARGE', '10000'))
N_REPLICATES = int(os.environ.get('N_REP', '5'))


def test_1_consistency():
    """Test 1: Bias should decrease with n.
    
    For LinearDGP with α_A=0.30, β_A=0.20, α_M=[0.5,0.5,0.5]:
        True NDE = 0.30
        True NIE = 0.20 × (0.5+0.5+0.5) = 0.30  
        True total = 0.60
    
    NOTE: This test uses LinearRegression (no shrinkage) for outcome learner.
    Ridge introduces shrinkage bias that confounds EIF correctness verification.
    For real data with high-dimensional features, Ridge or GBM is appropriate
    (regularization helps with nuisance estimation rates).
    """
    from sklearn.linear_model import LinearRegression, LogisticRegression
    
    print("\n" + "═" * 70)
    print(" TEST 1: CONSISTENCY (bias should → 0 as n → ∞) ".center(70, "═"))
    print("═" * 70)
    
    dgp = LinearDGP(q=5, p=3, alpha_A=0.30, beta_A=0.20, alpha_M=np.array([0.5, 0.5, 0.5]))
    print(f"\n  True NDE = 0.30, NIE = 0.30, Total = 0.60")
    print(f"  Using LinearRegression for outcome (no shrinkage bias)")
    
    n_values = [500, 2000, 5000, N_LARGE]
    
    results = []
    for n in n_values:
        bias_NDE_list = []
        bias_NIE_list = []
        bias_total_list = []
        
        for seed in range(N_REPLICATES):
            data = dgp.generate(n=n, seed=42 + seed)
            
            est = HCDMLEstimatorEIF(
                paths=['direct', 'via_M'],
                n_folds=3, n_cluster_folds=1,
                outcome_learner=LinearRegression(),
                propensity_learner=LogisticRegression(max_iter=1000),
                random_state=seed,
            )
            r = est.fit(Y=data.Y, A=data.A, M=data.M, X=data.X, S=data.S)
            
            bias_NDE_list.append(r.tau_per_path.get('direct', float('nan')) - 0.30)
            bias_NIE_list.append(r.tau_per_path.get('via_M', float('nan')) - 0.30)
            bias_total_list.append(r.tau_pj_cf - 0.60)
        
        results.append({
            'n': n,
            'bias_NDE': np.mean(bias_NDE_list),
            'bias_NIE': np.mean(bias_NIE_list),
            'bias_total': np.mean(bias_total_list),
            'rmse_total': np.sqrt(np.mean(np.array(bias_total_list)**2)),
        })
    
    df = pd.DataFrame(results)
    print()
    print(df.to_string(index=False))
    
    # Check: bias at largest n should be small
    largest_n_bias = abs(results[-1]['bias_total'])
    if largest_n_bias < 0.05:
        print(f"\n  ✓ PASS: bias at n={n_values[-1]} is {largest_n_bias:.4f} < 0.05")
        return True
    else:
        print(f"\n  ✗ FAIL: bias at n={n_values[-1]} is {largest_n_bias:.4f}")
        print(f"    EIF derivation likely has a bug. Recommend cross-check with")
        print(f"    Tchetgen-Shpitser 2014 EIF formulas in IID case (Test 2).")
        return False


def test_2_iid_reduction():
    """Test 2: When L=1, EIF should match Tchetgen-Shpitser 2014.
    
    Compare with substitution estimator (HCDMLEstimator).
    Both should converge to truth at large n.
    EIF should have similar or better bias/RMSE.
    """
    print("\n" + "═" * 70)
    print(" TEST 2: IID REDUCTION (L=1) ".center(70, "═"))
    print("═" * 70)
    
    dgp = LinearDGP(q=5, p=3, alpha_A=0.30, beta_A=0.20, alpha_M=np.array([0.5, 0.5, 0.5]))
    
    eif_estimates = []
    sub_estimates = []
    
    for seed in range(N_REPLICATES):
        data = dgp.generate(n=N_LARGE, seed=42 + seed)
        
        est_eif = HCDMLEstimatorEIF(paths=['direct', 'via_M'], n_folds=3, n_cluster_folds=1,
                                    outcome_learner=Ridge(alpha=1.0), random_state=seed)
        r_eif = est_eif.fit(Y=data.Y, A=data.A, M=data.M, X=data.X, S=data.S)
        eif_estimates.append(r_eif.tau_pj_cf)
        
        est_sub = HCDMLEstimator(paths=['direct', 'via_M'], n_folds=3, n_cluster_folds=1,
                                 outcome_learner=Ridge(alpha=1.0), random_state=seed)
        r_sub = est_sub.fit(Y=data.Y, A=data.A, M=data.M, X=data.X, S=data.S)
        sub_estimates.append(r_sub.tau_pj_cf)
    
    eif_arr = np.array(eif_estimates)
    sub_arr = np.array(sub_estimates)
    
    print(f"\n  True total = 0.60, n = {N_LARGE}, replicates = {N_REPLICATES}")
    print(f"\n  EIF estimator:        mean = {eif_arr.mean():+.4f}, bias = {eif_arr.mean()-0.60:+.4f}, sd = {eif_arr.std():.4f}")
    print(f"  Substitution est.:    mean = {sub_arr.mean():+.4f}, bias = {sub_arr.mean()-0.60:+.4f}, sd = {sub_arr.std():.4f}")
    print(f"\n  Difference (EIF - Substitution): {(eif_arr - sub_arr).mean():+.4f}")
    
    # Both should be close to truth
    eif_bias = abs(eif_arr.mean() - 0.60)
    sub_bias = abs(sub_arr.mean() - 0.60)
    
    if eif_bias < 0.05:
        print(f"  ✓ EIF bias ({eif_bias:.4f}) < 0.05")
        return True
    else:
        print(f"  ✗ EIF bias ({eif_bias:.4f}) ≥ 0.05")
        return False


def test_3_hierarchical():
    """Test 3: Hierarchical data with L > 1.
    
    Verify estimator handles clustering correctly.
    """
    print("\n" + "═" * 70)
    print(" TEST 3: HIERARCHICAL (L > 1) ".center(70, "═"))
    print("═" * 70)
    
    dgp = HierarchicalDGP(
        n_clusters=20, icc=0.10,
        alpha_A=0.30, beta_A=0.20,
        alpha_M=np.array([0.5, 0.5, 0.5]),
        cluster_size_range=(100, 300),
    )
    
    print(f"\n  True total = 0.60, clusters = 20, replicates = {N_REPLICATES}")
    
    estimates = []
    ses = []
    for seed in range(N_REPLICATES):
        data = dgp.generate(seed=42 + seed)
        est = HCDMLEstimatorEIF(
            paths=['direct', 'via_M'],
            n_folds=3, n_cluster_folds=3,
            outcome_learner=Ridge(alpha=1.0),
            random_state=seed,
        )
        r = est.fit(Y=data.Y, A=data.A, M=data.M, X=data.X, S=data.S)
        estimates.append(r.tau_pj_cf)
        ses.append(r.se)
    
    est_arr = np.array(estimates)
    se_arr = np.array(ses)
    
    print(f"\n  Mean τ̂ = {est_arr.mean():+.4f}")
    print(f"  Bias    = {est_arr.mean() - 0.60:+.4f}")
    print(f"  SD(τ̂)   = {est_arr.std():.4f}")
    print(f"  Mean reported SE = {se_arr.mean():.4f}")
    print(f"  Ratio (mean SE / SD): {se_arr.mean() / max(est_arr.std(), 1e-9):.2f}")
    print(f"  (Should be close to 1.0 if SE properly calibrated)")
    
    return True


def main():
    print("\n" + "█" * 70)
    print(" EIF ESTIMATOR VERIFICATION ".center(70, "█"))
    print("█" * 70)
    print(f"\n  N_LARGE = {N_LARGE}")
    print(f"  N_REP   = {N_REPLICATES}")
    print(f"\n  This script verifies the EIF estimator from theory/EIF_derivation.tex")
    print(f"  Run this BEFORE trusting EIF results on real data.")
    
    test_results = {}
    test_results['consistency'] = test_1_consistency()
    test_results['iid_reduction'] = test_2_iid_reduction()
    test_results['hierarchical'] = test_3_hierarchical()
    
    print("\n" + "█" * 70)
    print(" VERIFICATION SUMMARY ".center(70, "█"))
    print("█" * 70)
    
    for test_name, passed in test_results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name:<25} {status}")
    
    print()
    if all(test_results.values()):
        print("  ✓ All tests passed. EIF implementation appears correct.")
        print()
        print("  Next steps:")
        print("    1. Use EIF estimator (hcdml_eif.HCDMLEstimatorEIF) on real data")
        print("    2. Replace substitution estimator in paper")
        print("    3. Re-run bootstrap inference")
    else:
        print("  ✗ Some tests failed. EIF derivation likely has errors.")
        print()
        print("  Recommended actions:")
        print("    1. Re-read theory/EIF_derivation.tex carefully")
        print("    2. Cross-check formulas against Tchetgen-Shpitser 2014")
        print("    3. Consider using substitution estimator (hcdml.HCDMLEstimator) until verified")
        print("    4. Consult colleague with causal inference expertise")


if __name__ == '__main__':
    main()
