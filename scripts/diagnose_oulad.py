"""
OULAD Per-Cluster Diagnostic
=============================

Investigates the cross-method divergence on OULAD by:
    1. Running HC-DML on each module separately
    2. Checking if effects vary in SIGN across modules (heterogeneity)
    3. Comparing within-cluster vs marginal estimates
    4. Identifying which modules drive the overall estimate

If effects vary in sign across modules:
    → OULAD divergence is FEATURE (heterogeneity matters)
    → HC-DML correctly residualizes cluster
    → Naive incorrectly averages over heterogeneity

If effects are consistent across modules:
    → Divergence is BUG (something wrong with cluster handling)
    → Need to debug HC-DML cluster cross-fitting

USAGE:
    OULAD_PATH=~/oulad_data python scripts/diagnose_oulad.py
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
from sklearn.linear_model import Ridge, LogisticRegression, LinearRegression

OULAD_PATH = os.environ.get('OULAD_PATH', '~/oulad_data')
OULAD_PATH = os.path.expanduser(OULAD_PATH)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)

from loaders_oulad import load_oulad
from hcdml import HCDMLEstimator
from baselines import NaivePlugIn


# =========================================================================
# DIAGNOSTIC 1: Per-cluster HC-DML estimates
# =========================================================================

def per_cluster_analysis(data):
    """Run HC-DML on each module separately to detect heterogeneity."""
    
    print("\n" + "═" * 70)
    print(" DIAGNOSTIC 1: PER-CLUSTER ESTIMATES ".center(70, "═"))
    print("═" * 70)
    
    cluster_map = data['metadata']['cluster_map']
    cluster_inv = {v: k for k, v in cluster_map.items()}
    
    results = []
    
    for s_id in sorted(np.unique(data['S'])):
        mask = data['S'] == s_id
        n_s = mask.sum()
        cluster_name = cluster_inv[s_id]
        
        if n_s < 100:
            print(f"  Skipping cluster {cluster_name} (n={n_s} too small)")
            continue
        
        # Subset data
        Y_s = data['Y'][mask]
        A_s = data['A'][mask]
        M_s = data['M'][mask]
        X_s = data['X'][mask]
        S_s = np.zeros(n_s, dtype=int)  # Single cluster within subset
        
        # Check A balance and Y mean
        a_balance = A_s.mean()
        y_mean = Y_s.mean()
        
        # Skip if no variation
        if a_balance < 0.05 or a_balance > 0.95:
            print(f"  Skipping {cluster_name}: A unbalanced ({a_balance:.3f})")
            continue
        
        if y_mean < 0.05 or y_mean > 0.95:
            print(f"  Skipping {cluster_name}: Y unbalanced ({y_mean:.3f})")
            continue
        
        try:
            # Naive (simple regression)
            naive = NaivePlugIn(paths=['direct', 'via_M'], outcome_model='linear')
            r_naive = naive.fit(Y_s, A_s, M_s, X_s, S_s)
            
            # HC-DML
            est = HCDMLEstimator(
                paths=['direct', 'via_M'],
                n_folds=3, n_cluster_folds=1,
                outcome_learner=Ridge(alpha=1.0),
            )
            r_hcdml = est.fit(Y_s, A_s, M_s, X_s, S_s)
            
            # Simple OLS as sanity check  
            features = np.column_stack([X_s, A_s.reshape(-1, 1), M_s])
            ols = LinearRegression().fit(features, Y_s)
            ols_direct = ols.coef_[X_s.shape[1]]  # Coefficient on A
            
            results.append({
                'cluster': cluster_name,
                'n': n_s,
                'a_balance': a_balance,
                'y_mean': y_mean,
                'naive_total': r_naive.tau_pj_cf,
                'naive_direct': r_naive.tau_per_path['direct'],
                'naive_via_M': r_naive.tau_per_path['via_M'],
                'hcdml_total': r_hcdml.tau_pj_cf,
                'hcdml_direct': r_hcdml.tau_per_path['direct'],
                'hcdml_via_M': r_hcdml.tau_per_path['via_M'],
                'hcdml_se': r_hcdml.se,
                'ols_direct': ols_direct,
            })
            
        except Exception as e:
            print(f"  Failed {cluster_name}: {e}")
    
    df = pd.DataFrame(results)
    
    print(f"\n  Total clusters analyzed: {len(df)}")
    print()
    print(df[['cluster', 'n', 'a_balance', 'y_mean',
            'naive_total', 'hcdml_total', 'ols_direct']].to_string(index=False))
    
    # ─── Heterogeneity diagnosis ───
    print("\n  ┌─────────────────────────────────────────────┐")
    print("  │  HETEROGENEITY DIAGNOSIS                     │")
    print("  └─────────────────────────────────────────────┘")
    
    tau_values = df['hcdml_total'].values
    pos = (tau_values > 0.01).sum()
    neg = (tau_values < -0.01).sum()
    near_zero = ((tau_values >= -0.01) & (tau_values <= 0.01)).sum()
    
    print(f"  Clusters with positive τ:  {pos:>3} / {len(df)}")
    print(f"  Clusters with negative τ:  {neg:>3} / {len(df)}")
    print(f"  Clusters near zero:        {near_zero:>3} / {len(df)}")
    print(f"  τ range:                   [{tau_values.min():+.4f}, {tau_values.max():+.4f}]")
    print(f"  τ standard deviation:      {tau_values.std():.4f}")
    
    if pos > 2 and neg > 2:
        print(f"\n  → HETEROGENEITY DETECTED: effects vary in SIGN across modules")
        print(f"  → OULAD divergence is FEATURE, not bug")
        print(f"  → HC-DML correctly handles cluster-level heterogeneity")
        verdict = 'feature'
    elif tau_values.std() > 0.05:
        print(f"\n  → MODERATE HETEROGENEITY: effects vary in magnitude")
        print(f"  → Divergence partly explained by clustering")
        verdict = 'partial'
    else:
        print(f"\n  → HOMOGENEITY: effects consistent across modules")
        print(f"  → Divergence may indicate BUG in cluster handling")
        verdict = 'bug'
    
    return df, verdict


# =========================================================================
# DIAGNOSTIC 2: Marginal vs Conditional estimands
# =========================================================================

def compare_estimands(data, per_cluster_df):
    """Compare different estimands:
       1. Marginal: average effect across population (what Naive estimates)
       2. Within-cluster average: average of per-cluster effects (what HC-DML approximates)
       3. Cluster-weighted: weighted by cluster size
    """
    print("\n" + "═" * 70)
    print(" DIAGNOSTIC 2: ESTIMAND COMPARISON ".center(70, "═"))
    print("═" * 70)
    
    # Estimand 1: Naive marginal (from per_cluster_df)
    # This is what Naive computes — average over ALL observations
    
    # Estimand 2: Simple average of per-cluster effects (unweighted)
    eff_unweighted = per_cluster_df['hcdml_total'].mean()
    
    # Estimand 3: Cluster-size weighted average  
    eff_weighted = (per_cluster_df['hcdml_total'] * per_cluster_df['n']).sum() / per_cluster_df['n'].sum()
    
    # Estimand 4: Full-pooled OLS
    features = np.column_stack([data['X'], data['A'].reshape(-1, 1), data['M']])
    ols = LinearRegression().fit(features, data['Y'])
    ols_pooled = ols.coef_[data['X'].shape[1]]
    
    # Estimand 5: OLS with cluster fixed effects
    cluster_dummies = pd.get_dummies(data['S'], prefix='S', drop_first=True).values
    features_fe = np.column_stack([data['X'], data['A'].reshape(-1, 1), data['M'], cluster_dummies])
    ols_fe = LinearRegression().fit(features_fe, data['Y'])
    ols_fe_effect = ols_fe.coef_[data['X'].shape[1]]
    
    print(f"  Different estimands of the same parameter:")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Marginal OLS (pooled, no cluster):        {ols_pooled:+.4f}")
    print(f"  OLS with cluster fixed effects:           {ols_fe_effect:+.4f}")
    print(f"  Average of per-cluster HC-DML (unweighted): {eff_unweighted:+.4f}")
    print(f"  Average of per-cluster HC-DML (weighted):   {eff_weighted:+.4f}")
    
    return {
        'ols_pooled': ols_pooled,
        'ols_with_fe': ols_fe_effect,
        'cluster_avg_unweighted': eff_unweighted,
        'cluster_avg_weighted': eff_weighted,
    }


# =========================================================================
# DIAGNOSTIC 3: Specific module deep-dive
# =========================================================================

def module_deep_dive(data, per_cluster_df):
    """Examine modules with extreme effects to understand pattern."""
    
    print("\n" + "═" * 70)
    print(" DIAGNOSTIC 3: EXTREME MODULES ".center(70, "═"))
    print("═" * 70)
    
    # Sort by HC-DML estimate
    sorted_df = per_cluster_df.sort_values('hcdml_total')
    
    print("\n  Modules with MOST NEGATIVE effects (females lower):")
    print(sorted_df.head(3)[['cluster', 'n', 'hcdml_total', 'hcdml_direct', 'hcdml_via_M', 'y_mean']].to_string(index=False))
    
    print("\n  Modules with MOST POSITIVE effects (females higher):")
    print(sorted_df.tail(3)[['cluster', 'n', 'hcdml_total', 'hcdml_direct', 'hcdml_via_M', 'y_mean']].to_string(index=False))
    
    # Compute by module characteristics if we can infer
    # Module codes in OULAD: AAA, BBB, CCC, DDD, EEE, FFF, GGG
    # Typically: AAA/BBB/GGG are Social Sciences, CCC/DDD/EEE/FFF are STEM
    # This is documented in Kuzilek et al. 2017
    
    sorted_df['module_code'] = sorted_df['cluster'].str[:3]
    by_module = sorted_df.groupby('module_code').agg(
        avg_tau=('hcdml_total', 'mean'),
        n_presentations=('cluster', 'count'),
        total_n=('n', 'sum'),
    ).reset_index()
    
    print("\n  Effects by module code (course type):")
    print(by_module.to_string(index=False))


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("\n" + "█" * 70)
    print(" OULAD DIVERGENCE DIAGNOSTIC ".center(70, "█"))
    print("█" * 70)
    
    if not os.path.exists(OULAD_PATH):
        print(f"\n✗ OULAD_PATH not found: {OULAD_PATH}")
        return
    
    # Load OULAD
    print(f"\n  Loading OULAD from {OULAD_PATH}...")
    data = load_oulad(
        OULAD_PATH,
        protected='gender',
        outcome='pass_distinction',
        aggregate_clicks_by='cumulative',
        min_assessments=1,
        verbose=False,
    )
    
    print(f"\n  Loaded: n={data['metadata']['n']:,}, clusters={data['metadata']['n_clusters']}")
    
    # Run diagnostics
    per_cluster_df, verdict = per_cluster_analysis(data)
    
    # Save per-cluster results
    cluster_path = os.path.join(OUTPUT_DIR, 'oulad_per_cluster_diagnostic.csv')
    per_cluster_df.to_csv(cluster_path, index=False)
    print(f"\n  Saved: {cluster_path}")
    
    # Compare estimands
    estimands = compare_estimands(data, per_cluster_df)
    
    # Module deep-dive
    module_deep_dive(data, per_cluster_df)
    
    # Final verdict
    print("\n" + "█" * 70)
    print(" FINAL VERDICT ".center(70, "█"))
    print("█" * 70)
    
    if verdict == 'feature':
        print("\n  ✓ OULAD divergence is a FEATURE")
        print("    Effects vary in sign across modules.")
        print("    Different methods estimate different (legitimate) estimands.")
        print()
        print("  Interpretation for paper:")
        print("    - HC-DML estimates within-module average effect")
        print("    - Naive estimates marginal effect (averaged over module mix)")  
        print("    - These ARE different parameters")
        print("    - Reviewer-defensible because cluster structure matters")
    elif verdict == 'partial':
        print("\n  ~ MODERATE: heterogeneity partial explanation")
        print("    Recommend: report per-cluster results in paper appendix")
    else:
        print("\n  ✗ POTENTIAL BUG in cluster handling")
        print("    Recommend: debug HC-DML cross-fitting logic")
        print("    Check: stratification, fold creation, score aggregation")


if __name__ == '__main__':
    main()
