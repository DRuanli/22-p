"""
Multiple Testing Correction and Heterogeneity Test for OULAD Per-Cluster Analysis
===================================================================================

Adds BH-FDR adjusted p-values, Bonferroni p-values, and Cochran's Q heterogeneity
test to the per-cluster OULAD results.

INPUT:
    results/eif_oulad_per_cluster.csv (output from rerun_all_datasets_eif.py)

OUTPUT:
    results/eif_oulad_per_cluster_corrected.csv (with p_bh, p_bonferroni columns)
    results/oulad_heterogeneity_test.csv (Cochran Q, I², DerSimonian-Laird τ²)

USAGE:
    python scripts/multiple_testing_oulad.py

ADDRESSES:
    Reviewer concern: "22 clusters tested without multiple-testing correction
    inflates Type-I error. After Bonferroni or BH-FDR, are findings still
    significant?"

KEY OUTPUT METRIC: Cochran's Q test for omnibus heterogeneity, which addresses
'are cluster effects different from each other?' as a single primary test
(no multiple comparisons issue).

References:
    Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate:
        a practical and powerful approach to multiple testing.
        Journal of the Royal Statistical Society, Series B, 57(1), 289-300.

    Cochran, W. G. (1954). The combination of estimates from different
        experiments. Biometrics, 10(1), 101-129.

    DerSimonian, R., & Laird, N. (1986). Meta-analysis in clinical trials.
        Controlled Clinical Trials, 7(3), 177-188.

    Higgins, J. P., & Thompson, S. G. (2002). Quantifying heterogeneity in a
        meta-analysis. Statistics in Medicine, 21(11), 1539-1558.

    Higgins, J. P., Thompson, S. G., Deeks, J. J., & Altman, D. G. (2003).
        Measuring inconsistency in meta-analyses. BMJ, 327(7414), 557-560.
"""

import sys
import os
import argparse

import numpy as np
import pandas as pd
from scipy import stats


# =========================================================================
# CORE STATISTICAL FUNCTIONS
# =========================================================================

def benjamini_hochberg_adjust(p_values: np.ndarray) -> np.ndarray:
    """Compute Benjamini-Hochberg FDR-adjusted p-values.

    Procedure:
        1. Sort p-values ascending: p_(1) ≤ p_(2) ≤ ... ≤ p_(m)
        2. Compute raw adjusted: p_BH_(i) = p_(i) * m / i
        3. Enforce monotonicity from right: p_BH_(i) = min(p_BH_(i), p_BH_(i+1), ...)
        4. Cap at 1.0

    Parameters
    ----------
    p_values : array of shape (m,)
        Raw p-values from m independent tests.

    Returns
    -------
    adjusted : array of shape (m,)
        BH-adjusted p-values, in same order as input.

    References
    ----------
    Benjamini & Hochberg (1995).
    """
    p_values = np.asarray(p_values, dtype=float)
    n = len(p_values)
    if n == 0:
        return np.array([])

    order = np.argsort(p_values)
    sorted_p = p_values[order]

    # Raw BH: p_(i) * m/i, where i is 1-indexed rank
    bh_raw = sorted_p * n / (np.arange(n) + 1)

    # Enforce monotonicity from largest to smallest (running min from right)
    bh_monotonic = np.minimum.accumulate(bh_raw[::-1])[::-1]
    bh_monotonic = np.minimum(bh_monotonic, 1.0)

    # Restore original order
    adjusted = np.empty_like(bh_monotonic)
    adjusted[order] = bh_monotonic
    return adjusted


def cochran_q_test(estimates: np.ndarray, standard_errors: np.ndarray) -> dict:
    """Compute Cochran's Q test for heterogeneity across subgroup effects.

    Tests H0: all subgroup effects are equal (homogeneity)
    against H1: at least one subgroup differs.

    Q = Σ w_i (θ_i - θ_bar)²
        where w_i = 1/SE_i² and θ_bar = Σ(w_i θ_i) / Σ(w_i)
    Under H0, Q ~ χ²(m-1)

    Also returns:
        - I² statistic: % of variation due to heterogeneity (Higgins 2003)
        - DerSimonian-Laird estimator of between-cluster variance τ²

    Parameters
    ----------
    estimates : array, shape (m,)
        Subgroup-specific estimates θ_i.
    standard_errors : array, shape (m,)
        Standard errors SE_i of subgroup estimates.

    Returns
    -------
    dict with keys: Q, df, p_value, I_squared_pct, tau_squared_DL,
        tau_DL_SD, theta_fixed_effect, n_clusters.
    """
    estimates = np.asarray(estimates, dtype=float)
    ses = np.asarray(standard_errors, dtype=float)

    if np.any(ses <= 0):
        raise ValueError("All standard errors must be positive.")

    m = len(estimates)
    if m < 2:
        raise ValueError("Need at least 2 subgroups.")

    # Inverse-variance weights
    w = 1.0 / (ses ** 2)
    theta_fixed = np.sum(w * estimates) / np.sum(w)

    # Q statistic
    Q = float(np.sum(w * (estimates - theta_fixed) ** 2))
    df = m - 1
    p_value = float(1 - stats.chi2.cdf(Q, df))

    # I² statistic (Higgins 2003)
    I_squared = max(0.0, (Q - df) / Q) * 100 if Q > 0 else 0.0

    # DerSimonian-Laird τ² estimator
    C = float(np.sum(w) - np.sum(w ** 2) / np.sum(w))
    tau_squared_DL = max(0.0, (Q - df) / C) if C > 0 else 0.0

    return {
        'Q': Q,
        'df': df,
        'p_value': p_value,
        'I_squared_pct': I_squared,
        'tau_squared_DL': tau_squared_DL,
        'tau_DL_SD': float(np.sqrt(tau_squared_DL)),
        'theta_fixed_effect': float(theta_fixed),
        'n_clusters': m,
    }


def add_multiple_testing_corrections(df: pd.DataFrame,
                                     p_col: str = 'p_value') -> pd.DataFrame:
    """Add BH-FDR and Bonferroni adjusted p-values to a results DataFrame.

    Parameters
    ----------
    df : DataFrame
        Must contain column named `p_col` with raw p-values.
    p_col : str
        Name of the raw p-value column. Default 'p_value'.

    Returns
    -------
    DataFrame with added columns: p_bh, p_bonferroni, sig_raw_05,
    sig_bh_05, sig_bonf_05, sig_bh_10.
    """
    if p_col not in df.columns:
        raise ValueError(f"Column '{p_col}' not found. Available: {df.columns.tolist()}")

    df = df.copy()
    p_raw = df[p_col].values
    m = len(p_raw)

    df['p_bh'] = benjamini_hochberg_adjust(p_raw)
    df['p_bonferroni'] = np.minimum(p_raw * m, 1.0)

    df['sig_raw_05'] = df[p_col] < 0.05
    df['sig_bh_05'] = df['p_bh'] < 0.05
    df['sig_bonf_05'] = df['p_bonferroni'] < 0.05
    df['sig_bh_10'] = df['p_bh'] < 0.10

    return df


# =========================================================================
# MAIN ANALYSIS
# =========================================================================

def main(args):
    input_path = args.input
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print("\n" + "█" * 70)
    print(" MULTIPLE TESTING & HETEROGENEITY: OULAD PER-CLUSTER ".center(70, "█"))
    print("█" * 70)

    print(f"\n  Input:      {input_path}")
    print(f"  Output dir: {output_dir}")

    # Load
    df = pd.read_csv(input_path)
    m = len(df)
    print(f"  Clusters:   {m}")

    # Required columns
    required = ['cluster', 'tau_eif', 'se', 'p_value']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # ─── 1. Multiple testing corrections ───
    print("\n" + "─" * 70)
    print("  1. MULTIPLE TESTING CORRECTIONS")
    print("─" * 70)

    df = add_multiple_testing_corrections(df, p_col='p_value')

    print(f"\n  Bonferroni threshold (α/m): {0.05/m:.6f}")
    print()
    print(f"  Significant at α=0.05:")
    print(f"    Raw p-value:       {df['sig_raw_05'].sum()}/{m}")
    print(f"    BH-FDR adjusted:   {df['sig_bh_05'].sum()}/{m}")
    print(f"    Bonferroni:        {df['sig_bonf_05'].sum()}/{m}")
    print()
    print(f"  Significant at α=0.10:")
    print(f"    BH-FDR adjusted:   {df['sig_bh_10'].sum()}/{m}")

    # ─── 2. Heterogeneity test ───
    print("\n" + "─" * 70)
    print("  2. COCHRAN's Q TEST FOR HETEROGENEITY")
    print("─" * 70)

    het = cochran_q_test(df['tau_eif'].values, df['se'].values)

    print(f"\n  Q statistic:             {het['Q']:.2f}")
    print(f"  Degrees of freedom:      {het['df']}")
    print(f"  P-value:                 {het['p_value']:.4g}")
    print(f"  I² statistic:            {het['I_squared_pct']:.1f}%")
    print(f"  τ² (DerSimonian-Laird):  {het['tau_squared_DL']:.6f}")
    print(f"  τ (between-cluster SD):  {het['tau_DL_SD']:.4f}")
    print(f"  Fixed-effect estimate:   {het['theta_fixed_effect']:+.4f}")

    # Interpretation
    print()
    if het['p_value'] < 0.001:
        print(f"  → Strong evidence of heterogeneity (p={het['p_value']:.4g})")
    elif het['p_value'] < 0.05:
        print(f"  → Significant heterogeneity (p={het['p_value']:.4g})")
    else:
        print(f"  → No significant heterogeneity")

    if het['I_squared_pct'] >= 75:
        print(f"  → High heterogeneity (I²={het['I_squared_pct']:.0f}%)")
    elif het['I_squared_pct'] >= 50:
        print(f"  → Moderate heterogeneity (I²={het['I_squared_pct']:.0f}%)")
    elif het['I_squared_pct'] >= 25:
        print(f"  → Low heterogeneity (I²={het['I_squared_pct']:.0f}%)")
    else:
        print(f"  → Minimal heterogeneity (I²={het['I_squared_pct']:.0f}%)")

    # ─── 3. Sorted table ───
    print("\n" + "─" * 70)
    print("  3. TOP CLUSTERS BY SIGNIFICANCE")
    print("─" * 70)

    sorted_df = df.sort_values('p_value')
    display_cols = ['cluster', 'n', 'a_balance', 'tau_eif',
                    'p_value', 'p_bh', 'p_bonferroni']
    available_cols = [c for c in display_cols if c in sorted_df.columns]

    print()
    print(sorted_df.head(8)[available_cols].to_string(index=False, float_format=lambda x: f"{x:.4g}"))

    # ─── 4. Save outputs ───
    out_corrected = os.path.join(output_dir, 'eif_oulad_per_cluster_corrected.csv')
    df.to_csv(out_corrected, index=False)
    print(f"\n  Saved: {out_corrected}")

    out_het = os.path.join(output_dir, 'oulad_heterogeneity_test.csv')
    het_df = pd.DataFrame({
        'statistic': list(het.keys()),
        'value': list(het.values()),
    })
    het_df.to_csv(out_het, index=False)
    print(f"  Saved: {out_het}")

    print("\n" + "█" * 70)
    print(" DONE ".center(70, "█"))
    print("█" * 70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--input',
        default=os.path.join(os.path.dirname(__file__), '..', 'results',
                            'eif_oulad_per_cluster.csv'),
        help='Path to per-cluster OULAD results CSV',
    )
    parser.add_argument(
        '--output-dir',
        default=os.path.join(os.path.dirname(__file__), '..', 'results'),
        help='Directory to write corrected outputs',
    )
    args = parser.parse_args()
    main(args)