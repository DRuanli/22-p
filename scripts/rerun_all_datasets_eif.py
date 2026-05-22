"""
Re-run All Real Datasets with EIF Estimator
=============================================

Re-runs HC-DML on all real datasets using the VERIFIED EIF estimator
(HCDMLEstimatorEIF) instead of the substitution-based estimator.

This is the primary results script for JCI/AISTATS submission.

Compared to apply_all_datasets.py (which uses substitution estimator):
    - Uses EIF score → doubly robust
    - Proper cluster-robust SE (no 30-160x underestimation)
    - More efficient inference

DATASETS:
    1. UCI Student Math
    2. UCI Student Portuguese  
    3. xAPI Educational
    4. Law School (LSAC)
    5. OULAD

OUTPUT:
    - results/eif_all_datasets.csv: main comparison table
    - results/eif_vs_substitution.csv: side-by-side comparison
    - results/eif_oulad_per_cluster.csv: per-cluster EIF results

USAGE:
    DATA_DIR=/path/to/data OULAD_PATH=~/oulad_data \\
    LAW_PATH=data/law_data.csv python scripts/rerun_all_datasets_eif.py

EXPECTED RUNTIME:
    - UCI Math/Por: 30s each (small n)
    - xAPI:         30s
    - Law School:   3-5 min (n=22K)
    - OULAD:        10-20 min (n=26K, MC marginalization)
    
    Total: ~25-40 min
"""

import sys
import os
import warnings
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'algorithms'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge, LogisticRegression

from hcdml import HCDMLEstimator       # Substitution (for comparison)
from hcdml_eif import HCDMLEstimatorEIF  # EIF (new primary)
from loaders import load_uci_student, load_xapi
from loaders_law_school import load_law_school

try:
    from loaders_oulad import load_oulad
    HAS_OULAD = True
except ImportError:
    HAS_OULAD = False


# =========================================================================
# CONFIG
# =========================================================================

DATA_DIR = os.environ.get('DATA_DIR', '/Users/lenguyen/Documents/26-Research/unknown/hcdml_project/data')
OULAD_PATH = os.path.expanduser(os.environ.get('OULAD_PATH', '/Users/lenguyen/Documents/26-Research/unknown/hcdml_project/oulad_data'))
LAW_PATH = os.environ.get(
    'LAW_PATH',
    os.path.join(os.path.dirname(__file__), '..', 'data', 'law_data.csv')
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================================
# RUN BOTH ESTIMATORS ON A DATASET
# =========================================================================

def run_estimators(data, name, verbose=True):
    """Run substitution + EIF estimators on a dataset.
    
    Returns list of result dicts (one per method).
    """
    print("\n" + "─" * 70)
    print(f"  {name} (n={data['metadata']['n']:,}, clusters={data['metadata']['n_clusters']})")
    print("─" * 70)
    
    rows = []
    
    n_clusters = data['metadata']['n_clusters']
    n_cluster_folds = min(3, n_clusters) if n_clusters > 1 else 1
    
    # Use Ridge for outcome (regularization helps on real data)
    # Use LogisticRegression for propensity (well-calibrated)
    outcome_learner = Ridge(alpha=1.0)
    propensity_learner = LogisticRegression(max_iter=1000)
    
    # ─── Substitution estimator (existing) ───
    print(f"\n  Running substitution estimator...")
    t0 = time.time()
    try:
        est_sub = HCDMLEstimator(
            paths=['direct', 'via_M'],
            n_folds=3, n_cluster_folds=n_cluster_folds,
            outcome_learner=outcome_learner,
        )
        r_sub = est_sub.fit(Y=data['Y'], A=data['A'], M=data['M'], X=data['X'], S=data['S'])
        elapsed_sub = time.time() - t0
        
        print(f"    τ = {r_sub.tau_pj_cf:+.4f}  CI=[{r_sub.ci_lower:+.4f}, {r_sub.ci_upper:+.4f}]  SE={r_sub.se:.4f}  ({elapsed_sub:.1f}s)")
        
        rows.append({
            'dataset': name,
            'n': data['metadata']['n'],
            'n_clusters': data['metadata']['n_clusters'],
            'method': 'Substitution',
            'tau_total': r_sub.tau_pj_cf,
            'tau_direct': r_sub.tau_per_path.get('direct'),
            'tau_via_M': r_sub.tau_per_path.get('via_M'),
            'se': r_sub.se,
            'ci_lower': r_sub.ci_lower,
            'ci_upper': r_sub.ci_upper,
            'p_value': r_sub.p_value,
            'time_s': elapsed_sub,
        })
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        rows.append({'dataset': name, 'method': 'Substitution', 'error': str(e)})
    
    # ─── EIF estimator (new primary) ───
    print(f"\n  Running EIF estimator...")
    t0 = time.time()
    try:
        est_eif = HCDMLEstimatorEIF(
            paths=['direct', 'via_M'],
            n_folds=3, n_cluster_folds=n_cluster_folds,
            outcome_learner=outcome_learner,
            propensity_learner=propensity_learner,
        )
        r_eif = est_eif.fit(Y=data['Y'], A=data['A'], M=data['M'], X=data['X'], S=data['S'])
        elapsed_eif = time.time() - t0
        
        print(f"    τ = {r_eif.tau_pj_cf:+.4f}  CI=[{r_eif.ci_lower:+.4f}, {r_eif.ci_upper:+.4f}]  SE={r_eif.se:.4f}  ({elapsed_eif:.1f}s)")
        
        rows.append({
            'dataset': name,
            'n': data['metadata']['n'],
            'n_clusters': data['metadata']['n_clusters'],
            'method': 'EIF',
            'tau_total': r_eif.tau_pj_cf,
            'tau_direct': r_eif.tau_per_path.get('direct'),
            'tau_via_M': r_eif.tau_per_path.get('via_M'),
            'se': r_eif.se,
            'ci_lower': r_eif.ci_lower,
            'ci_upper': r_eif.ci_upper,
            'p_value': r_eif.p_value,
            'time_s': elapsed_eif,
            'phi_NDE_mean': r_eif.phi_NDE_mean,  # diagnostic (should ≈ 0)
            'phi_NIE_mean': r_eif.phi_NIE_mean,
            'theta_00': r_eif.eif_decomposition.get('theta_00'),
            'theta_10': r_eif.eif_decomposition.get('theta_10'),
            'theta_11': r_eif.eif_decomposition.get('theta_11'),
        })
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        rows.append({'dataset': name, 'method': 'EIF', 'error': str(e)})
    
    return rows


# =========================================================================
# PER-CLUSTER EIF ANALYSIS (OULAD only)
# =========================================================================

def per_cluster_eif(data):
    """Run EIF estimator on each cluster separately for OULAD.
    
    This produces the per-module forest plot for the paper.
    """
    print("\n" + "═" * 70)
    print(" PER-CLUSTER EIF ON OULAD ".center(70, "═"))
    print("═" * 70)
    
    cluster_map = data['metadata']['cluster_map']
    cluster_inv = {v: k for k, v in cluster_map.items()}
    
    results = []
    for s_id in sorted(np.unique(data['S'])):
        mask = data['S'] == s_id
        n_s = mask.sum()
        cluster_name = cluster_inv[s_id]
        
        if n_s < 200:
            continue
        
        # Subset
        Y_s = data['Y'][mask]
        A_s = data['A'][mask]
        M_s = data['M'][mask]
        X_s = data['X'][mask]
        S_s = np.zeros(n_s, dtype=int)
        
        # Skip if A unbalanced
        a_bal = A_s.mean()
        if a_bal < 0.05 or a_bal > 0.95:
            continue
        
        try:
            est = HCDMLEstimatorEIF(
                paths=['direct', 'via_M'],
                n_folds=3, n_cluster_folds=1,
                outcome_learner=Ridge(alpha=1.0),
                propensity_learner=LogisticRegression(max_iter=1000),
            )
            r = est.fit(Y_s, A_s, M_s, X_s, S_s)
            
            results.append({
                'cluster': cluster_name,
                'n': n_s,
                'a_balance': a_bal,
                'y_mean': float(Y_s.mean()),
                'tau_eif': r.tau_pj_cf,
                'tau_NDE': r.tau_per_path.get('direct'),
                'tau_NIE': r.tau_per_path.get('via_M'),
                'se': r.se,
                'ci_lower': r.ci_lower,
                'ci_upper': r.ci_upper,
                'p_value': r.p_value,
            })
            
            print(f"  {cluster_name:<12} n={n_s:5d}  τ={r.tau_pj_cf:+.4f}  CI=[{r.ci_lower:+.4f}, {r.ci_upper:+.4f}]")
        except Exception as e:
            print(f"  {cluster_name:<12} FAILED: {e}")
    
    df = pd.DataFrame(results)
    
    # Heterogeneity check
    if len(df) > 0:
        print(f"\n  Heterogeneity diagnosis:")
        print(f"    τ range:           [{df['tau_eif'].min():+.4f}, {df['tau_eif'].max():+.4f}]")
        print(f"    τ standard dev:    {df['tau_eif'].std():.4f}")
        print(f"    Positive clusters: {(df['tau_eif'] > 0.01).sum()} / {len(df)}")
        print(f"    Negative clusters: {(df['tau_eif'] < -0.01).sum()} / {len(df)}")
    
    return df


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("\n" + "█" * 70)
    print(" RE-RUN ALL DATASETS WITH EIF ESTIMATOR ".center(70, "█"))
    print("█" * 70)
    print(f"\n  DATA_DIR:   {DATA_DIR}")
    print(f"  LAW_PATH:   {LAW_PATH}")
    print(f"  OULAD_PATH: {OULAD_PATH}")
    
    all_rows = []
    
    # ─── UCI Math ───
    path = os.path.join(DATA_DIR, 'student-mat.csv')
    if os.path.exists(path):
        try:
            data = load_uci_student(path, subject='math', outcome='G3', protected='sex')
            all_rows.extend(run_estimators(data, 'UCI_Math'))
        except Exception as e:
            print(f"\n  UCI Math load failed: {e}")
    else:
        print(f"\n  ✗ UCI Math not found: {path}")
    
    # ─── UCI Portuguese ───
    path = os.path.join(DATA_DIR, 'student-por.csv')
    if os.path.exists(path):
        try:
            data = load_uci_student(path, subject='portuguese', outcome='G3', protected='sex')
            all_rows.extend(run_estimators(data, 'UCI_Portuguese'))
        except Exception as e:
            print(f"\n  UCI Portuguese load failed: {e}")
    
    # ─── xAPI ───
    path = os.path.join(DATA_DIR, 'xAPI-Edu-Data_csv.xls')
    if os.path.exists(path):
        try:
            data = load_xapi(path, outcome='class', protected='gender')
            all_rows.extend(run_estimators(data, 'xAPI'))
        except Exception as e:
            print(f"\n  xAPI load failed: {e}")
    
    # ─── Law School ───
    if os.path.exists(LAW_PATH):
        try:
            data = load_law_school(LAW_PATH)
            all_rows.extend(run_estimators(data, 'Law_School'))
        except Exception as e:
            print(f"\n  Law School load failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ─── OULAD ───
    if HAS_OULAD and os.path.exists(OULAD_PATH):
        try:
            data_oulad = load_oulad(
                OULAD_PATH,
                protected='gender',
                outcome='pass_distinction',
                aggregate_clicks_by='cumulative',
                min_assessments=1,
                verbose=False,
            )
            all_rows.extend(run_estimators(data_oulad, 'OULAD'))
            
            # Per-cluster analysis for OULAD only
            print()
            per_cluster_df = per_cluster_eif(data_oulad)
            if len(per_cluster_df) > 0:
                cluster_path = os.path.join(OUTPUT_DIR, 'eif_oulad_per_cluster.csv')
                per_cluster_df.to_csv(cluster_path, index=False)
                print(f"\n  Per-cluster saved: {cluster_path}")
        except Exception as e:
            print(f"\n  OULAD failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ─── Save main results ───
    if all_rows:
        df = pd.DataFrame(all_rows)
        main_path = os.path.join(OUTPUT_DIR, 'eif_all_datasets.csv')
        df.to_csv(main_path, index=False)
        print(f"\n  Main results saved: {main_path}")
        
        # ─── Comparison table: EIF vs Substitution ───
        print("\n" + "█" * 70)
        print(" COMPARISON: SUBSTITUTION vs EIF ".center(70, "█"))
        print("█" * 70)
        
        comparison_rows = []
        for dataset in df['dataset'].unique():
            sub_row = df[(df['dataset']==dataset) & (df['method']=='Substitution')]
            eif_row = df[(df['dataset']==dataset) & (df['method']=='EIF')]
            
            if len(sub_row) > 0 and len(eif_row) > 0:
                sub_row = sub_row.iloc[0]
                eif_row = eif_row.iloc[0]
                
                comparison_rows.append({
                    'dataset': dataset,
                    'n': sub_row.get('n'),
                    'tau_substitution': sub_row.get('tau_total'),
                    'se_substitution': sub_row.get('se'),
                    'tau_EIF': eif_row.get('tau_total'),
                    'se_EIF': eif_row.get('se'),
                    'se_ratio_EIF_over_Sub': eif_row.get('se', 0) / max(sub_row.get('se', 1e-9), 1e-9),
                    'tau_diff': eif_row.get('tau_total', 0) - sub_row.get('tau_total', 0),
                })
        
        comp_df = pd.DataFrame(comparison_rows)
        comp_path = os.path.join(OUTPUT_DIR, 'eif_vs_substitution.csv')
        comp_df.to_csv(comp_path, index=False)
        
        print()
        cols_show = ['dataset', 'n', 'tau_substitution', 'tau_EIF', 'se_substitution', 'se_EIF', 'se_ratio_EIF_over_Sub']
        print(comp_df[cols_show].to_string(index=False))
        print(f"\n  Comparison saved: {comp_path}")
        
        # Key insight summary
        print("\n  KEY INSIGHT:")
        print(f"  SE ratio (EIF/Substitution) should be > 1 — EIF gives proper SE,")
        print(f"  Substitution underestimated SE in previous analyses.")
        print(f"  Mean SE ratio: {comp_df['se_ratio_EIF_over_Sub'].mean():.2f}")


if __name__ == '__main__':
    main()
