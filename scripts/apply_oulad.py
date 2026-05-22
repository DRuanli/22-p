"""
OULAD Application: HC-DML Path-Specific Fairness Analysis
============================================================

Applies HC-DML and baselines to the Open University Learning Analytics Dataset
(OULAD) for path-specific counterfactual fairness analysis.

SETUP:
    1. Download OULAD from https://analyse.kmi.open.ac.uk/open-dataset
    2. Extract 7 CSVs to OULAD_PATH below
    3. Adjust OULAD_PATH variable to your local directory
    4. Run: python scripts/apply_oulad.py

DAG used:
    A: gender (binary, F=1)
    M: sum_clicks, first_assessment_score, avg_assessment_score, 
       days_late_registration
    X: age_band, region, imd_band, highest_education, disability,
       num_prev_attempts, studied_credits
    Y: pass_distinction (binary)
    S: code_module × code_presentation (22 clusters)

EXPECTED RUNTIME:
    - Loading OULAD with VLE aggregation: 3-10 minutes (depending on RAM)
    - Running 4 methods: 5-20 minutes
    - Sensitivity analysis: additional 10-20 minutes

EXPECTED MEMORY:
    - ~4-8 GB peak during VLE aggregation
"""

import sys
import os
import warnings

# Adjust these paths for your local environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'algorithms'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))

# Local OULAD CSV directory — UPDATE THIS
OULAD_PATH = os.environ.get('OULAD_PATH', '~/oulad_data')
OULAD_PATH = os.path.expanduser(OULAD_PATH)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor

from loaders_oulad import load_oulad
from hcdml import HCDMLEstimator
from baselines import NaivePlugIn, SingleLevelDML, ChiappaVAE


# =========================================================================
# MAIN ANALYSIS
# =========================================================================

def main():
    print("\n" + "█" * 70)
    print(" OULAD: PATH-SPECIFIC COUNTERFACTUAL FAIRNESS ".center(70, "█"))
    print("█" * 70)
    
    # Check OULAD path
    if not os.path.exists(OULAD_PATH):
        print(f"\n✗ ERROR: OULAD_PATH not found: {OULAD_PATH}")
        print(f"  Download OULAD from: https://analyse.kmi.open.ac.uk/open-dataset")
        print(f"  Then set OULAD_PATH env variable or edit this script")
        return
    
    # ─── Load OULAD ───
    try:
        data = load_oulad(
            OULAD_PATH,
            protected='gender',
            outcome='pass_distinction',
            aggregate_clicks_by='cumulative',  # Use 'first_quarter' to avoid leakage
            min_assessments=1,
            verbose=True,
        )
    except Exception as e:
        print(f"\n✗ Failed to load OULAD: {e}")
        return
    
    # ─── Run all methods ───
    print("\n" + "═" * 70)
    print(" RUNNING METHODS ".center(70, "═"))
    print("═" * 70)
    
    # NOTE: For OULAD's larger scale, GBM may give better estimates than Ridge.
    # But GBM is slow. Adjust based on your runtime budget.
    use_gbm = False  # Set True for higher quality, slower run
    
    if use_gbm:
        outcome_learner = GradientBoostingRegressor(
            n_estimators=100, max_depth=4, random_state=42
        )
    else:
        outcome_learner = Ridge(alpha=1.0)
    
    methods = [
        ('Naive (linear)', NaivePlugIn(paths=['direct', 'via_M'], outcome_model='linear')),
        ('SingleLevelDML', SingleLevelDML(paths=['direct', 'via_M'], n_folds=3)),
        ('ChiappaVAE',     ChiappaVAE(paths=['direct', 'via_M'], bootstrap_n=0)),
        ('HC-DML',         HCDMLEstimator(
            paths=['direct', 'via_M'],
            n_folds=3, n_cluster_folds=5,
            outcome_learner=outcome_learner,
            verbose=True,
        )),
    ]
    
    results = []
    for method_name, estimator in methods:
        print(f"\n  → Running {method_name}...")
        try:
            r = estimator.fit(
                Y=data['Y'], A=data['A'],
                M=data['M'], X=data['X'], S=data['S']
            )
            results.append({
                'method': method_name,
                'tau_total': r.tau_pj_cf,
                'tau_direct': r.tau_per_path.get('direct', np.nan),
                'tau_via_M': r.tau_per_path.get('via_M', np.nan),
                'se': r.se,
                'ci_lower': r.ci_lower,
                'ci_upper': r.ci_upper,
                'p_value': r.p_value,
            })
            print(f"    τ = {r.tau_pj_cf:+.4f}  [{r.ci_lower:+.4f}, {r.ci_upper:+.4f}]")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            results.append({'method': method_name, 'error': str(e)})
    
    # ─── Save main results ───
    df_results = pd.DataFrame(results)
    main_path = os.path.join(OUTPUT_DIR, 'oulad_main_results.csv')
    df_results.to_csv(main_path, index=False)
    print(f"\n\n  Main results saved: {main_path}")
    
    print("\n" + "─" * 70)
    print("  Comparison table:")
    print(df_results[['method', 'tau_total', 'tau_direct', 'tau_via_M',
                     'se', 'ci_lower', 'ci_upper']].to_string(index=False))
    
    # ─── Sensitivity to ψ ───
    print("\n" + "═" * 70)
    print(" SENSITIVITY TO ψ(via_M) — HC-DML ".center(70, "═"))
    print("═" * 70)
    
    sens_results = []
    for psi_val in [0.0, 0.25, 0.5, 0.75, 1.0]:
        print(f"  → ψ(via_M) = {psi_val:.2f}...")
        est = HCDMLEstimator(
            paths=['direct', 'via_M'],
            psi={'direct': 0.0, 'via_M': psi_val},
            n_folds=3, n_cluster_folds=5,
            outcome_learner=outcome_learner,
        )
        r = est.fit(Y=data['Y'], A=data['A'], M=data['M'], X=data['X'], S=data['S'])
        sens_results.append({
            'psi_via_M': psi_val,
            'tau_PJ_CF': r.tau_pj_cf,
            'ci_lower': r.ci_lower,
            'ci_upper': r.ci_upper,
        })
        print(f"    τ = {r.tau_pj_cf:+.4f}  CI=[{r.ci_lower:+.4f}, {r.ci_upper:+.4f}]")
    
    sens_df = pd.DataFrame(sens_results)
    sens_path = os.path.join(OUTPUT_DIR, 'oulad_sensitivity_psi.csv')
    sens_df.to_csv(sens_path, index=False)
    print(f"\n  Sensitivity saved: {sens_path}")
    
    # ─── Subgroup analysis: by cluster ───
    print("\n" + "═" * 70)
    print(" PER-CLUSTER HC-DML ESTIMATES ".center(70, "═"))
    print("═" * 70)
    
    cluster_results = []
    cluster_inv = {v: k for k, v in data['metadata']['cluster_map'].items()}
    
    for s_id in np.unique(data['S']):
        mask = data['S'] == s_id
        n_s = mask.sum()
        if n_s < 200:  # Need enough samples for cluster-specific
            continue
        
        try:
            est = HCDMLEstimator(
                paths=['direct', 'via_M'],
                n_folds=3, n_cluster_folds=1,
                outcome_learner=outcome_learner,
            )
            # Use cluster as single S
            S_local = np.zeros(n_s, dtype=int)
            r = est.fit(
                Y=data['Y'][mask], A=data['A'][mask],
                M=data['M'][mask], X=data['X'][mask], S=S_local,
            )
            cluster_results.append({
                'cluster_id': s_id,
                'cluster_name': cluster_inv[s_id],
                'n': n_s,
                'tau_PJ_CF': r.tau_pj_cf,
                'tau_direct': r.tau_per_path.get('direct'),
                'tau_via_M': r.tau_per_path.get('via_M'),
            })
        except Exception as e:
            print(f"    Cluster {s_id} failed: {e}")
    
    cluster_df = pd.DataFrame(cluster_results)
    cluster_path = os.path.join(OUTPUT_DIR, 'oulad_per_cluster.csv')
    cluster_df.to_csv(cluster_path, index=False)
    print(f"\n  Per-cluster results saved: {cluster_path}")
    print(cluster_df.to_string(index=False))
    
    # ─── Summary ───
    print("\n" + "█" * 70)
    print(" ANALYSIS COMPLETE ".center(70, "█"))
    print("█" * 70)
    
    print("\nINTERPRETATION CHECKLIST:")
    print("  1. Sign of τ_total: positive = Females have higher pass rate")
    print("  2. Direct vs via_M ratio: how much is mediated?")
    print("  3. Sensitivity to ψ: are findings robust to mediator justifiability?")
    print("  4. Cross-method agreement: methods should give similar τ")
    print("  5. Per-cluster heterogeneity: do effects vary across modules?")


if __name__ == '__main__':
    main()
