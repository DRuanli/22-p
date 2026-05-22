"""
OULAD: DAG Level C sensitivity analysis.

Tests whether OULAD findings are robust to the specification of the causal
DAG, specifically the assignment of variables to X (pre-treatment covariate)
vs M (mediator). This is a Level C sensitivity check (Robins, 2003;
Pearl, 2009) addressing assumption uncertainty rather than estimation error.

Three DAG specifications
------------------------
DAG 1 (default, as used in paper):
  X = {age_band, region, imd_band, highest_education, disability, 
       num_prev_attempts, studied_credits}
  M = {sum_clicks, first_assessment_score, avg_assessment_score, 
       days_late_registration}

DAG 2 (studied_credits as M):
  Hypothesis: studied_credits (course load) may be partially determined post-
  enrollment, making it a mediator of gender effects on outcomes via course
  selection behavior.
  X = {age_band, region, imd_band, highest_education, disability, 
       num_prev_attempts}
  M = {studied_credits, sum_clicks, first_assessment_score, 
       avg_assessment_score, days_late_registration}

DAG 3 (imd_band as M):
  Hypothesis: imd_band (socio-economic deprivation index) is a structural
  pre-treatment characteristic in classical view, BUT the relevant decile
  was assigned at the time of registration based on the student's neighborhood
  at that point; for students who relocated due to educational opportunities,
  it may reflect partly post-treatment circumstances. We test this DAG as a
  conservative sensitivity check.
  X = {age_band, region, highest_education, disability, num_prev_attempts, 
       studied_credits}
  M = {imd_band_numeric, sum_clicks, first_assessment_score, 
       avg_assessment_score, days_late_registration}

For each DAG, we re-run the EIF estimator with default density='gaussian'
and report the resulting tau_total, NDE, NIE, and per-cluster heterogeneity.

Run
---
Place in scripts/ directory:
    cd hcdml_project
    python scripts/dag_sensitivity_oulad.py
    
Approximate runtime: 90-120 minutes (3 OULAD runs).
"""

import os
import sys
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from algorithms.hcdml_eif import HCDMLEstimatorEIF
from loaders.loaders_oulad import load_oulad


def reassign_variable_to_M(data, var_name, source='X', target='M'):
    """
    Move a single variable from `source` to `target` in the data dict.
    
    Handles both:
    - Variable is in X (numerical column index given by feature_names_X)
    - Variable is in M (column index in feature_names_M)
    
    Returns a NEW data dict with the variable moved.
    """
    if source == 'X' and target == 'M':
        if var_name not in data.get('feature_names_X', []):
            raise ValueError(f"{var_name} not found in X feature names")
        idx = data['feature_names_X'].index(var_name)
        var_col = data['X'][:, idx:idx+1]
        
        new_data = dict(data)
        new_data['X'] = np.delete(data['X'], idx, axis=1)
        new_data['M'] = np.hstack([data['M'], var_col])
        new_data['feature_names_X'] = [n for n in data['feature_names_X'] if n != var_name]
        new_data['feature_names_M'] = list(data.get('feature_names_M', [])) + [var_name]
        return new_data
    else:
        raise NotImplementedError(f"Move from {source} to {target} not implemented")


def run_oulad_with_dag(data, dag_name, **estimator_kwargs):
    """Run EIF estimator on given data, return summary dict."""
    print(f"\n[{dag_name}] X dim = {data['X'].shape[1]}, M dim = {data['M'].shape[1]}, n = {len(data['Y'])}")
    
    t0 = time.time()
    est = HCDMLEstimatorEIF(
        K_outer=5,
        n_mc_samples=200,
        random_state=42,
        density_method='gaussian',
        clip_density_ratio=50.0,
        **estimator_kwargs,
    )
    est.fit(
        X=data['X'], A=data['A'], M=data['M'], Y=data['Y'], S=data['S'],
        cluster_id=data.get('cluster_id'),
    )
    runtime = time.time() - t0
    
    result = {
        'dag_name': dag_name,
        'X_dim': data['X'].shape[1],
        'M_dim': data['M'].shape[1],
        'M_vars': ', '.join(data.get('feature_names_M', [f'M{i}' for i in range(data['M'].shape[1])])),
        'tau_total': float(est.tau_PJ_CF_),
        'tau_NDE': float(est.tau_NDE_),
        'tau_NIE': float(est.tau_NIE_),
        'se_total': float(est.tau_PJ_CF_se_),
        'se_NDE': float(getattr(est, 'tau_NDE_se_', np.nan)),
        'se_NIE': float(getattr(est, 'tau_NIE_se_', np.nan)),
        'runtime_min': runtime / 60,
    }
    
    # Try per-cluster too (if estimator supports it)
    if hasattr(est, 'cluster_estimates_'):
        per_cluster = est.cluster_estimates_
        if per_cluster is not None:
            tau_per_cluster = per_cluster.get('tau_total', None)
            if tau_per_cluster is not None:
                result['cluster_range'] = f"[{np.min(tau_per_cluster):.3f}, {np.max(tau_per_cluster):.3f}]"
                result['cluster_sd'] = float(np.std(tau_per_cluster, ddof=1))
                # Cochran Q
                tau_arr = np.asarray(tau_per_cluster)
                se_arr = np.asarray(per_cluster.get('se_total', np.full_like(tau_arr, np.nan)))
                valid = ~np.isnan(se_arr) & (se_arr > 0)
                if valid.sum() > 1:
                    w = 1 / se_arr[valid] ** 2
                    theta_fixed = np.sum(w * tau_arr[valid]) / np.sum(w)
                    Q = np.sum(w * (tau_arr[valid] - theta_fixed) ** 2)
                    df = valid.sum() - 1
                    from scipy.stats import chi2
                    Q_p = float(1 - chi2.cdf(Q, df))
                    result['cochran_Q'] = float(Q)
                    result['cochran_df'] = int(df)
                    result['cochran_p'] = Q_p
                    result['I_squared_pct'] = float(max(0, (Q - df) / Q) * 100) if Q > 0 else 0.0
    
    print(f"  tau_total = {result['tau_total']:+.4f} (SE = {result['se_total']:.4f})")
    print(f"  NDE       = {result['tau_NDE']:+.4f}")
    print(f"  NIE       = {result['tau_NIE']:+.4f}")
    if 'cluster_range' in result:
        print(f"  Cluster range = {result['cluster_range']}, SD = {result['cluster_sd']:.4f}")
        print(f"  Cochran Q = {result.get('cochran_Q', np.nan):.2f}, df = {result.get('cochran_df', np.nan)}, p = {result.get('cochran_p', np.nan):.2e}, I² = {result.get('I_squared_pct', np.nan):.1f}%")
    print(f"  Runtime: {runtime/60:.1f} min")
    
    return result


def main():
    out_dir = 'results'
    os.makedirs(out_dir, exist_ok=True)
    
    print("=" * 80)
    print("OULAD DAG Level C Sensitivity Analysis")
    print("=" * 80)
    
    # Load OULAD with default DAG
    print("\n[Loading OULAD with default DAG]")
    data_default = load_oulad()
    print(f"  X vars ({len(data_default.get('feature_names_X', []))}): {data_default.get('feature_names_X')}")
    print(f"  M vars ({len(data_default.get('feature_names_M', []))}): {data_default.get('feature_names_M')}")
    
    # Alternative DAGs
    data_dag2 = reassign_variable_to_M(data_default, 'studied_credits')
    
    # For imd_band: it may be encoded as one-hot in X, need to handle differently
    # If imd_band_numeric exists in X, use it
    if 'imd_band' in data_default.get('feature_names_X', []):
        data_dag3 = reassign_variable_to_M(data_default, 'imd_band')
    elif 'imd_band_numeric' in data_default.get('feature_names_X', []):
        data_dag3 = reassign_variable_to_M(data_default, 'imd_band_numeric')
    else:
        # IMD might be one-hot encoded across multiple columns; skip or handle separately
        print("\n[WARNING] imd_band not found as single feature; DAG 3 will use a representative IMD encoding instead")
        # Find first imd_-prefixed column
        imd_cols = [n for n in data_default.get('feature_names_X', []) if 'imd' in n.lower()]
        if imd_cols:
            print(f"  Using {imd_cols[0]} as proxy for imd_band")
            data_dag3 = reassign_variable_to_M(data_default, imd_cols[0])
        else:
            print("  No IMD column found; DAG 3 skipped")
            data_dag3 = None
    
    results = []
    
    # DAG 1: default
    results.append(run_oulad_with_dag(data_default, 'DAG1_default'))
    
    # DAG 2: studied_credits as M
    results.append(run_oulad_with_dag(data_dag2, 'DAG2_studied_credits_as_M'))
    
    # DAG 3: imd_band as M (if available)
    if data_dag3 is not None:
        results.append(run_oulad_with_dag(data_dag3, 'DAG3_imd_band_as_M'))
    
    # Save
    df = pd.DataFrame(results)
    df.to_csv(f'{out_dir}/oulad_dag_sensitivity.csv', index=False)
    print(f"\nResults saved to {out_dir}/oulad_dag_sensitivity.csv")
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"{'DAG':<32} {'tau_total':>12} {'NDE':>10} {'NIE':>10}")
    for r in results:
        print(f"{r['dag_name']:<32} {r['tau_total']:>+12.4f} {r['tau_NDE']:>+10.4f} {r['tau_NIE']:>+10.4f}")
    
    if len(results) >= 2:
        max_delta_total = max(abs(r['tau_total'] - results[0]['tau_total']) for r in results[1:])
        max_delta_NDE = max(abs(r['tau_NDE'] - results[0]['tau_NDE']) for r in results[1:])
        max_delta_NIE = max(abs(r['tau_NIE'] - results[0]['tau_NIE']) for r in results[1:])
        print(f"\nMax deviation from default DAG:")
        print(f"  tau_total: ±{max_delta_total:.4f} ({max_delta_total / max(results[0]['se_total'], 1e-6):.1f} SE units)")
        print(f"  NDE      : ±{max_delta_NDE:.4f}")
        print(f"  NIE      : ±{max_delta_NIE:.4f}")
        
        # Sign-robustness check
        signs_total = [np.sign(r['tau_total']) for r in results]
        if len(set(signs_total)) == 1:
            print(f"\n[ROBUST] tau_total sign consistent across all {len(results)} DAGs")
        else:
            print(f"\n[FRAGILE] tau_total sign DIFFERS across DAGs: {signs_total}")


if __name__ == '__main__':
    main()