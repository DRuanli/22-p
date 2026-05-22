"""
Synthetic Data Validation: HC-DML vs Baselines
==================================================

Compares HC-DML against baselines on synthetic data where ground truth
is known. Reports bias, variance, and coverage across multiple seeds.

USAGE:
    python scripts/validate_synthetic.py

WHAT IT DOES:
    1. Generates synthetic data from each DGP variant
    2. Runs all methods (HC-DML, naive, single-level DML, ChiappaVAE)
    3. Reports: bias, RMSE, coverage of CI, runtime
    4. Saves results to CSV for further analysis

This is the PRIMARY validation: confirms our algorithm recovers truth.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'algorithms'))

import time
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from dgp import LinearDGP, HierarchicalDGP, ConfoundedDGP
from hcdml import HCDMLEstimator
from baselines import NaivePlugIn, SingleLevelDML, ChiappaVAE


# =========================================================================
# CONFIGURATION
# =========================================================================

N_SEEDS = 10  # Number of random seeds per DGP setting
N_BOOTSTRAP = 50  # For ChiappaVAE and NaivePlugIn with bootstrap

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================================
# RUN ALL METHODS
# =========================================================================

def run_methods(data, paths=('direct', 'via_M'), psi=None):
    """Run all methods on given data, return dict of results."""
    if psi is None:
        psi = {'direct': 0.0, 'via_M': 0.0}
    
    results = {}
    
    # Method 1: Naive plug-in
    try:
        t0 = time.time()
        r = NaivePlugIn(paths=list(paths), psi=psi, outcome_model='linear', bootstrap_n=0).fit(
            data.Y, data.A, data.M, data.X, data.S
        )
        results['Naive'] = {
            'tau': r.tau_pj_cf,
            'se': r.se,
            'ci_l': r.ci_lower,
            'ci_u': r.ci_upper,
            'per_path': r.tau_per_path,
            'time': time.time() - t0,
        }
    except Exception as e:
        results['Naive'] = {'error': str(e)}
    
    # Method 2: Single-level DML
    try:
        t0 = time.time()
        r = SingleLevelDML(paths=list(paths), psi=psi, n_folds=3).fit(
            data.Y, data.A, data.M, data.X, data.S
        )
        results['SingleLevelDML'] = {
            'tau': r.tau_pj_cf,
            'se': r.se,
            'ci_l': r.ci_lower,
            'ci_u': r.ci_upper,
            'per_path': r.tau_per_path,
            'time': time.time() - t0,
        }
    except Exception as e:
        results['SingleLevelDML'] = {'error': str(e)}
    
    # Method 3: ChiappaVAE (simplified) — without bootstrap for speed
    try:
        t0 = time.time()
        r = ChiappaVAE(paths=list(paths), psi=psi, bootstrap_n=0).fit(
            data.Y, data.A, data.M, data.X
        )
        results['ChiappaVAE'] = {
            'tau': r.tau_pj_cf,
            'se': r.se,
            'ci_l': r.ci_lower,
            'ci_u': r.ci_upper,
            'per_path': r.tau_per_path,
            'time': time.time() - t0,
        }
    except Exception as e:
        results['ChiappaVAE'] = {'error': str(e)}
    
    # Method 4: HC-DML
    try:
        t0 = time.time()
        est = HCDMLEstimator(
            paths=list(paths), psi=psi,
            n_folds=3, n_cluster_folds=3 if data.n_clusters > 5 else 1,
            outcome_learner=Ridge(alpha=1.0),
            verbose=False,
        )
        r = est.fit(data.Y, data.A, data.M, data.X, data.S)
        results['HC-DML'] = {
            'tau': r.tau_pj_cf,
            'se': r.se,
            'ci_l': r.ci_lower,
            'ci_u': r.ci_upper,
            'per_path': r.tau_per_path,
            'time': time.time() - t0,
        }
    except Exception as e:
        results['HC-DML'] = {'error': str(e)}
    
    return results


# =========================================================================
# EXPERIMENTS
# =========================================================================

def experiment_1_linear(n=3000):
    """Experiment 1: LinearDGP (no clustering) — sanity check."""
    print("\n" + "═" * 70)
    print(" EXPERIMENT 1: LinearDGP (IID) ".center(70, "═"))
    print("═" * 70)
    
    dgp = LinearDGP(q=5, p=3, alpha_A=0.30, beta_A=0.20, 
                    alpha_M=np.array([0.5, 0.5, 0.5]))
    truth = dgp.true_pj_cf(psi={'direct': 0.0, 'via_M': 0.0})
    true_tau = truth['total']
    
    print(f"\nTrue PJ-CF = {true_tau:.4f}  (direct={truth['PSE_direct']:.4f}, via_M={truth['PSE_via_M']:.4f})")
    print(f"n = {n}, seeds = {N_SEEDS}\n")
    
    results_list = []
    
    for seed_i in range(N_SEEDS):
        data = dgp.generate(n=n, seed=42 + seed_i)
        seed_results = run_methods(data)
        
        for method, res in seed_results.items():
            if 'error' in res:
                continue
            row = {
                'experiment': 'Linear',
                'seed': seed_i,
                'method': method,
                'tau': res['tau'],
                'true_tau': true_tau,
                'bias': res['tau'] - true_tau,
                'se': res['se'],
                'ci_covers': res['ci_l'] <= true_tau <= res['ci_u'] if not np.isnan(res['se']) else False,
                'ci_width': res['ci_u'] - res['ci_l'] if not np.isnan(res['se']) else float('nan'),
                'time_s': res['time'],
            }
            row.update({f'tau_{k}': v for k, v in res['per_path'].items()})
            results_list.append(row)
    
    return pd.DataFrame(results_list)


def experiment_2_hierarchical(n_clusters=30):
    """Experiment 2: HierarchicalDGP — test cluster-aware methods."""
    print("\n" + "═" * 70)
    print(" EXPERIMENT 2: HierarchicalDGP (clustered) ".center(70, "═"))
    print("═" * 70)
    
    dgp = HierarchicalDGP(
        n_clusters=n_clusters, icc=0.10,
        cluster_size_range=(30, 150),
        alpha_A=0.25, beta_A=0.20,
        alpha_M=np.array([0.5, 0.5, 0.5])
    )
    truth = dgp.true_pj_cf(psi={'direct': 0.0, 'via_M': 0.0})
    true_tau = truth['total']
    
    print(f"\nTrue PJ-CF = {true_tau:.4f}  (n_clusters={n_clusters})")
    print(f"seeds = {N_SEEDS}\n")
    
    results_list = []
    
    for seed_i in range(N_SEEDS):
        data = dgp.generate(seed=42 + seed_i)
        seed_results = run_methods(data)
        
        for method, res in seed_results.items():
            if 'error' in res:
                continue
            row = {
                'experiment': 'Hierarchical',
                'seed': seed_i,
                'method': method,
                'tau': res['tau'],
                'true_tau': true_tau,
                'bias': res['tau'] - true_tau,
                'se': res['se'],
                'ci_covers': res['ci_l'] <= true_tau <= res['ci_u'] if not np.isnan(res['se']) else False,
                'ci_width': res['ci_u'] - res['ci_l'] if not np.isnan(res['se']) else float('nan'),
                'time_s': res['time'],
            }
            row.update({f'tau_{k}': v for k, v in res['per_path'].items()})
            results_list.append(row)
    
    return pd.DataFrame(results_list)


def experiment_3_confounded(n_clusters=30):
    """Experiment 3: ConfoundedDGP — test sensitivity to unobserved confounder."""
    print("\n" + "═" * 70)
    print(" EXPERIMENT 3: ConfoundedDGP (unobserved U) ".center(70, "═"))
    print("═" * 70)
    
    dgp = ConfoundedDGP(
        n_clusters=n_clusters, icc=0.10,
        cluster_size_range=(30, 150),
        alpha_A=0.25, beta_A=0.20,
        alpha_M=np.array([0.5, 0.5, 0.5]),
        alpha_U=0.30, gamma_U=0.40,
    )
    truth = dgp.true_pj_cf(psi={'direct': 0.0, 'via_M': 0.0})
    true_tau = truth['total']
    
    print(f"\nTrue PJ-CF = {true_tau:.4f}  (unobserved U with α_U=0.30, γ_U=0.40)")
    print(f"Expected: all methods will be BIASED because they don't observe U")
    print(f"seeds = {N_SEEDS}\n")
    
    results_list = []
    
    for seed_i in range(N_SEEDS):
        data = dgp.generate(seed=42 + seed_i)
        seed_results = run_methods(data)
        
        for method, res in seed_results.items():
            if 'error' in res:
                continue
            row = {
                'experiment': 'Confounded',
                'seed': seed_i,
                'method': method,
                'tau': res['tau'],
                'true_tau': true_tau,
                'bias': res['tau'] - true_tau,
                'se': res['se'],
                'ci_covers': res['ci_l'] <= true_tau <= res['ci_u'] if not np.isnan(res['se']) else False,
                'ci_width': res['ci_u'] - res['ci_l'] if not np.isnan(res['se']) else float('nan'),
                'time_s': res['time'],
            }
            row.update({f'tau_{k}': v for k, v in res['per_path'].items()})
            results_list.append(row)
    
    return pd.DataFrame(results_list)


# =========================================================================
# AGGREGATION AND REPORTING
# =========================================================================

def summarize_results(df: pd.DataFrame) -> pd.DataFrame:
    """Compute summary statistics across seeds per method."""
    summary = df.groupby(['experiment', 'method']).agg(
        n_seeds=('seed', 'count'),
        true_tau=('true_tau', 'first'),
        tau_mean=('tau', 'mean'),
        tau_sd=('tau', 'std'),
        bias=('bias', 'mean'),
        rmse=('bias', lambda x: np.sqrt(np.mean(x**2))),
        mean_se=('se', 'mean'),
        coverage=('ci_covers', 'mean'),
        avg_ci_width=('ci_width', 'mean'),
        avg_time_s=('time_s', 'mean'),
    ).reset_index()
    return summary


def print_summary(summary: pd.DataFrame):
    """Print summary table."""
    print("\n" + "═" * 90)
    print(" SUMMARY: All Methods Across DGPs ".center(90, "═"))
    print("═" * 90)
    
    pd.set_option('display.float_format', lambda x: f'{x:.4f}')
    pd.set_option('display.width', 120)
    pd.set_option('display.max_columns', 15)
    
    print("\n", summary.to_string(index=False))


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("\n" + "█" * 70)
    print(" HC-DML SYNTHETIC VALIDATION SUITE ".center(70, "█"))
    print("█" * 70)
    
    all_results = []
    
    # Experiment 1: Linear (sanity check)
    df1 = experiment_1_linear(n=3000)
    all_results.append(df1)
    print(f"  Done: Linear ({len(df1)} rows)")
    
    # Experiment 2: Hierarchical
    df2 = experiment_2_hierarchical(n_clusters=30)
    all_results.append(df2)
    print(f"  Done: Hierarchical ({len(df2)} rows)")
    
    # Experiment 3: Confounded
    df3 = experiment_3_confounded(n_clusters=30)
    all_results.append(df3)
    print(f"  Done: Confounded ({len(df3)} rows)")
    
    # Combine
    all_df = pd.concat(all_results, ignore_index=True)
    
    # Save raw
    raw_path = os.path.join(OUTPUT_DIR, 'synthetic_validation_raw.csv')
    all_df.to_csv(raw_path, index=False)
    print(f"\n  Raw results saved: {raw_path}")
    
    # Summary
    summary = summarize_results(all_df)
    summary_path = os.path.join(OUTPUT_DIR, 'synthetic_validation_summary.csv')
    summary.to_csv(summary_path, index=False)
    print(f"  Summary saved:     {summary_path}")
    
    # Print
    print_summary(summary)
    
    # Highlight key findings
    print("\n" + "═" * 70)
    print(" KEY FINDINGS ".center(70, "═"))
    print("═" * 70)
    
    for exp in summary['experiment'].unique():
        exp_df = summary[summary['experiment'] == exp]
        best_bias = exp_df.loc[exp_df['bias'].abs().idxmin()]
        best_rmse = exp_df.loc[exp_df['rmse'].idxmin()]
        
        print(f"\n{exp}:")
        print(f"  Lowest bias:  {best_bias['method']:<20} (bias={best_bias['bias']:+.4f})")
        print(f"  Lowest RMSE:  {best_rmse['method']:<20} (RMSE={best_rmse['rmse']:.4f})")
    
    print("\n" + "═" * 70)
    print(" DONE ".center(70, "═"))
    print("═" * 70)


if __name__ == '__main__':
    main()
