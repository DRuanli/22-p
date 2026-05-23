"""
Per-Cluster Sensitivity Analysis for OULAD
=============================================

Runs Marginal Sensitivity Model bounds for EACH OULAD cluster (module).
Critical for paper: shows that statistically significant per-cluster
effects are more robust to unobserved confounding than the aggregate.

Hypothesis: Modules with LARGER |τ| have LARGER Γ break points
(more robust to unmeasured confounding).

USAGE:
    OULAD_PATH=~/oulad_data python scripts/sensitivity_per_cluster_oulad.py

OUTPUT:
    results/sensitivity_oulad_per_cluster.csv
"""

import sys
import os
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'algorithms'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression

from hcdml_eif import HCDMLEstimatorEIF
from sensitivity import confounding_sensitivity_analysis
from loaders_oulad import load_oulad


OULAD_PATH = os.path.expanduser(os.environ.get('OULAD_PATH', '~/oulad_data'))
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def main():
    print("\n" + "█" * 70)
    print(" PER-CLUSTER SENSITIVITY: OULAD ".center(70, "█"))
    print("█" * 70)
    
    if not os.path.exists(OULAD_PATH):
        print(f"\n✗ OULAD_PATH not found: {OULAD_PATH}")
        return
    
    # Load OULAD
    print("\n  Loading OULAD...")
    data = load_oulad(
        OULAD_PATH,
        protected='gender',
        outcome='pass_distinction',
        aggregate_clicks_by='cumulative',
        min_assessments=1,
        verbose=False,
    )
    
    cluster_map = data['metadata']['cluster_map']
    cluster_inv = {v: k for k, v in cluster_map.items()}
    
    # Use smaller gamma grid for per-cluster (faster)
    gamma_grid = np.array([1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0])
    
    all_results = []
    
    for s_id in sorted(np.unique(data['S'])):
        mask = data['S'] == s_id
        n_s = mask.sum()
        cluster_name = cluster_inv[s_id]
        
        if n_s < 300:
            print(f"\n  Skipping {cluster_name} (n={n_s} too small)")
            continue
        
        # Subset data
        Y_s = data['Y'][mask]
        A_s = data['A'][mask]
        M_s = data['M'][mask]
        X_s = data['X'][mask]
        S_s = np.zeros(n_s, dtype=int)
        
        # Skip if A unbalanced
        a_bal = A_s.mean()
        if a_bal < 0.05 or a_bal > 0.95:
            print(f"\n  Skipping {cluster_name} (A unbalanced: {a_bal:.3f})")
            continue
        
        print(f"\n  {cluster_name} (n={n_s}, A_bal={a_bal:.3f}):")
        
        try:
            est = HCDMLEstimatorEIF(
                paths=['direct', 'via_M'],
                n_folds=3, n_cluster_folds=1,
                outcome_learner=Ridge(alpha=1.0),
                propensity_learner=LogisticRegression(max_iter=1000),
                min_n_for_eif=200,
            )
            
            r_sens = confounding_sensitivity_analysis(
                est, Y_s, A_s, M_s, X_s, S_s,
                gamma_grid=gamma_grid,
                verbose=False,
            )
            
            # Save all gamma rows for this cluster
            for i, gamma in enumerate(gamma_grid):
                sign_preserved = (
                    np.sign(r_sens.tau_lower[i]) == np.sign(r_sens.tau_upper[i])
                    and r_sens.tau_lower[i] != 0
                )
                all_results.append({
                    'cluster': cluster_name,
                    'n': n_s,
                    'gamma': gamma,
                    'tau_point': r_sens.tau_point,
                    'tau_lower': r_sens.tau_lower[i],
                    'tau_upper': r_sens.tau_upper[i],
                    'sign_preserved': sign_preserved,
                })
            
            # Compute break point for this cluster
            break_point = None
            for i in range(1, len(gamma_grid)):
                if not all_results[-len(gamma_grid) + i]['sign_preserved']:
                    break_point = gamma_grid[i]
                    break
            
            if break_point is None:
                print(f"    τ̂ = {r_sens.tau_point:+.4f}, Γ break = >3.0 (robust)")
            else:
                print(f"    τ̂ = {r_sens.tau_point:+.4f}, Γ break ≈ {break_point:.2f}")
        
        except Exception as e:
            print(f"    ✗ Failed: {e}")
    
    # Save results
    if all_results:
        df = pd.DataFrame(all_results)
        path = os.path.join(OUTPUT_DIR, 'sensitivity_oulad_per_cluster.csv')
        df.to_csv(path, index=False)
        print(f"\n  Saved: {path}")
        
        # Compute break points summary
        print("\n" + "═" * 70)
        print(" SUMMARY: Γ BREAK POINTS BY CLUSTER ".center(70, "═"))
        print("═" * 70)
        
        summary_rows = []
        for cluster in df['cluster'].unique():
            sub = df[df['cluster'] == cluster].sort_values('gamma')
            tau_point = sub.iloc[0]['tau_point']
            
            # Find break
            crossed = sub[~sub['sign_preserved']]
            if len(crossed) > 0:
                break_g = crossed.iloc[0]['gamma']
            else:
                break_g = float('inf')
            
            summary_rows.append({
                'cluster': cluster,
                'n': sub.iloc[0]['n'],
                'tau': tau_point,
                'abs_tau': abs(tau_point),
                'gamma_break': break_g,
            })
        
        summary_df = pd.DataFrame(summary_rows).sort_values('abs_tau', ascending=False)
        
        print()
        print(summary_df.to_string(index=False))
        
        # Test hypothesis: larger |τ| → larger break point
        valid = summary_df[summary_df['gamma_break'] < float('inf')]
        if len(valid) > 5:
            corr = valid['abs_tau'].corr(valid['gamma_break'])
            print(f"\n  Correlation |τ| × Γ_break: {corr:+.3f}")
            print(f"  (Positive correlation supports hypothesis:")
            print(f"   larger effects are more robust to confounding)")
        
        summary_path = os.path.join(OUTPUT_DIR, 'sensitivity_oulad_break_points.csv')
        summary_df.to_csv(summary_path, index=False)
        print(f"\n  Summary saved: {summary_path}")


if __name__ == '__main__':
    main()