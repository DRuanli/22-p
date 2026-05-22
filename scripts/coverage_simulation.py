"""
Coverage Simulation for HC-DML
================================

Empirically verifies confidence interval coverage of HC-DML estimators.
Critical for journal reviewers (DSS, ESWA, JCI) who will ask:
    "Does your 95% CI actually contain truth 95% of the time?"

THREE COVERAGE SCENARIOS:
    1. IID case (L=1): Standard DML coverage
    2. Hierarchical case (L=20): Cluster-robust coverage  
    3. Small-cluster case (L=10): Stress test asymptotic theory

METHODS COMPARED:
    - HC-DML EIF (analytical cluster-robust SE)
    - HC-DML Substitution with bootstrap CI
    - HC-DML EIF with bootstrap CI

USAGE:
    python scripts/coverage_simulation.py
    
    # Quick version:
    N_REP=100 N_SAMPLE_SIZES=2 python scripts/coverage_simulation.py
    
    # Comprehensive (paper quality):
    N_REP=500 python scripts/coverage_simulation.py

EXPECTED RUNTIME:
    Quick:        15-30 min
    Standard:     1-2 hours
    Comprehensive: 4-6 hours

INTERPRETATION:
    Coverage 93-97%: Acceptable (CI properly calibrated)
    Coverage 90-93%: Slightly anti-conservative (over-cover or under)
    Coverage <90%:   Concerning (under-coverage)
    Coverage >98%:   Over-conservative (too wide CIs)

OUTPUT:
    results/coverage_simulation.csv: full results
    results/coverage_summary.csv: aggregated by method/scenario
"""

import sys
import os
import warnings
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'algorithms'))

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge

from dgp import LinearDGP, HierarchicalDGP
from hcdml import HCDMLEstimator
from hcdml_eif import HCDMLEstimatorEIF
from bootstrap_inference import bootstrap_estimator


# =========================================================================
# CONFIG
# =========================================================================

N_REP = int(os.environ.get('N_REP', '200'))
N_SAMPLE_SIZES_FLAG = int(os.environ.get('N_SAMPLE_SIZES', '3'))

# Bootstrap iterations within each replication
N_BOOT_INNER = int(os.environ.get('N_BOOT_INNER', '50'))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================================
# CORE COVERAGE COMPUTATION
# =========================================================================

def run_coverage_scenario(
    dgp,
    true_tau: float,
    n: int,
    scenario_name: str,
    n_rep: int = 200,
    use_bootstrap: bool = True,
    is_hierarchical: bool = False,
):
    """Run coverage simulation for one scenario.
    
    Returns dict with coverage statistics for each method.
    """
    print(f"\n  Scenario: {scenario_name} (n={n}, n_rep={n_rep})")
    print(f"  True τ = {true_tau:+.4f}")
    print(f"  ────────────────────────────────────────────────────")
    
    results = {
        'eif_analytical': [],
        'sub_analytical': [],
    }
    if use_bootstrap:
        results['eif_bootstrap'] = []
        results['sub_bootstrap'] = []
    
    t_start = time.time()
    
    for rep in range(n_rep):
        if (rep + 1) % max(1, n_rep // 20) == 0:
            elapsed = (time.time() - t_start) / 60
            print(f"    Replication {rep+1:>4}/{n_rep}  ({elapsed:.1f} min elapsed)")
        
        # Generate data
        if is_hierarchical:
            data = dgp.generate(seed=42 + rep)
            Y_, A_, M_, X_, S_ = data.Y, data.A, data.M, data.X, data.S
        else:
            data = dgp.generate(n=n, seed=42 + rep)
            Y_, A_, M_, X_, S_ = data.Y, data.A, data.M, data.X, data.S
        
        # ─── EIF Analytical CI ───
        try:
            est_eif = HCDMLEstimatorEIF(
                paths=['direct', 'via_M'],
                n_folds=3,
                n_cluster_folds=3 if is_hierarchical else 1,
                outcome_learner=LinearRegression(),
                propensity_learner=LogisticRegression(max_iter=1000),
                min_n_for_eif=500,
                random_state=rep,
            )
            r_eif = est_eif.fit(Y=Y_, A=A_, M=M_, X=X_, S=S_)
            covered = r_eif.ci_lower <= true_tau <= r_eif.ci_upper
            results['eif_analytical'].append({
                'tau': r_eif.tau_pj_cf,
                'ci_lower': r_eif.ci_lower,
                'ci_upper': r_eif.ci_upper,
                'covered': covered,
                'ci_width': r_eif.ci_upper - r_eif.ci_lower,
            })
        except Exception as e:
            results['eif_analytical'].append({'error': str(e)})
        
        # ─── Substitution Analytical CI ───
        try:
            est_sub = HCDMLEstimator(
                paths=['direct', 'via_M'],
                n_folds=3,
                n_cluster_folds=3 if is_hierarchical else 1,
                outcome_learner=LinearRegression(),
                random_state=rep,
            )
            r_sub = est_sub.fit(Y=Y_, A=A_, M=M_, X=X_, S=S_)
            covered = r_sub.ci_lower <= true_tau <= r_sub.ci_upper
            results['sub_analytical'].append({
                'tau': r_sub.tau_pj_cf,
                'ci_lower': r_sub.ci_lower,
                'ci_upper': r_sub.ci_upper,
                'covered': covered,
                'ci_width': r_sub.ci_upper - r_sub.ci_lower,
            })
        except Exception as e:
            results['sub_analytical'].append({'error': str(e)})
        
        # ─── Bootstrap CIs (more expensive, do less often) ───
        if use_bootstrap and (rep < N_BOOT_INNER or rep % 5 == 0):
            try:
                # EIF + bootstrap
                est_eif_boot = HCDMLEstimatorEIF(
                    paths=['direct', 'via_M'],
                    n_folds=3,
                    n_cluster_folds=3 if is_hierarchical else 1,
                    outcome_learner=LinearRegression(),
                    propensity_learner=LogisticRegression(max_iter=1000),
                    min_n_for_eif=500,
                    random_state=rep,
                )
                r_boot = bootstrap_estimator(
                    est_eif_boot, Y_, A_, M_, X_, S_,
                    n_bootstrap=N_BOOT_INNER,
                    method='cluster' if is_hierarchical else 'iid',
                    verbose=False,
                    random_state=rep,
                )
                covered = r_boot.ci_percentile[0] <= true_tau <= r_boot.ci_percentile[1]
                results['eif_bootstrap'].append({
                    'tau': r_boot.tau_total,
                    'ci_lower': r_boot.ci_percentile[0],
                    'ci_upper': r_boot.ci_percentile[1],
                    'covered': covered,
                    'ci_width': r_boot.ci_percentile[1] - r_boot.ci_percentile[0],
                })
            except Exception as e:
                results['eif_bootstrap'].append({'error': str(e)})
            
            # Substitution + bootstrap
            try:
                est_sub_boot = HCDMLEstimator(
                    paths=['direct', 'via_M'],
                    n_folds=3,
                    n_cluster_folds=3 if is_hierarchical else 1,
                    outcome_learner=LinearRegression(),
                    random_state=rep,
                )
                r_boot2 = bootstrap_estimator(
                    est_sub_boot, Y_, A_, M_, X_, S_,
                    n_bootstrap=N_BOOT_INNER,
                    method='cluster' if is_hierarchical else 'iid',
                    verbose=False,
                    random_state=rep,
                )
                covered = r_boot2.ci_percentile[0] <= true_tau <= r_boot2.ci_percentile[1]
                results['sub_bootstrap'].append({
                    'tau': r_boot2.tau_total,
                    'ci_lower': r_boot2.ci_percentile[0],
                    'ci_upper': r_boot2.ci_percentile[1],
                    'covered': covered,
                    'ci_width': r_boot2.ci_percentile[1] - r_boot2.ci_percentile[0],
                })
            except Exception as e:
                results['sub_bootstrap'].append({'error': str(e)})
    
    # ─── Compute coverage statistics ───
    summary = {}
    for method, reps in results.items():
        valid_reps = [r for r in reps if 'error' not in r]
        if len(valid_reps) > 0:
            covered_count = sum(r['covered'] for r in valid_reps)
            coverage_pct = 100 * covered_count / len(valid_reps)
            avg_width = np.mean([r['ci_width'] for r in valid_reps])
            avg_tau = np.mean([r['tau'] for r in valid_reps])
            
            summary[method] = {
                'scenario': scenario_name,
                'method': method,
                'n_rep': len(valid_reps),
                'coverage_pct': coverage_pct,
                'avg_ci_width': avg_width,
                'avg_tau': avg_tau,
                'bias': avg_tau - true_tau,
                'true_tau': true_tau,
            }
            
            # Status indicator
            if 93 <= coverage_pct <= 97:
                status = "✓ GOOD"
            elif 90 <= coverage_pct < 93:
                status = "⚠ UNDER"
            elif coverage_pct < 90:
                status = "✗ POOR"
            else:
                status = "○ OVER"
            
            print(f"    {method:<18}  coverage = {coverage_pct:5.1f}%  ({status})  avg_width = {avg_width:.3f}")
    
    return summary


# =========================================================================
# DGP DEFINITIONS
# =========================================================================

def get_iid_dgp():
    """LinearDGP for IID case."""
    return LinearDGP(
        q=5, p=3,
        alpha_A=0.30, beta_A=0.20,
        alpha_M=np.array([0.5, 0.5, 0.5]),
    ), 0.60  # true total tau


def get_hierarchical_dgp(n_clusters=20):
    """HierarchicalDGP for clustered case."""
    return HierarchicalDGP(
        n_clusters=n_clusters,
        icc=0.15,
        alpha_A=0.30, beta_A=0.20,
        alpha_M=np.array([0.5, 0.5, 0.5]),
        cluster_size_range=(100, 300),
    ), 0.60  # true total tau


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("\n" + "█" * 70)
    print(" COVERAGE SIMULATION FOR HC-DML ".center(70, "█"))
    print("█" * 70)
    print(f"\n  N_REP = {N_REP}")
    print(f"  N_BOOT_INNER = {N_BOOT_INNER}")
    print(f"  Scenarios: {N_SAMPLE_SIZES_FLAG}")
    
    all_summaries = []
    
    # ─── Scenario 1: IID small n ───
    if N_SAMPLE_SIZES_FLAG >= 1:
        dgp, true_tau = get_iid_dgp()
        summary = run_coverage_scenario(
            dgp, true_tau, n=2000, scenario_name='IID_n2000',
            n_rep=N_REP, use_bootstrap=True, is_hierarchical=False,
        )
        for m, s in summary.items():
            all_summaries.append(s)
    
    # ─── Scenario 2: IID large n ───
    if N_SAMPLE_SIZES_FLAG >= 2:
        dgp, true_tau = get_iid_dgp()
        summary = run_coverage_scenario(
            dgp, true_tau, n=5000, scenario_name='IID_n5000',
            n_rep=N_REP, use_bootstrap=False, is_hierarchical=False,
        )
        for m, s in summary.items():
            all_summaries.append(s)
    
    # ─── Scenario 3: Hierarchical 20 clusters ───
    if N_SAMPLE_SIZES_FLAG >= 3:
        dgp, true_tau = get_hierarchical_dgp(n_clusters=20)
        summary = run_coverage_scenario(
            dgp, true_tau, n=None, scenario_name='Hierarchical_L20',
            n_rep=N_REP, use_bootstrap=True, is_hierarchical=True,
        )
        for m, s in summary.items():
            all_summaries.append(s)
    
    # ─── Scenario 4: Hierarchical 10 clusters (stress test) ───
    if N_SAMPLE_SIZES_FLAG >= 4:
        dgp, true_tau = get_hierarchical_dgp(n_clusters=10)
        summary = run_coverage_scenario(
            dgp, true_tau, n=None, scenario_name='Hierarchical_L10',
            n_rep=N_REP, use_bootstrap=True, is_hierarchical=True,
        )
        for m, s in summary.items():
            all_summaries.append(s)
    
    # ─── Save results ───
    df = pd.DataFrame(all_summaries)
    summary_path = os.path.join(OUTPUT_DIR, 'coverage_summary.csv')
    df.to_csv(summary_path, index=False)
    print(f"\n  Summary saved: {summary_path}")
    
    # ─── Final summary table ───
    print("\n" + "█" * 70)
    print(" FINAL COVERAGE SUMMARY ".center(70, "█"))
    print("█" * 70)
    
    print()
    cols_show = ['scenario', 'method', 'coverage_pct', 'avg_ci_width', 'bias', 'n_rep']
    if all(c in df.columns for c in cols_show):
        print(df[cols_show].to_string(index=False))
    
    # ─── Quality flags ───
    print("\n  Quality flags:")
    poor = df[df['coverage_pct'] < 90]
    over = df[df['coverage_pct'] > 98]
    good = df[(df['coverage_pct'] >= 93) & (df['coverage_pct'] <= 97)]
    
    print(f"    Good calibration (93-97%): {len(good)}/{len(df)}")
    print(f"    Under-coverage (<90%):     {len(poor)}/{len(df)}")
    print(f"    Over-coverage (>98%):      {len(over)}/{len(df)}")
    
    if len(poor) == 0 and len(over) == 0:
        print("\n  ✓ All scenarios show acceptable CI calibration.")
    else:
        print("\n  ⚠ Some scenarios show miscalibration. Review individual results.")


if __name__ == '__main__':
    main()