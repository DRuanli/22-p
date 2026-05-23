"""
Bootstrap Inference on All Real Datasets
=========================================

Runs cluster bootstrap on HC-DML for proper SE estimation across all
datasets. Reports point estimate + bootstrap SE + percentile CI.

Compares with the misleading original SE estimates.

EXPECTED RUNTIME:
    - UCI Math/Por:  2-3 minutes each (small)
    - xAPI:          2-3 minutes
    - Law School:    10-20 minutes (n=22K)
    - OULAD:         20-40 minutes (n=26K, cluster bootstrap)
    
    Total: ~30-70 minutes depending on hardware.

USAGE:
    # Set DATA_DIR and OULAD_PATH env vars, then:
    python scripts/bootstrap_all_datasets.py
    
    # Reduce iterations for faster testing:
    N_BOOT=50 python scripts/bootstrap_all_datasets.py
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
from sklearn.linear_model import Ridge

from hcdml import HCDMLEstimator
from bootstrap_inference import bootstrap_estimator
from loaders import load_uci_student, load_xapi

# Optional OULAD loader
try:
    from loaders_oulad import load_oulad
    HAS_OULAD_LOADER = True
except ImportError:
    HAS_OULAD_LOADER = False


# =========================================================================
# CONFIG
# =========================================================================

DATA_DIR = os.environ.get(
    'DATA_DIR',
    os.path.join(os.path.dirname(__file__), '..', 'data')
)
OULAD_PATH = os.environ.get('OULAD_PATH', '~/oulad_data')
OULAD_PATH = os.path.expanduser(OULAD_PATH)
LAW_PATH = os.environ.get(
    'LAW_PATH',
    os.path.join(os.path.dirname(__file__), '..', 'data', 'law_data.csv')
)

N_BOOTSTRAP = int(os.environ.get('N_BOOT', '200'))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================================
# WORKFLOW
# =========================================================================

def run_bootstrap_on_dataset(data, name, n_bootstrap=200, has_clusters=True):
    """Run cluster (or iid) bootstrap on a single dataset."""
    print("\n" + "═" * 70)
    print(f" BOOTSTRAP: {name} ".center(70, "═"))
    print("═" * 70)
    
    method = 'cluster' if has_clusters and data['metadata']['n_clusters'] > 1 else 'iid'
    
    print(f"\n  n = {data['metadata']['n']:,}")
    print(f"  clusters = {data['metadata']['n_clusters']}")
    print(f"  bootstrap method = {method}")
    print(f"  n_bootstrap = {n_bootstrap}")
    
    est = HCDMLEstimator(
        paths=['direct', 'via_M'],
        n_folds=3,
        n_cluster_folds=3 if data['metadata']['n_clusters'] > 5 else 1,
        outcome_learner=Ridge(alpha=1.0),
    )
    
    try:
        result = bootstrap_estimator(
            est,
            Y=data['Y'], A=data['A'],
            M=data['M'], X=data['X'], S=data['S'],
            n_bootstrap=n_bootstrap,
            method=method,
            verbose=True,
        )
        
        print(result.summary())
        
        return {
            'dataset': name,
            'n': data['metadata']['n'],
            'n_clusters': data['metadata']['n_clusters'],
            'method': method,
            'tau': result.tau_total,
            'boot_mean': result.bootstrap_mean,
            'boot_se': result.bootstrap_se,
            'boot_bias': result.bootstrap_bias,
            'ci_lower_pct': result.ci_percentile[0],
            'ci_upper_pct': result.ci_percentile[1],
            'ci_lower_norm': result.ci_normal[0],
            'ci_upper_norm': result.ci_normal[1],
            'p_value': result.p_value,
            'n_bootstrap_used': result.n_bootstrap,
        }
    except Exception as e:
        print(f"\n  ✗ Failed: {e}")
        return {'dataset': name, 'error': str(e)}


def main():
    print("\n" + "█" * 70)
    print(" BOOTSTRAP INFERENCE — ALL DATASETS ".center(70, "█"))
    print("█" * 70)
    print(f"\n  Bootstrap iterations: {N_BOOTSTRAP}")
    print(f"  (Set N_BOOT env var to change, e.g. N_BOOT=50 for fast testing)")
    
    results = []
    
    # ─── UCI Math ───
    path = os.path.join(DATA_DIR, 'student-mat.csv')
    if os.path.exists(path):
        try:
            data = load_uci_student(path, subject='math', outcome='G3', protected='sex')
            results.append(run_bootstrap_on_dataset(data, 'UCI_Math', N_BOOTSTRAP, has_clusters=False))
        except Exception as e:
            print(f"\n  UCI Math failed to load: {e}")
    
    # ─── UCI Portuguese ───
    path = os.path.join(DATA_DIR, 'student-por.csv')
    if os.path.exists(path):
        try:
            data = load_uci_student(path, subject='portuguese', outcome='G3', protected='sex')
            results.append(run_bootstrap_on_dataset(data, 'UCI_Portuguese', N_BOOTSTRAP, has_clusters=False))
        except Exception as e:
            print(f"\n  UCI Portuguese failed: {e}")
    
    # ─── xAPI ───
    path = os.path.join(DATA_DIR, 'xAPI-Edu-Data_csv.xls')
    if os.path.exists(path):
        try:
            data = load_xapi(path, outcome='class', protected='gender')
            results.append(run_bootstrap_on_dataset(data, 'xAPI', N_BOOTSTRAP, has_clusters=True))
        except Exception as e:
            print(f"\n  xAPI failed: {e}")
    
    # ─── Law School ───
    if os.path.exists(LAW_PATH):
        try:
            # Need to use whichever loader exists in the project
            # For now, use simple loader inline
            df = pd.read_csv(LAW_PATH)
            
            # Build minimal data dict (uses existing project conventions)
            data = _load_law_school_inline(df)
            results.append(run_bootstrap_on_dataset(data, 'Law_School', 
                                                   max(N_BOOTSTRAP // 2, 100),
                                                   has_clusters=False))
        except Exception as e:
            print(f"\n  Law School failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ─── OULAD ───
    if HAS_OULAD_LOADER and os.path.exists(OULAD_PATH):
        try:
            data = load_oulad(
                OULAD_PATH, protected='gender', outcome='pass_distinction',
                aggregate_clicks_by='cumulative', min_assessments=1, verbose=False,
            )
            # OULAD bootstrap is slow; reduce iterations
            results.append(run_bootstrap_on_dataset(
                data, 'OULAD', max(N_BOOTSTRAP // 4, 50), has_clusters=True
            ))
        except Exception as e:
            print(f"\n  OULAD failed: {e}")
    
    # ─── Save results ───
    if results:
        df_results = pd.DataFrame(results)
        path = os.path.join(OUTPUT_DIR, 'bootstrap_all_datasets.csv')
        df_results.to_csv(path, index=False)
        print(f"\n\nSaved: {path}")
        
        # Summary table
        print("\n" + "═" * 70)
        print(" SUMMARY: BOOTSTRAP vs ORIGINAL SE ".center(70, "═"))
        print("═" * 70)
        
        cols_to_show = ['dataset', 'n', 'tau', 'boot_se', 
                       'ci_lower_pct', 'ci_upper_pct', 'p_value']
        if all(c in df_results.columns for c in cols_to_show):
            print()
            print(df_results[cols_to_show].to_string(index=False))


def _load_law_school_inline(df):
    """Minimal inline Law School loader for bootstrap script.
    
    Note: produces same structure as full loader but inlined here
    to avoid dependency on user's specific Law School loader file.
    """
    # Race binarization: White = 1, others = 0
    race_col = 'race' if 'race' in df.columns else 'race1'
    A = (df[race_col].astype(str).str.lower() == 'white').astype(int).values
    
    # Outcome
    outcome_col = 'first_pf' if 'first_pf' in df.columns else 'pass_bar'
    Y = df[outcome_col].astype(int).values
    
    # Mediators
    M_cols = ['UGPA', 'LSAT'] if 'UGPA' in df.columns else ['ugpa', 'lsat']
    M = df[M_cols].values.astype(float)
    M_std = M.std(axis=0)
    M_std[M_std < 1e-6] = 1.0
    M = (M - M.mean(axis=0)) / M_std
    
    # Covariates (sex + region if available)
    X_cols = []
    if 'sex' in df.columns:
        X_cols.append(pd.get_dummies(df['sex'], drop_first=True).values)
    if 'region_first' in df.columns:
        X_cols.append(pd.get_dummies(df['region_first'], drop_first=True).values.astype(float))
    if X_cols:
        X = np.hstack(X_cols).astype(float)
    else:
        X = np.ones((len(df), 1))
    
    # No clusters
    S = np.zeros(len(df), dtype=int)
    
    return {
        'Y': Y, 'A': A.astype(float), 'M': M, 'X': X, 'S': S,
        'metadata': {
            'dataset': 'Law_School',
            'n': len(df),
            'n_clusters': 1,
            'A_balance': float(A.mean()),
            'Y_mean': float(Y.mean()),
        }
    }


if __name__ == '__main__':
    main()
