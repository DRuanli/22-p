"""
Unified Multi-Dataset Application Script
==========================================

Runs HC-DML + baselines on all available educational fairness datasets:
    1. UCI Student Math
    2. UCI Student Portuguese  
    3. xAPI Educational
    4. Law School Admissions (LSAC) — Kusner 2017 benchmark
    5. UC Berkeley Admissions — Chiappa 2019 benchmark
    6. OULAD — large-scale online learning
    7. PISA (optional, slow) — 3-level hierarchy

Skips datasets where files are not present.

USAGE:
    # Set paths via environment variables, then:
    python scripts/apply_all_datasets.py

PATH OVERRIDES (env vars):
    UCI_MATH_PATH       (default: ~/data/student-mat.csv)
    UCI_POR_PATH        (default: ~/data/student-por.csv)
    XAPI_PATH           (default: ~/data/xAPI-Edu-Data_csv.xls)
    LAW_PATH            (default: ~/data/law_data.csv)
    BERKELEY_PATH       (default: ~/data/berkeley.csv)
    OULAD_PATH          (default: ~/data/oulad_data/)
    PISA_PATH           (default: ~/data/CY08MSP_STU_QQQ.csv)
    SKIP_PISA           (default: 1 — set 0 to enable PISA)
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
from sklearn.linear_model import Ridge

# Algorithms
from hcdml import HCDMLEstimator
from baselines import NaivePlugIn, SingleLevelDML, ChiappaVAE

# Loaders
from loaders import load_uci_student, load_xapi


# =========================================================================
# CONFIGURATION
# =========================================================================

PATHS = {
    'UCI_Math':       os.environ.get('UCI_MATH_PATH', os.path.expanduser('~/data/student-mat.csv')),
    'UCI_Portuguese': os.environ.get('UCI_POR_PATH',  os.path.expanduser('~/data/student-por.csv')),
    'xAPI':           os.environ.get('XAPI_PATH',     os.path.expanduser('~/data/xAPI-Edu-Data_csv.xls')),
    'Law_School':     os.environ.get('LAW_PATH',      os.path.expanduser('~/data/law_data.csv')),
    'Berkeley':       os.environ.get('BERKELEY_PATH', os.path.expanduser('~/data/berkeley.csv')),
    'OULAD':          os.environ.get('OULAD_PATH',    os.path.expanduser('~/data/oulad_data')),
    'PISA':           os.environ.get('PISA_PATH',     os.path.expanduser('~/data/CY08MSP_STU_QQQ.csv')),
}

SKIP_PISA = os.environ.get('SKIP_PISA', '1') == '1'
SKIP_OULAD = os.environ.get('SKIP_OULAD', '0') == '1'

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================================
# UNIVERSAL METHOD RUNNER
# =========================================================================

def run_all_methods(data, dataset_name, verbose=True):
    """Run all 4 methods on a loaded dataset."""
    if verbose:
        print(f"\n  → Running methods on {dataset_name}...")
    
    methods = [
        ('Naive', NaivePlugIn(paths=['direct', 'via_M'])),
        ('SingleLevelDML', SingleLevelDML(paths=['direct', 'via_M'], n_folds=3)),
        ('ChiappaVAE', ChiappaVAE(paths=['direct', 'via_M'], bootstrap_n=0)),
        ('HC-DML', HCDMLEstimator(
            paths=['direct', 'via_M'],
            n_folds=3, 
            n_cluster_folds=3 if data['metadata']['n_clusters'] > 5 else 1,
            outcome_learner=Ridge(alpha=1.0),
        )),
    ]
    
    results = []
    for method_name, est in methods:
        t0 = time.time()
        try:
            r = est.fit(Y=data['Y'], A=data['A'], M=data['M'], X=data['X'], S=data['S'])
            results.append({
                'dataset': dataset_name,
                'method': method_name,
                'n': data['metadata']['n'],
                'n_clusters': data['metadata']['n_clusters'],
                'tau_total': r.tau_pj_cf,
                'tau_direct': r.tau_per_path.get('direct', np.nan),
                'tau_via_M': r.tau_per_path.get('via_M', np.nan),
                'se': r.se,
                'ci_lower': r.ci_lower,
                'ci_upper': r.ci_upper,
                'p_value': r.p_value,
                'time_s': time.time() - t0,
            })
            if verbose:
                print(f"    {method_name:<18}: τ={r.tau_pj_cf:+.4f}  CI=[{r.ci_lower:+.4f}, {r.ci_upper:+.4f}]")
        except Exception as e:
            if verbose:
                print(f"    {method_name:<18}: FAILED — {e}")
            results.append({
                'dataset': dataset_name,
                'method': method_name,
                'error': str(e),
            })
    
    return pd.DataFrame(results)


# =========================================================================
# DATASET LOADERS
# =========================================================================

def try_load(loader_fn, path, dataset_name, **kwargs):
    """Try to load a dataset, return None if file missing."""
    if not os.path.exists(path):
        print(f"  ✗ SKIP {dataset_name}: file not found at {path}")
        return None
    try:
        return loader_fn(path, **kwargs)
    except Exception as e:
        print(f"  ✗ ERROR loading {dataset_name}: {e}")
        return None


def main():
    print("\n" + "█" * 70)
    print(" MULTI-DATASET HC-DML APPLICATION ".center(70, "█"))
    print("█" * 70)
    
    all_results = []
    
    # ─── 1. UCI Math ───
    print(f"\n{'─' * 70}\n[1/7] UCI Student (Math)\n{'─' * 70}")
    data = try_load(
        load_uci_student, PATHS['UCI_Math'], 'UCI_Math',
        subject='math', outcome='G3', protected='sex'
    )
    if data is not None:
        all_results.append(run_all_methods(data, 'UCI_Math'))
    
    # ─── 2. UCI Portuguese ───
    print(f"\n{'─' * 70}\n[2/7] UCI Student (Portuguese)\n{'─' * 70}")
    data = try_load(
        load_uci_student, PATHS['UCI_Portuguese'], 'UCI_Portuguese',
        subject='portuguese', outcome='G3', protected='sex'
    )
    if data is not None:
        all_results.append(run_all_methods(data, 'UCI_Portuguese'))
    
    # ─── 3. xAPI ───
    print(f"\n{'─' * 70}\n[3/7] xAPI Educational\n{'─' * 70}")
    data = try_load(
        load_xapi, PATHS['xAPI'], 'xAPI',
        outcome='class', protected='gender'
    )
    if data is not None:
        all_results.append(run_all_methods(data, 'xAPI'))
    
    # ─── 4. Law School ───
    print(f"\n{'─' * 70}\n[4/7] Law School Admissions (LSAC)\n{'─' * 70}")
    if os.path.exists(PATHS['Law_School']):
        try:
            from loaders_law_school import load_law_school
            data = load_law_school(PATHS['Law_School'], protected='race', outcome='zfygpa')
            all_results.append(run_all_methods(data, 'Law_School'))
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
    else:
        print(f"  ✗ SKIP: file not found at {PATHS['Law_School']}")
    
    # ─── 5. Berkeley Admission ───
    print(f"\n{'─' * 70}\n[5/7] UC Berkeley Admissions\n{'─' * 70}")
    if os.path.exists(PATHS['Berkeley']):
        try:
            from loaders_berkeley import load_berkeley_admission
            data = load_berkeley_admission(PATHS['Berkeley'])
            all_results.append(run_all_methods(data, 'Berkeley'))
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
    else:
        print(f"  ✗ SKIP: file not found at {PATHS['Berkeley']}")
    
    # ─── 6. OULAD ───
    print(f"\n{'─' * 70}\n[6/7] OULAD\n{'─' * 70}")
    if SKIP_OULAD:
        print(f"  ✗ SKIP: SKIP_OULAD=1")
    elif os.path.exists(PATHS['OULAD']):
        try:
            from loaders_oulad import load_oulad
            data = load_oulad(
                PATHS['OULAD'], protected='gender', outcome='pass_distinction',
                aggregate_clicks_by='cumulative', min_assessments=1, verbose=True,
            )
            all_results.append(run_all_methods(data, 'OULAD'))
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
    else:
        print(f"  ✗ SKIP: directory not found at {PATHS['OULAD']}")
    
    # ─── 7. PISA ───
    print(f"\n{'─' * 70}\n[7/7] PISA (optional, slow)\n{'─' * 70}")
    if SKIP_PISA:
        print(f"  ✗ SKIP: SKIP_PISA=1 (set SKIP_PISA=0 to enable)")
    elif os.path.exists(PATHS['PISA']):
        try:
            from loaders_pisa import load_pisa
            data = load_pisa(
                PATHS['PISA'],
                outcome='math', protected='gender',
                # Optional: filter to specific countries / subsample for speed
                # countries=['VNM', 'KOR', 'JPN'],
                n_sample=50000,  # Subsample for tractability
                verbose=True,
            )
            all_results.append(run_all_methods(data, 'PISA'))
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
    else:
        print(f"  ✗ SKIP: file not found at {PATHS['PISA']}")
    
    # ─── Aggregate ───
    if not all_results:
        print(f"\n\n✗ No datasets loaded successfully. Check file paths.")
        return
    
    combined = pd.concat(all_results, ignore_index=True)
    out_path = os.path.join(OUTPUT_DIR, 'all_datasets_results.csv')
    combined.to_csv(out_path, index=False)
    
    print(f"\n\n{'═' * 70}")
    print(" SUMMARY ".center(70, "═"))
    print(f"{'═' * 70}")
    print(f"\n  Results saved: {out_path}")
    print(f"\n  Datasets analyzed: {combined['dataset'].nunique()}")
    print(f"  Total method × dataset runs: {len(combined)}")
    
    # Per-dataset comparison
    print(f"\n  Cross-method consistency (HC-DML vs others):")
    print(f"  {'Dataset':<20} {'HC-DML τ':<12} {'Method range':<15} {'Disagreement'}")
    print(f"  {'─' * 70}")
    
    for ds in combined['dataset'].unique():
        sub = combined[(combined['dataset'] == ds) & combined['tau_total'].notna()]
        if len(sub) == 0:
            continue
        hc = sub[sub['method'] == 'HC-DML']['tau_total']
        if len(hc) == 0:
            continue
        hc_val = hc.values[0]
        all_taus = sub['tau_total'].values
        tau_range = all_taus.max() - all_taus.min()
        disagreement_pct = tau_range / max(abs(hc_val), 0.01) * 100
        flag = '⚠' if disagreement_pct > 30 else '✓'
        print(f"  {ds:<20} {hc_val:+.4f}     [{all_taus.min():+.3f}, {all_taus.max():+.3f}]  "
              f"{disagreement_pct:.0f}% {flag}")


if __name__ == '__main__':
    main()
