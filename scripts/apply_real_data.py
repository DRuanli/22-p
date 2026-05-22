"""
Real Data Application: Path-Specific Counterfactual Fairness
=============================================================

Applies HC-DML and baselines to real educational datasets:
    - UCI Student Performance (math + Portuguese)
    - xAPI Educational dataset

HONEST INTERPRETATION GUIDE:
    - We do NOT have ground truth on real data
    - Cannot say which method is "correct"
    - Reports method AGREEMENT and divergence
    - Strong disagreement = sensitivity to assumptions
    - Convergence across methods = robust finding

The "fairness violation" we report is conditional on:
    1. The chosen DAG (mediator vs covariate distinction)
    2. The chosen ψ values (justifiability of paths)
    3. Identification assumptions (unconfoundedness, etc.)

We test SENSITIVITY by varying these choices.

USAGE:
    # Update DATA_DIR to point to your local CSV files
    python scripts/apply_real_data.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'algorithms'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from loaders import load_uci_student, load_xapi, print_dataset_summary
from hcdml import HCDMLEstimator
from baselines import NaivePlugIn, SingleLevelDML, ChiappaVAE


# =========================================================================
# CONFIGURATION — UPDATE THESE PATHS
# =========================================================================

# Update to your local paths
DATA_DIR = '/mnt/user-data/uploads'  # Where the CSV files are

PATH_UCI_MATH = os.path.join(DATA_DIR, 'student-mat.csv')
PATH_UCI_POR = os.path.join(DATA_DIR, 'student-por.csv')
PATH_XAPI = os.path.join(DATA_DIR, 'xAPI-Edu-Data_csv.xls')  # despite extension, is CSV

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================================
# METHOD RUNNER
# =========================================================================

def run_all_methods(data, name, paths=('direct', 'via_M'), psi=None):
    """Run all methods on a real dataset."""
    if psi is None:
        psi = {'direct': 0.0, 'via_M': 0.0}
    
    results = []
    
    methods_config = [
        ('Naive', NaivePlugIn(paths=list(paths), psi=psi, outcome_model='linear', bootstrap_n=0)),
        ('SingleLevelDML', SingleLevelDML(paths=list(paths), psi=psi, n_folds=3)),
        ('ChiappaVAE', ChiappaVAE(paths=list(paths), psi=psi, bootstrap_n=0)),
        ('HC-DML', HCDMLEstimator(
            paths=list(paths), psi=psi,
            n_folds=3, n_cluster_folds=3 if data['metadata']['n_clusters'] > 5 else 1,
            outcome_learner=Ridge(alpha=1.0),
            verbose=False,
        )),
    ]
    
    for method_name, estimator in methods_config:
        try:
            r = estimator.fit(
                Y=data['Y'], A=data['A'],
                M=data['M'], X=data['X'], S=data['S']
            )
            row = {
                'dataset': name,
                'method': method_name,
                'tau_total': r.tau_pj_cf,
                'tau_direct': r.tau_per_path.get('direct', np.nan),
                'tau_via_M': r.tau_per_path.get('via_M', np.nan),
                'se': r.se,
                'ci_lower': r.ci_lower,
                'ci_upper': r.ci_upper,
                'p_value': r.p_value,
                'n': data['metadata']['n'],
            }
        except Exception as e:
            row = {
                'dataset': name,
                'method': method_name,
                'error': str(e),
            }
        results.append(row)
    
    return pd.DataFrame(results)


# =========================================================================
# SENSITIVITY ANALYSIS
# =========================================================================

def sensitivity_to_psi(data, name):
    """Show how PJ-CF changes with different psi values for via_M path.
    
    psi['via_M'] = 0   : via_M path UNJUSTIFIED (counts in violation)
    psi['via_M'] = 1   : via_M path JUSTIFIED (does NOT count)
    
    This shows the sensitivity of conclusions to pedagogical justification.
    """
    print(f"\n--- Sensitivity to ψ (via_M) for {name} ---")
    
    estimator = HCDMLEstimator(
        paths=['direct', 'via_M'],
        n_folds=3, n_cluster_folds=3 if data['metadata']['n_clusters'] > 5 else 1,
        outcome_learner=Ridge(alpha=1.0),
    )
    
    psi_values = [0.0, 0.25, 0.5, 0.75, 1.0]
    rows = []
    
    for psi_val in psi_values:
        estimator.psi = {'direct': 0.0, 'via_M': psi_val}
        r = estimator.fit(
            Y=data['Y'], A=data['A'],
            M=data['M'], X=data['X'], S=data['S']
        )
        rows.append({
            'dataset': name,
            'psi_via_M': psi_val,
            'tau_PJ_CF': r.tau_pj_cf,
            'ci_lower': r.ci_lower,
            'ci_upper': r.ci_upper,
        })
    
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    return df


# =========================================================================
# MAIN ANALYSIS
# =========================================================================

def main():
    print("\n" + "█" * 70)
    print(" REAL DATA APPLICATION: PSCF ".center(70, "█"))
    print("█" * 70)
    
    all_results = []
    all_sensitivity = []
    
    # ─────────────────────────────────────────────────────────────────────
    # UCI Student Performance (Math)
    # ─────────────────────────────────────────────────────────────────────
    if os.path.exists(PATH_UCI_MATH):
        try:
            data = load_uci_student(
                PATH_UCI_MATH, 
                subject='math', 
                outcome='G3',
                protected='sex',
            )
            print_dataset_summary(data, "UCI Student (Math) — sex → G3")
            
            results = run_all_methods(data, 'UCI_Math_sex_G3')
            print("\nResults:")
            print(results[['method', 'tau_total', 'tau_direct', 'tau_via_M', 
                          'se', 'ci_lower', 'ci_upper', 'p_value']].to_string(index=False))
            all_results.append(results)
            
            # Sensitivity to ψ
            sens = sensitivity_to_psi(data, 'UCI_Math_sex_G3')
            all_sensitivity.append(sens)
        except Exception as e:
            print(f"  Error on UCI Math: {e}")
    else:
        print(f"\n  SKIPPED: {PATH_UCI_MATH} not found")
    
    # ─────────────────────────────────────────────────────────────────────
    # UCI Student Performance (Portuguese)
    # ─────────────────────────────────────────────────────────────────────
    if os.path.exists(PATH_UCI_POR):
        try:
            data = load_uci_student(
                PATH_UCI_POR,
                subject='portuguese',
                outcome='G3',
                protected='sex',
            )
            print_dataset_summary(data, "UCI Student (Portuguese) — sex → G3")
            
            results = run_all_methods(data, 'UCI_Por_sex_G3')
            print("\nResults:")
            print(results[['method', 'tau_total', 'tau_direct', 'tau_via_M',
                          'se', 'ci_lower', 'ci_upper', 'p_value']].to_string(index=False))
            all_results.append(results)
            
            sens = sensitivity_to_psi(data, 'UCI_Por_sex_G3')
            all_sensitivity.append(sens)
        except Exception as e:
            print(f"  Error on UCI Portuguese: {e}")
    else:
        print(f"\n  SKIPPED: {PATH_UCI_POR} not found")
    
    # ─────────────────────────────────────────────────────────────────────
    # xAPI Educational
    # ─────────────────────────────────────────────────────────────────────
    if os.path.exists(PATH_XAPI):
        try:
            data = load_xapi(
                PATH_XAPI,
                outcome='class',
                protected='gender',
            )
            print_dataset_summary(data, "xAPI — gender → Class")
            
            results = run_all_methods(data, 'xAPI_gender_class')
            print("\nResults:")
            print(results[['method', 'tau_total', 'tau_direct', 'tau_via_M',
                          'se', 'ci_lower', 'ci_upper', 'p_value']].to_string(index=False))
            all_results.append(results)
            
            sens = sensitivity_to_psi(data, 'xAPI_gender_class')
            all_sensitivity.append(sens)
        except Exception as e:
            print(f"  Error on xAPI: {e}")
    else:
        print(f"\n  SKIPPED: {PATH_XAPI} not found")
    
    # ─────────────────────────────────────────────────────────────────────
    # Aggregate and save
    # ─────────────────────────────────────────────────────────────────────
    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        path = os.path.join(OUTPUT_DIR, 'real_data_results.csv')
        combined.to_csv(path, index=False)
        print(f"\n\nResults saved: {path}")
        
        # Cross-method comparison
        print("\n" + "═" * 70)
        print(" METHOD AGREEMENT ANALYSIS ".center(70, "═"))
        print("═" * 70)
        
        for ds in combined['dataset'].unique():
            sub = combined[combined['dataset'] == ds]
            taus = sub['tau_total'].dropna().values
            if len(taus) > 1:
                rng = taus.max() - taus.min()
                ratio = rng / max(abs(taus.mean()), 1e-6)
                print(f"\n{ds}:")
                print(f"  Tau range: [{taus.min():+.4f}, {taus.max():+.4f}]")
                print(f"  Spread/mean: {ratio:.2%}")
                if ratio > 0.5:
                    print(f"  ⚠ HIGH disagreement — interpretation requires caution")
                else:
                    print(f"  ✓ Reasonable agreement across methods")
    
    if all_sensitivity:
        sens_combined = pd.concat(all_sensitivity, ignore_index=True)
        path = os.path.join(OUTPUT_DIR, 'real_data_sensitivity.csv')
        sens_combined.to_csv(path, index=False)
        print(f"\nSensitivity saved: {path}")
    
    print("\n" + "█" * 70)
    print(" ANALYSIS COMPLETE ".center(70, "█"))
    print("█" * 70)
    
    print("\nINTERPRETATION CHECKLIST:")
    print("  1. Did all methods produce similar tau? (Robustness)")
    print("  2. Does tau move significantly with ψ? (Pedagogical sensitivity)")
    print("  3. Are CIs narrow enough for actionable conclusions? (Sample size)")
    print("  4. Direction matches prior expectations? (Face validity)")
    print()
    print("REMEMBER: No ground truth on real data. Interpret tau as")
    print("'extent of unjustified path-specific dependence between A and Y'")
    print("conditional on chosen DAG and ψ values.")


if __name__ == '__main__':
    main()
