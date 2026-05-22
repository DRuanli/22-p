"""
OULAD: KDE vs Gaussian density ratio robustness check.

Purpose
-------
Verify that the OULAD findings (tau_total = +0.076, NDE = +0.230, NIE = -0.154)
are robust to the choice of mediator density estimator. OULAD's mediator
sum_clicks is heavily right-skewed (long-tailed distribution of engagement),
which is exactly the regime where Gaussian density approximation can bias the
path decomposition (NDE/NIE split) even when total tau is doubly-robust.

Runs both density methods and outputs:
- algorithms/hcdml_eif.py with density_method='gaussian' (default)
- algorithms/hcdml_eif.py with density_method='kernel' (patched via hcdml_eif_kde)

Outputs
-------
results/oulad_kde_vs_gaussian.csv
results/oulad_mediator_diagnostics.csv (skewness, kurtosis of each mediator)

Run
---
Place this in scripts/ directory of the hcdml_project. Then:
    cd hcdml_project
    python scripts/oulad_kde_comparison.py
    
Approximate runtime: 60-90 minutes (OULAD pipeline runs twice).
"""

import sys
import os
import time
import numpy as np
import pandas as pd

OULAD_PATH = os.environ.get('OULAD_PATH', '/Users/lenguyen/Documents/26-Research/unknown/hcdml_project/oulad_data')

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

# Import KDE patch FIRST
from algorithms.hcdml_eif_kde import patch_kde_support
patch_kde_support()

from algorithms.hcdml_eif import HCDMLEstimatorEIF
from data.loaders_oulad import load_oulad


def main():
    out_dir = 'results'
    os.makedirs(out_dir, exist_ok=True)
    
    print("=" * 80)
    print("OULAD: KDE vs Gaussian density ratio comparison")
    print("=" * 80)
    
    # Load OULAD
    print("\n[1/4] Loading OULAD...")
    t0 = time.time()
    data = load_oulad(OULAD_PATH, protected='gender', outcome='pass_distinction',
                aggregate_clicks_by='cumulative', min_assessments=1, verbose=False,)  # uses default DAG
    print(f"  n={len(data['Y'])}, L={len(np.unique(data['S']))}, M dim={data['M'].shape[1]}")
    print(f"  Load time: {time.time() - t0:.1f}s")
    
    # Mediator diagnostics: skewness, kurtosis
    print("\n[2/4] Computing mediator distributional diagnostics...")
    from scipy.stats import skew, kurtosis, jarque_bera
    
    med_diag = []
    med_names = data.get('feature_names_M', [f'M{i}' for i in range(data['M'].shape[1])])
    for j, mname in enumerate(med_names):
        m_vals = data['M'][:, j]
        m_clean = m_vals[~np.isnan(m_vals)]
        # Per-A residuals
        for a_val in [0, 1]:
            m_a = m_clean[data['A'][~np.isnan(m_vals)] == a_val]
            if len(m_a) < 30:
                continue
            sk = skew(m_a)
            kt = kurtosis(m_a)
            jb_stat, jb_p = jarque_bera(m_a)
            med_diag.append({
                'mediator': mname, 'A': a_val,
                'n': len(m_a),
                'mean': float(np.mean(m_a)),
                'sd': float(np.std(m_a)),
                'skewness': float(sk),
                'kurtosis_excess': float(kt),
                'jb_stat': float(jb_stat),
                'jb_p': float(jb_p),
                'normality_rejected_05': bool(jb_p < 0.05),
            })
            print(f"  {mname:30s} | A={a_val} | n={len(m_a):>6} | skew={sk:+.2f} | kurt={kt:+.2f} | JB p={jb_p:.1e}")
    
    pd.DataFrame(med_diag).to_csv(f'{out_dir}/oulad_mediator_diagnostics.csv', index=False)
    
    # Run both density methods
    results = []
    for density_method in ['gaussian', 'kernel']:
        print(f"\n[3/4] Running EIF with density_method='{density_method}'...")
        t0 = time.time()
        
        est = HCDMLEstimatorEIF(
            density_method=density_method,
            K_outer=5,
            n_mc_samples=200,
            random_state=42,
            clip_density_ratio=50.0,
        )
        est.fit(
            X=data['X'], A=data['A'], M=data['M'], Y=data['Y'], S=data['S'],
            cluster_id=data.get('cluster_id'),
        )
        
        tau_total = est.tau_PJ_CF_
        tau_NDE = est.tau_NDE_
        tau_NIE = est.tau_NIE_
        se_total = est.tau_PJ_CF_se_
        se_NDE = getattr(est, 'tau_NDE_se_', None)
        se_NIE = getattr(est, 'tau_NIE_se_', None)
        
        runtime = time.time() - t0
        print(f"  Runtime: {runtime/60:.1f} min")
        print(f"  tau_total = {tau_total:+.4f}  (SE = {se_total:.4f})")
        print(f"  NDE       = {tau_NDE:+.4f}")
        print(f"  NIE       = {tau_NIE:+.4f}")
        
        results.append({
            'density_method': density_method,
            'tau_total': tau_total,
            'tau_NDE': tau_NDE,
            'tau_NIE': tau_NIE,
            'se_total': se_total,
            'se_NDE': se_NDE,
            'se_NIE': se_NIE,
            'ci_total_lower': tau_total - 1.96 * se_total,
            'ci_total_upper': tau_total + 1.96 * se_total,
            'runtime_seconds': runtime,
        })
    
    # Comparison
    print("\n[4/4] Saving comparison CSV...")
    df = pd.DataFrame(results)
    df.to_csv(f'{out_dir}/oulad_kde_vs_gaussian.csv', index=False)
    
    # Compute differences
    g = df[df['density_method'] == 'gaussian'].iloc[0]
    k = df[df['density_method'] == 'kernel'].iloc[0]
    print("\n=== COMPARISON ===")
    print(f"{'Quantity':<15} {'Gaussian':>12} {'KDE':>12} {'Δ':>12} {'%Δ':>8}")
    for col in ['tau_total', 'tau_NDE', 'tau_NIE']:
        delta = k[col] - g[col]
        pct = 100 * delta / abs(g[col]) if g[col] != 0 else float('nan')
        print(f"{col:<15} {g[col]:>+12.4f} {k[col]:>+12.4f} {delta:>+12.4f} {pct:>+7.1f}%")
    
    print(f"\nResults saved to {out_dir}/")
    print("\nNext steps:")
    print("  - If |Δ tau_total| < 1 * SE: total estimate is robust to density choice (expected per double robustness)")
    print("  - If |Δ NDE|, |Δ NIE| > 2 * SE: path decomposition is sensitive — report KDE as robustness check")
    print("  - If both decompositions are similar: explicit confirmation that Gaussian approximation is adequate for OULAD")


if __name__ == '__main__':
    main()