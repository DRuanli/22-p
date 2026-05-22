"""
Law School Admissions Dataset Loader (LSAC)
=============================================

Wightman (1998). LSAC National Longitudinal Bar Passage Study.
~21,790 students, used as the standard benchmark in counterfactual 
fairness literature.

POSSIBLE DATA SOURCES (the user must obtain themselves):
    1. AIF360 package: 
       `from aif360.datasets import LawSchoolGPADataset`
       Provides processed CSV under aif360/data/raw/law_school/
    
    2. Kusner et al. 2017 GitHub replication:
       https://github.com/mkusner/counterfactual-fairness
       Contains `law_data.csv`
    
    3. tempeh benchmark package:
       `pip install tempeh`
       `from tempeh.configurations import datasets`
    
    4. LSAC archive (academic request):
       https://www.lsac.org/lsacresources/research/

EXPECTED SCHEMA (after preprocessing, regardless of source):
    Columns we look for:
        race        : str (categorical: White, Black, Asian, Hispanic, ...)
                     OR
        race_white  : binary 0/1
                     OR
        white       : binary 0/1
                     (we'll detect which is present)
        
        sex / gender / female : binary or categorical (M/F)
        
        LSAT / lsat : numerical (Law School Admission Test score, 120-180)
        
        UGPA / undergrad_GPA / ugpa : numerical (undergraduate GPA, 0-4)
        
        ZFYA / first_year_GPA / zfygpa : numerical (first year law school GPA, 
                                          standardized)
                                          
        pass_bar (optional): binary (bar exam pass)

CAUSAL DAG (following Kusner 2017):
    A : race (binary: White=1) and/or sex (binary: Female=1)
    X : (none — race and sex are root causes)
    M : ugpa, lsat  (BOTH affected by race/sex via systemic bias)
    Y : zfygpa (first year law school GPA)
    
    Path-specific consideration:
        race → ugpa → zfygpa  (mediator path: prior academic prep)
        race → lsat → zfygpa  (mediator path: test performance)
        race → zfygpa         (direct effect)
    
    Whether mediator paths are "fair" is debated:
        - Test scores influenced by societal racism → arguably UNFAIR pathway
        - Academic preparation reflects opportunity → UNFAIR pathway
        - Same as Chiappa 2019's interpretation for similar cases

CLUSTER STRUCTURE:
    - No natural clusters in standard LSAC distribution
    - Some versions include `school_id` (162 law schools) — strong cluster!
    - We'll detect and use if available

USAGE:
    >>> from loaders_law_school import load_law_school
    >>> data = load_law_school('/path/to/law_data.csv')
    >>> # Or specify column mapping if your CSV uses different names:
    >>> data = load_law_school('/path/to/data.csv', 
    ...                        col_mapping={'race_col': 'ethnicity'})
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, List

import numpy as np
import pandas as pd


# Standard column name aliases — we try multiple names
COLUMN_ALIASES = {
    'lsat': ['lsat', 'LSAT', 'LSAT_score', 'lsat_score'],
    'ugpa': ['ugpa', 'UGPA', 'undergrad_GPA', 'undergraduate_GPA', 'ugpa_score'],
    'zfygpa': ['zfygpa', 'ZFYA', 'first_year_GPA', 'fyGPA', 'fy_gpa', 'FYA'],
    'race': ['race', 'ethnicity', 'race_white', 'white', 'is_white'],
    'sex': ['sex', 'gender', 'female', 'is_female', 'male'],
    'pass_bar': ['pass_bar', 'pass_bar1', 'bar_passed', 'bar'],
    'school_id': ['school_id', 'schoolID', 'cluster_id', 'law_school_id'],
}


def _find_column(df: pd.DataFrame, target: str) -> Optional[str]:
    """Find which alias is present in dataframe."""
    aliases = COLUMN_ALIASES.get(target, [target])
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def load_law_school(
    dataset_path: str,
    protected: str = 'race',  # 'race' or 'sex'
    outcome: str = 'zfygpa',
    binarize_protected: bool = True,
    col_mapping: Optional[Dict[str, str]] = None,
    verbose: bool = True,
) -> Dict[str, np.ndarray]:
    """Load Law School Admissions dataset for HC-DML.
    
    Parameters
    ----------
    dataset_path : str
        Path to CSV file containing Law School data.
    protected : str
        'race' (binarize as White vs Non-White) or 'sex' (Female=1).
    outcome : str
        'zfygpa' (first year GPA, default Kusner 2017 outcome)
        OR 'pass_bar' (binary bar exam pass, if available)
    binarize_protected : bool
        If True, race coded as White=1 vs Non-White=0.
        If False, raises error (current implementation requires binary A).
    col_mapping : dict, optional
        Override default column detection. Keys: 'lsat', 'ugpa', 'zfygpa', 
        'race', 'sex', 'pass_bar', 'school_id'.
    verbose : bool
        Print loading info.
    
    Returns
    -------
    dict with keys: Y, A, M, X, S, feature_names, metadata
    """
    df = pd.read_csv(dataset_path)
    
    if verbose:
        print(f"\n{'═' * 60}")
        print(f" Loading Law School from {dataset_path} ".center(60, "═"))
        print(f"{'═' * 60}")
        print(f"  Raw shape: {df.shape}")
        print(f"  Raw columns: {list(df.columns)}")
    
    # Apply user-specified mapping
    col_mapping = col_mapping or {}
    
    # Detect columns
    cols = {}
    for key in ['lsat', 'ugpa', 'zfygpa', 'race', 'sex', 'pass_bar', 'school_id']:
        if key in col_mapping:
            cols[key] = col_mapping[key]
        else:
            cols[key] = _find_column(df, key)
    
    if verbose:
        print(f"\n  Column detection:")
        for k, v in cols.items():
            status = "✓" if v else "✗"
            print(f"    {status} {k:<12} → {v}")
    
    # Verify required columns
    required = ['ugpa', 'lsat', 'zfygpa', 'race', 'sex']
    missing = [k for k in required if cols.get(k) is None]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Available columns: {list(df.columns)}. "
            f"Use col_mapping={{ 'lsat': 'your_lsat_col', ... }} to override."
        )
    
    # ─── Protected attribute ───
    if protected == 'race':
        race_col = cols['race']
        race_vals = df[race_col]
        
        if pd.api.types.is_numeric_dtype(race_vals):
            # Already binary or numeric coding
            A = race_vals.astype(float).values
            # If 0/1, assume 1=White; if other coding, user must specify
            if set(np.unique(A)) <= {0.0, 1.0}:
                if verbose:
                    print(f"  Race already binary (assume 1=White)")
            else:
                # Try to interpret: 1 typically = White in many LSAC versions
                A = (race_vals == 1).astype(float).values
        else:
            # String categorical
            race_str = race_vals.astype(str).str.lower().str.strip()
            white_aliases = {'white', '1', 'caucasian', 'w'}
            A = race_str.isin(white_aliases).astype(float).values
            if verbose:
                unique_races = race_vals.unique()
                print(f"  Race categories found: {list(unique_races)}")
                print(f"  Coding: White → 1, others → 0")
    
    elif protected == 'sex':
        sex_col = cols['sex']
        sex_vals = df[sex_col]
        
        if pd.api.types.is_numeric_dtype(sex_vals):
            A = sex_vals.astype(float).values
            if verbose:
                print(f"  Sex already binary")
        else:
            sex_str = sex_vals.astype(str).str.lower().str.strip()
            female_aliases = {'female', 'f', '1', 'woman', 'women'}
            A = sex_str.isin(female_aliases).astype(float).values
            if verbose:
                print(f"  Coding: Female → 1, others → 0")
    else:
        raise ValueError(f"Unknown protected: {protected}")
    
    # ─── Outcome ───
    if outcome == 'zfygpa':
        zfygpa_col = cols['zfygpa']
        Y = pd.to_numeric(df[zfygpa_col], errors='coerce').values.astype(float)
    elif outcome == 'pass_bar':
        if cols['pass_bar'] is None:
            raise ValueError("pass_bar column not found")
        Y_raw = df[cols['pass_bar']]
        if pd.api.types.is_numeric_dtype(Y_raw):
            Y = Y_raw.astype(float).values
        else:
            Y_str = Y_raw.astype(str).str.lower().str.strip()
            Y = Y_str.isin({'yes', '1', 'true', 'passed', 'pass'}).astype(float).values
    else:
        raise ValueError(f"Unknown outcome: {outcome}")
    
    # ─── Mediators (LSAT, UGPA) ───
    M_cols = []
    M_names = []
    
    for med_key in ['ugpa', 'lsat']:
        col = cols[med_key]
        if col is None:
            continue
        vals = pd.to_numeric(df[col], errors='coerce')
        # Fill missing with median (limitation: should be MAR, may not be true)
        vals = vals.fillna(vals.median())
        M_cols.append(vals.values.astype(float))
        M_names.append(med_key)
    
    M = np.column_stack(M_cols)
    
    # ─── Covariates X ───
    # In Kusner 2017 DAG, race/sex have no parents → no covariates X
    # We include OTHER demographic if not used as A
    X_cols = []
    X_names = []
    
    # Include the protected attribute NOT used as A
    if protected == 'race':
        # Include sex as covariate
        if cols['sex']:
            sex_vals = df[cols['sex']]
            if pd.api.types.is_numeric_dtype(sex_vals):
                X_cols.append(sex_vals.astype(float).values)
            else:
                sex_str = sex_vals.astype(str).str.lower()
                X_cols.append(sex_str.isin({'female', 'f', '1'}).astype(float).values)
            X_names.append('sex')
    elif protected == 'sex':
        if cols['race']:
            race_vals = df[cols['race']]
            if pd.api.types.is_numeric_dtype(race_vals):
                X_cols.append(race_vals.astype(float).values)
            else:
                race_str = race_vals.astype(str).str.lower()
                X_cols.append(race_str.isin({'white', '1'}).astype(float).values)
            X_names.append('race')
    
    if not X_cols:
        # Fallback: dummy X with intercept
        X = np.ones((len(Y), 1))
        X_names = ['intercept']
    else:
        X = np.column_stack(X_cols)
    
    # ─── Cluster ───
    if cols['school_id'] is not None:
        school_vals = df[cols['school_id']]
        unique_schools = sorted(school_vals.unique())
        school_map = {s: i for i, s in enumerate(unique_schools)}
        S = school_vals.map(school_map).values.astype(int)
        n_clusters = len(unique_schools)
    else:
        # No cluster structure
        S = np.zeros(len(Y), dtype=int)
        n_clusters = 1
    
    # ─── Standardize ───
    if X.shape[1] > 1 or X_names != ['intercept']:
        X_std = X.std(axis=0)
        X_std[X_std < 1e-6] = 1.0
        X = (X - X.mean(axis=0)) / X_std
    
    M_std = M.std(axis=0)
    M_std[M_std < 1e-6] = 1.0
    M = (M - M.mean(axis=0)) / M_std
    
    # Drop rows with NaN in Y
    valid = ~np.isnan(Y)
    if not valid.all() and verbose:
        print(f"  Dropping {(~valid).sum()} rows with missing outcome")
    Y = Y[valid]
    A = A[valid]
    M = M[valid]
    X = X[valid]
    S = S[valid]
    
    metadata = {
        'dataset': 'LawSchool',
        'protected': protected,
        'outcome': outcome,
        'n': len(Y),
        'n_clusters': n_clusters,
        'A_balance': float(A.mean()),
        'Y_mean': float(Y.mean()),
        'columns_detected': cols,
    }
    
    if verbose:
        print(f"\n  Final:")
        print(f"    n           = {len(Y):,}")
        print(f"    A balance   = {A.mean():.3f}")
        print(f"    Y mean      = {Y.mean():.3f}")
        print(f"    n_clusters  = {n_clusters}")
        print(f"    Mediators   = {M_names}")
    
    return {
        'Y': Y,
        'A': A,
        'M': M,
        'X': X,
        'S': S,
        'feature_names_X': X_names,
        'mediator_names': M_names,
        'metadata': metadata,
    }


__all__ = ['load_law_school']
