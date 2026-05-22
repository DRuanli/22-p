"""
Comprehensive Sensitivity Analysis for All Datasets
=====================================================

Runs three levels of sensitivity analysis using verified EIF estimator:
    A. ψ sensitivity (pedagogical justifiability)
    B. Unobserved confounding bounds (Marginal Sensitivity Model)
    C. DAG specification sensitivity (alternative variable assignments)

Output files:
    - results/sensitivity_psi_all.csv: τ vs ψ for each dataset
    - results/sensitivity_confounding_all.csv: bounds vs Γ for each dataset
    - results/sensitivity_dag_oulad.csv: alternative DAGs for OULAD

USAGE:
    DATA_DIR=/path/to/data OULAD_PATH=~/oulad_data \\
    LAW_PATH=data/law_data.csv python scripts/sensitivity_all_datasets.py

    # Quick run (fewer Γ values):
    QUICK=1 python scripts/sensitivity_all_datasets.py

EXPECTED RUNTIME: 30-60 minutes (longer cho large datasets).

INTERPRETATION GUIDE:
    Γ break point > 2.0  → robust to unobserved confounding
    Γ break point 1.5-2.0 → moderately robust
    Γ break point < 1.5  → fragile, sensitive to confounding
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
from sensitivity import (
    psi_sensitivity_analysis,
    confounding_sensitivity_analysis,
    dag_sensitivity_analysis,
)

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

QUICK = bool(int(os.environ.get('QUICK', '0')))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================================
# MAIN
# =========================================================================

def run_sensitivity(data, name):
    """Run all sensitivity analyses on one dataset."""
    print("\n" + "═" * 70)
    print(f" {name} (n={data['metadata']['n']:,}, clusters={data['metadata']['n_clusters']}) ".center(70, "═"))
    print("═" * 70)
    
    n_cluster_folds = min(3, data['metadata']['n_clusters']) if data['metadata']['n_clusters'] > 1 else 1
    
    # Build estimator
    estimator_params = {
        'paths': ['direct', 'via_M'],
        'n_folds': 3,
        'n_cluster_folds': n_cluster_folds,
        'outcome_learner': Ridge(alpha=1.0),
        'propensity_learner': LogisticRegression(max_iter=1000),
        'min_n_for_eif': 500,  # Don't warn for smaller datasets
    }
    
    est = HCDMLEstimatorEIF(**estimator_params)
    
    # ─── Level A: ψ sensitivity ───
    print(f"\n  Level A: ψ Sensitivity")
    psi_grid = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    
    try:
        r_psi = psi_sensitivity_analysis(
            est, data['Y'], data['A'], data['M'], data['X'], data['S'],
            psi_grid=psi_grid,
            path_to_vary='via_M',
            verbose=False,
        )
        psi_rows = []
        for i, psi_val in enumerate(psi_grid):
            psi_rows.append({
                'dataset': name,
                'psi_via_M': psi_val,
                'tau': r_psi.tau_estimates[i],
                'ci_lower': r_psi.ci_lower[i],
                'ci_upper': r_psi.ci_upper[i],
            })
        print(f"    ψ range: [{r_psi.tau_estimates.min():+.4f}, {r_psi.tau_estimates.max():+.4f}]")
        print(f"    Sign robust: {r_psi.sign_robust}")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        psi_rows = []
    
    # ─── Level B: Confounding sensitivity ───
    print(f"\n  Level B: Confounding Sensitivity")
    
    if QUICK:
        gamma_grid = np.array([1.0, 1.5, 2.0])
    else:
        gamma_grid = np.array([1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0])
    
    try:
        # Need fresh estimator (Level A modified it)
        est_for_conf = HCDMLEstimatorEIF(**estimator_params)
        
        r_conf = confounding_sensitivity_analysis(
            est_for_conf, data['Y'], data['A'], data['M'], data['X'], data['S'],
            gamma_grid=gamma_grid,
            verbose=False,
        )
        conf_rows = []
        for i, gamma in enumerate(gamma_grid):
            conf_rows.append({
                'dataset': name,
                'gamma': gamma,
                'tau_lower': r_conf.tau_lower[i],
                'tau_upper': r_conf.tau_upper[i],
                'sign_preserved': (np.sign(r_conf.tau_lower[i]) == np.sign(r_conf.tau_upper[i])
                                   and r_conf.tau_lower[i] != 0),
            })
        print(f"    Point τ̂ = {r_conf.tau_point:+.4f}")
        if r_conf.gamma_break_point is not None:
            print(f"    Break point: Γ ≈ {r_conf.gamma_break_point:.2f}")
            print(f"    Qualitative robust: {r_conf.qualitative_robust}")
        else:
            print(f"    Qualitatively robust across all tested Γ")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        conf_rows = []
    
    return psi_rows, conf_rows


def main():
    print("\n" + "█" * 70)
    print(" COMPREHENSIVE SENSITIVITY ANALYSIS ".center(70, "█"))
    print("█" * 70)
    
    print(f"\n  QUICK mode: {QUICK}")
    print(f"  DATA_DIR:   {DATA_DIR}")
    print(f"  LAW_PATH:   {LAW_PATH}")
    print(f"  OULAD_PATH: {OULAD_PATH}")
    
    all_psi_rows = []
    all_conf_rows = []
    
    # ─── Each dataset ───
    
    # UCI Math
    path = os.path.join(DATA_DIR, 'student-mat.csv')
    if os.path.exists(path):
        try:
            data = load_uci_student(path, subject='math', outcome='G3', protected='sex')
            p, c = run_sensitivity(data, 'UCI_Math')
            all_psi_rows.extend(p); all_conf_rows.extend(c)
        except Exception as e:
            print(f"\n  UCI Math failed: {e}")
    
    # UCI Portuguese
    path = os.path.join(DATA_DIR, 'student-por.csv')
    if os.path.exists(path):
        try:
            data = load_uci_student(path, subject='portuguese', outcome='G3', protected='sex')
            p, c = run_sensitivity(data, 'UCI_Portuguese')
            all_psi_rows.extend(p); all_conf_rows.extend(c)
        except Exception as e:
            print(f"\n  UCI Portuguese failed: {e}")
    
    # xAPI
    path = os.path.join(DATA_DIR, 'xAPI-Edu-Data_csv.xls')
    if os.path.exists(path):
        try:
            data = load_xapi(path, outcome='class', protected='gender')
            p, c = run_sensitivity(data, 'xAPI')
            all_psi_rows.extend(p); all_conf_rows.extend(c)
        except Exception as e:
            print(f"\n  xAPI failed: {e}")
    
    # Law School
    if os.path.exists(LAW_PATH):
        try:
            data = load_law_school(LAW_PATH)
            p, c = run_sensitivity(data, 'Law_School')
            all_psi_rows.extend(p); all_conf_rows.extend(c)
        except Exception as e:
            print(f"\n  Law School failed: {e}")
    
    # OULAD
    if HAS_OULAD and os.path.exists(OULAD_PATH):
        try:
            data = load_oulad(
                OULAD_PATH, protected='gender', outcome='pass_distinction',
                aggregate_clicks_by='cumulative', min_assessments=1, verbose=False,
            )
            p, c = run_sensitivity(data, 'OULAD')
            all_psi_rows.extend(p); all_conf_rows.extend(c)
        except Exception as e:
            print(f"\n  OULAD failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ─── Save results ───
    if all_psi_rows:
        psi_df = pd.DataFrame(all_psi_rows)
        psi_path = os.path.join(OUTPUT_DIR, 'sensitivity_psi_all.csv')
        psi_df.to_csv(psi_path, index=False)
        print(f"\n  Saved: {psi_path}")
    
    if all_conf_rows:
        conf_df = pd.DataFrame(all_conf_rows)
        conf_path = os.path.join(OUTPUT_DIR, 'sensitivity_confounding_all.csv')
        conf_df.to_csv(conf_path, index=False)
        print(f"  Saved: {conf_path}")
    
    # ─── Summary table ───
    print("\n" + "█" * 70)
    print(" SUMMARY ".center(70, "█"))
    print("█" * 70)
    
    if all_conf_rows:
        # For each dataset, find smallest Γ where bounds cross 0
        conf_df = pd.DataFrame(all_conf_rows)
        summary_rows = []
        for dataset in conf_df['dataset'].unique():
            sub = conf_df[conf_df['dataset'] == dataset].sort_values('gamma')
            # First gamma where bounds cross zero
            crossed = sub[~sub['sign_preserved']]
            if len(crossed) > 0:
                break_gamma = crossed.iloc[0]['gamma']
                summary_rows.append({
                    'dataset': dataset,
                    'gamma_break': break_gamma,
                    'qualitative_robust': break_gamma > 2.0,
                })
            else:
                summary_rows.append({
                    'dataset': dataset,
                    'gamma_break': float('inf'),
                    'qualitative_robust': True,
                })
        
        summary_df = pd.DataFrame(summary_rows)
        print()
        print(summary_df.to_string(index=False))


if __name__ == '__main__':
    main()