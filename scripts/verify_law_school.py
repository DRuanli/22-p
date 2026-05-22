"""
Law School Encoding Verification
=================================

Verifies the semantics of the Law School (LSAC) dataset:
    1. Outcome direction: does first_pf=1 mean PASS or FAIL?
    2. Race encoding consistency
    3. Sample comparison with Kusner 2017 / Chiappa 2019 reported numbers
    4. DAG specification sanity (mediator/outcome relationships)

USAGE:
    python scripts/verify_law_school.py
    
    # Or specify path:
    LAW_PATH=/path/to/law_data.csv python scripts/verify_law_school.py
"""

import sys
import os
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

LAW_PATH = os.environ.get(
    'LAW_PATH', 
    os.path.join(os.path.dirname(__file__), '..', 'data', 'law_data.csv')
)


def main():
    print("\n" + "█" * 70)
    print(" LAW SCHOOL DATASET VERIFICATION ".center(70, "█"))
    print("█" * 70)
    
    if not os.path.exists(LAW_PATH):
        print(f"\n✗ Law School data not found: {LAW_PATH}")
        print(f"  Set LAW_PATH env variable or place file at default location.")
        return
    
    print(f"\n  Loading: {LAW_PATH}")
    df = pd.read_csv(LAW_PATH)
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")
    
    # ─── Diagnostic 1: Outcome variable analysis ───
    print("\n" + "═" * 70)
    print(" DIAGNOSTIC 1: OUTCOME VARIABLE (first_pf) ".center(70, "═"))
    print("═" * 70)
    
    if 'first_pf' in df.columns:
        outcome_col = 'first_pf'
    elif 'pass_bar' in df.columns:
        outcome_col = 'pass_bar'
    elif 'bar1' in df.columns:
        outcome_col = 'bar1'
    else:
        print(f"  ✗ No standard outcome column found")
        print(f"  Available: {df.columns.tolist()}")
        return
    
    print(f"\n  Outcome column: {outcome_col}")
    print(f"\n  Value distribution:")
    val_counts = df[outcome_col].value_counts(dropna=False)
    print(val_counts.to_string())
    print(f"\n  Mean = {df[outcome_col].mean():.4f}")
    print(f"  Missing: {df[outcome_col].isna().sum()}")
    
    # Interpretation
    mean_val = df[outcome_col].mean()
    if 0.05 <= mean_val <= 0.15:
        print(f"\n  ⚠ Mean {mean_val:.3f} is LOW for 'pass bar' (expect 70-90%)")
        print(f"     Possible interpretation: '1' = FAIL or 'first attempt fail'")
        print(f"     Need additional context to determine direction")
    elif 0.7 <= mean_val <= 0.95:
        print(f"\n  ✓ Mean {mean_val:.3f} consistent with bar pass rate (1 = pass)")
    else:
        print(f"\n  ? Mean {mean_val:.3f} unusual, manual verification needed")
    
    # ─── Diagnostic 2: Outcome by race ───
    print("\n" + "═" * 70)
    print(" DIAGNOSTIC 2: OUTCOME BY RACE ".center(70, "═"))
    print("═" * 70)
    
    if 'race' in df.columns:
        race_col = 'race'
    elif 'race1' in df.columns:
        race_col = 'race1'
    else:
        print(f"  No race column found")
        race_col = None
    
    if race_col:
        # Standardize race values
        race_vals = df[race_col].astype(str).str.lower()
        print(f"\n  Race categories:")
        print(df[race_col].value_counts().to_string())
        
        # Cross-tab race × outcome
        print(f"\n  Outcome rates by race:")
        crosstab = pd.crosstab(df[race_col], df[outcome_col], normalize='index') * 100
        print(crosstab.round(2).to_string())
        
        # Identify White vs non-White comparison
        white_mask = df[race_col].astype(str).str.lower() == 'white'
        if white_mask.sum() > 0:
            white_rate = df.loc[white_mask, outcome_col].mean()
            nonwhite_rate = df.loc[~white_mask, outcome_col].mean()
            gap = white_rate - nonwhite_rate
            
            print(f"\n  White outcome rate:     {white_rate:.4f}")
            print(f"  Non-White outcome rate: {nonwhite_rate:.4f}")
            print(f"  Gap (White - Non-White): {gap:+.4f}")
            
            if gap > 0:
                print(f"\n  → '1' is the DESIRABLE outcome (Whites have higher rate)")
                print(f"     Interpretation: 1 = PASSED")
                if mean_val < 0.5:
                    print(f"  ⚠ But overall mean is low ({mean_val:.3f})")
                    print(f"     Possible: dataset is filtered/restricted population")
            else:
                print(f"\n  → '1' is likely the UNDESIRABLE outcome (Whites have lower rate)")
                print(f"     Interpretation: 1 = FAILED or 'failed first attempt'")
                print(f"     Should FLIP outcome: Y_corrected = 1 - first_pf")
    
    # ─── Diagnostic 3: Compare with reference numbers ───
    print("\n" + "═" * 70)
    print(" DIAGNOSTIC 3: REFERENCE COMPARISON ".center(70, "═"))
    print("═" * 70)
    
    print(f"\n  Published reference points (Wightman 1998, Kusner 2017):")
    print(f"    Full LSAC: ~27,000 students, bar pass rate 86.7% overall")
    print(f"    Among Whites:  ~95% pass")
    print(f"    Among Blacks:  ~78% pass")
    print(f"    Gap:           ~17 percentage points")
    print()
    print(f"  Your data:")
    print(f"    n = {len(df):,}")
    if 'race' in df.columns:
        white_n = (df[race_col].astype(str).str.lower() == 'white').sum()
        print(f"    White n = {white_n:,}")
        print(f"    Non-White n = {len(df) - white_n:,}")
    
    # ─── Diagnostic 4: Mediator (LSAT, UGPA) distribution ───
    print("\n" + "═" * 70)
    print(" DIAGNOSTIC 4: MEDIATOR DISTRIBUTIONS ".center(70, "═"))
    print("═" * 70)
    
    if 'LSAT' in df.columns:
        print(f"\n  LSAT score distribution:")
        print(f"    Mean = {df['LSAT'].mean():.2f}")
        print(f"    Std  = {df['LSAT'].std():.2f}")
        print(f"    Range: [{df['LSAT'].min():.1f}, {df['LSAT'].max():.1f}]")
        print(f"  Expected: LSAT ~120-180 scale, mean ~150")
    
    if 'UGPA' in df.columns:
        print(f"\n  UGPA distribution:")
        print(f"    Mean = {df['UGPA'].mean():.2f}")
        print(f"    Std  = {df['UGPA'].std():.2f}")
        print(f"    Range: [{df['UGPA'].min():.2f}, {df['UGPA'].max():.2f}]")
        print(f"  Expected: UGPA ~0-4 scale, mean ~3.0-3.3")
    
    if 'ZFYA' in df.columns:
        print(f"\n  ZFYA (Z-score first year GPA):")
        print(f"    Mean = {df['ZFYA'].mean():.4f} (should be ~0)")
        print(f"    Std  = {df['ZFYA'].std():.4f} (should be ~1)")
    
    # ─── Diagnostic 5: DAG sanity checks ───
    print("\n" + "═" * 70)
    print(" DIAGNOSTIC 5: DAG SANITY ".center(70, "═"))
    print("═" * 70)
    
    if 'LSAT' in df.columns and 'UGPA' in df.columns:
        # LSAT and UGPA should be positively correlated
        lsat_ugpa_cor = df[['LSAT', 'UGPA']].corr().iloc[0, 1]
        print(f"\n  Correlation LSAT × UGPA: {lsat_ugpa_cor:+.3f}")
        print(f"    Expected: moderate positive (~0.4-0.6)")
        
        if 'race' in df.columns:
            white_mask = df[race_col].astype(str).str.lower() == 'white'
            print(f"\n  By race:")
            print(f"    Mean LSAT (White):     {df.loc[white_mask, 'LSAT'].mean():.2f}")
            print(f"    Mean LSAT (Non-White): {df.loc[~white_mask, 'LSAT'].mean():.2f}")
            print(f"    Mean UGPA (White):     {df.loc[white_mask, 'UGPA'].mean():.3f}")
            print(f"    Mean UGPA (Non-White): {df.loc[~white_mask, 'UGPA'].mean():.3f}")
    
    if 'sex' in df.columns:
        print(f"\n  Sex distribution:")
        print(df['sex'].value_counts().to_string())
    
    # ─── Final summary ───
    print("\n" + "█" * 70)
    print(" SUMMARY ".center(70, "█"))
    print("█" * 70)
    
    print(f"\n  Dataset: Law School (LSAC), n={len(df):,}")
    print(f"  Outcome: {outcome_col}, mean = {mean_val:.4f}")
    
    if mean_val < 0.2:
        print(f"\n  ⚠ ACTION NEEDED: outcome mean is suspiciously low")
        print(f"    Likely the outcome is 'failure-coded' (1 = bad outcome)")
        print(f"    To match HC-DML convention (1 = desirable), update loader:")
        print(f"      Y = 1 - df['{outcome_col}'].values")
        print()
        print(f"    Then re-interpret τ:")
        print(f"      Original τ = +0.72 means race effect on FAILURE rate")
        print(f"      Flipped τ would be -0.72 = race effect on PASS rate")
        print(f"      → Whites have lower failure rate (consistent with literature)")
    else:
        print(f"\n  ✓ Outcome direction appears correct")


if __name__ == '__main__':
    main()
