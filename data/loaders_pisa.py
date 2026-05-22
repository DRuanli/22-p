"""
PISA Dataset Loader for 3-Level Hierarchical Fairness Analysis
================================================================

OECD Programme for International Student Assessment (PISA).
~700,000 students from 81 countries (PISA 2022).

⚠️  HONEST WARNINGS:

1. **Sampling weights:** PISA uses complex two-stage stratified sampling.
   Causal estimation should weight observations by W_FSTUWT (final student
   weight). Current HC-DML implementation does NOT use sampling weights.
   Estimates may be biased relative to population. 

2. **Plausible values:** PISA scores are reported as 10 plausible values
   per student (PV1MATH, PV2MATH, ..., PV10MATH) — not single scores.
   For valid inference, should run analysis 10 times and combine (Rubin's
   rules). This loader uses ONLY PV1 by default — biased standard errors.

3. **3-level hierarchy:** student → school (SCHOOLID) → country (CNT).
   HC-DML in current form handles only 1 cluster level. Loading PISA
   with student → school clusters as primary; country as covariate.

4. **Massive file size:** Student-level file is ~3GB. Variables ~1000.
   Even loading subset requires careful memory management.

POSSIBLE DATA SOURCES:
    1. OECD Direct:
       https://www.oecd.org/pisa/data/2022database/
       Provides SPSS (.sav) and SAS (.sas7bdat) files
       Use pyreadstat: `pip install pyreadstat`
    
    2. PISA 2022 R package (cleaned):
       https://github.com/eyrunaolafs/pisa
    
    3. ouladFormat-style preprocessing scripts on GitHub:
       Search "PISA 2022 python loader"

EXPECTED SCHEMA (after extracting subset):
    Required:
        CNT          : str (country code, ISO 3-letter)
        SCHOOLID / CNTSCHID : str/int (school identifier)
        STIDSTD / CNTSTUID  : int (student identifier)
        ST004D01T / ST004Q01TA : Gender (1=Female, 2=Male in PISA coding)
        PV1MATH      : numerical (first plausible value, math score)
    
    Optional but recommended:
        ESCS         : numerical (socioeconomic status index)
        IMMIG        : categorical (1=native, 2=second-gen, 3=first-gen)
        REPEAT       : binary (grade repetition)
        AGE          : numerical
        ST022Q01TA   : language at home
        BSMJ         : expected occupation
        W_FSTUWT     : final student weight (CRUCIAL for unbiased estimation)

CAUSAL DAG (one possible specification):
    A : gender (binary, F=1)
    X : ESCS, IMMIG, AGE, REPEAT, native_language
    M : study habits, attitude toward math, math self-efficacy 
        (from background questionnaire — many possible)
    Y : PV1MATH (or pass binary)
    S : SCHOOLID (school-level cluster)
    
    Alternative DAGs:
    - Country fixed effects: include CNT dummies in X
    - 3-level: schools nested in countries → need extended HC-DML

PREPROCESSING REQUIREMENTS:
    1. Subset variables (don't load all 1000 columns)
    2. Handle missing codes: PISA uses 7, 8, 9 for various missing types
    3. Recode gender: 1→Female=1, 2→Male=0 (PISA convention)
    4. Filter to valid student records
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, List
import warnings

import numpy as np
import pandas as pd


# PISA missing value codes per OECD codebook
PISA_MISSING_CODES = {
    # Standard codes for "Valid Skip", "Not Applicable", "Invalid", "No Response"
    'invalid': [97, 98, 99, 9997, 9998, 9999],
    'numeric_missing': [997, 998, 999, 9997, 9998, 9999],
}

# Default variable subset to load (reduces from ~1000 to manageable)
DEFAULT_VARIABLES = [
    # Identifiers
    'CNT', 'CNTSCHID', 'CNTSTUID',
    # Demographics
    'ST004D01T',  # Gender
    'AGE',        # Age in years
    'ST001D01T',  # Grade
    'IMMIG',      # Immigration status
    # Outcome
    'PV1MATH',    # Math plausible value 1
    'PV1READ',    # Reading PV1 (for sensitivity)
    'PV1SCIE',    # Science PV1
    # Mediators (candidate)
    'ANXMAT',     # Math anxiety scale
    'MATHEFF',    # Math self-efficacy
    'BELONG',     # Sense of belonging
    'BSMJ',       # Expected occupation score
    # Covariates
    'ESCS',       # SES index
    'REPEAT',     # Grade repetition
    'HOMEPOS',    # Home possessions
    # Weights
    'W_FSTUWT',   # Final student weight
]


def load_pisa(
    dataset_path: str,
    file_format: str = 'csv',  # 'csv', 'sav' (SPSS), 'sas7bdat' (SAS)
    variables: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,  # Filter to specific countries
    outcome: str = 'math',  # 'math', 'reading', 'science', 'math_pass'
    protected: str = 'gender',  # 'gender' or 'immig'
    use_sampling_weights: bool = False,  # NOT YET SUPPORTED in HC-DML
    n_sample: Optional[int] = None,  # Subsample for memory/speed
    verbose: bool = True,
) -> Dict[str, np.ndarray]:
    """Load PISA dataset for HC-DML.
    
    Parameters
    ----------
    dataset_path : str
        Path to PISA data file.
    file_format : str
        Format of file. 'csv' for converted, 'sav' for SPSS, 'sas7bdat' for SAS.
    variables : list, optional
        Subset of variables to load. If None, use DEFAULT_VARIABLES.
    countries : list, optional
        ISO 3-letter codes to filter (e.g., ['VNM', 'KOR']).
    outcome : str
        Outcome variable.
    protected : str
        Protected attribute.
    use_sampling_weights : bool
        Apply sampling weights. NOT YET IMPLEMENTED.
    n_sample : int, optional
        Random subsample for testing.
    verbose : bool
        Print progress.
    
    Returns
    -------
    dict with HC-DML format
    """
    if use_sampling_weights:
        warnings.warn(
            "use_sampling_weights=True requested but not yet implemented. "
            "Estimates will not be population-representative. "
            "Will be biased toward larger schools/countries."
        )
    
    variables = variables or DEFAULT_VARIABLES
    
    if verbose:
        print(f"\n{'═' * 60}")
        print(f" Loading PISA from {dataset_path} ".center(60, "═"))
        print(f"{'═' * 60}")
        print(f"  Format: {file_format}")
        print(f"  Variables: {len(variables)} columns")
    
    # ─── Load data ───
    if file_format == 'csv':
        df = pd.read_csv(dataset_path, usecols=lambda c: c in variables, low_memory=False)
    elif file_format in ('sav', 'sas7bdat'):
        try:
            import pyreadstat
        except ImportError:
            raise ImportError(
                "Reading PISA SPSS/SAS files requires pyreadstat: pip install pyreadstat"
            )
        
        if file_format == 'sav':
            df, meta = pyreadstat.read_sav(
                dataset_path, 
                usecols=variables,
                disable_datetime_conversion=True
            )
        else:
            df, meta = pyreadstat.read_sas7bdat(
                dataset_path,
                usecols=variables,
                disable_datetime_conversion=True
            )
    else:
        raise ValueError(f"Unknown file_format: {file_format}")
    
    if verbose:
        print(f"  Loaded shape: {df.shape}")
    
    # ─── Filter countries ───
    if countries is not None and 'CNT' in df.columns:
        df = df[df['CNT'].isin(countries)].reset_index(drop=True)
        if verbose:
            print(f"  After country filter: {df.shape}")
    
    # ─── Subsample if requested ───
    if n_sample is not None and len(df) > n_sample:
        df = df.sample(n=n_sample, random_state=42).reset_index(drop=True)
        if verbose:
            print(f"  After subsample: {df.shape}")
    
    # ─── Handle PISA missing codes ───
    # Convert PISA missing markers to NaN
    for col in df.select_dtypes(include=[np.number]).columns:
        for missing_code in PISA_MISSING_CODES['numeric_missing']:
            df.loc[df[col] == missing_code, col] = np.nan
    
    # ─── Build A (protected attribute) ───
    if protected == 'gender':
        if 'ST004D01T' not in df.columns:
            raise ValueError("Gender column ST004D01T not found")
        # PISA codes: 1=Female, 2=Male
        # We code: Female=1, Male=0
        gender_raw = df['ST004D01T']
        A = (gender_raw == 1).astype(float).values
    elif protected == 'immig':
        if 'IMMIG' not in df.columns:
            raise ValueError("IMMIG column not found")
        # PISA codes: 1=Native, 2=Second-gen, 3=First-gen
        # We code: Immigrant (2 or 3) = 1, Native = 0
        immig_raw = df['IMMIG']
        A = immig_raw.isin([2, 3]).astype(float).values
    else:
        raise ValueError(f"Unknown protected: {protected}")
    
    # ─── Build Y (outcome) ───
    outcome_map = {
        'math': 'PV1MATH',
        'reading': 'PV1READ',
        'science': 'PV1SCIE',
    }
    
    if outcome == 'math_pass':
        if 'PV1MATH' not in df.columns:
            raise ValueError("PV1MATH not found")
        # PISA Level 2 = 420 points = baseline proficiency
        Y = (df['PV1MATH'] >= 420).astype(float).values
    elif outcome in outcome_map:
        col = outcome_map[outcome]
        if col not in df.columns:
            raise ValueError(f"{col} not found")
        Y = df[col].astype(float).values
    else:
        raise ValueError(f"Unknown outcome: {outcome}")
    
    # ─── Build S (cluster: school) ───
    if 'CNTSCHID' in df.columns:
        school_vals = df['CNTSCHID']
        unique_schools = sorted(school_vals.dropna().unique())
        school_map = {s: i for i, s in enumerate(unique_schools)}
        S = school_vals.map(school_map).fillna(-1).astype(int).values
    elif 'SCHOOLID' in df.columns:
        school_vals = df['SCHOOLID']
        unique_schools = sorted(school_vals.dropna().unique())
        school_map = {s: i for i, s in enumerate(unique_schools)}
        S = school_vals.map(school_map).fillna(-1).astype(int).values
    else:
        if verbose:
            print(f"  WARNING: No school ID found, using country as cluster")
        if 'CNT' in df.columns:
            cnt_vals = df['CNT']
            unique_cnts = sorted(cnt_vals.dropna().unique())
            cnt_map = {c: i for i, c in enumerate(unique_cnts)}
            S = cnt_vals.map(cnt_map).fillna(-1).astype(int).values
        else:
            S = np.zeros(len(df), dtype=int)
    
    # ─── Build M (mediators) ───
    M_candidates = ['ANXMAT', 'MATHEFF', 'BELONG', 'BSMJ']
    M_cols = []
    M_names = []
    for col in M_candidates:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors='coerce')
            if vals.notna().sum() > len(vals) * 0.1:  # At least 10% non-missing
                vals = vals.fillna(vals.median())
                M_cols.append(vals.values.astype(float))
                M_names.append(col)
    
    if not M_cols:
        warnings.warn(
            "No mediator variables found in M_candidates. "
            "Adding placeholder M from grade level."
        )
        if 'ST001D01T' in df.columns:
            grade = pd.to_numeric(df['ST001D01T'], errors='coerce').fillna(0)
            M_cols.append(grade.values.astype(float))
            M_names.append('grade_placeholder')
        else:
            M_cols.append(np.zeros(len(df)))
            M_names.append('zero_placeholder')
    
    M = np.column_stack(M_cols)
    
    # ─── Build X (covariates) ───
    X_cols = []
    X_names = []
    
    for col in ['ESCS', 'AGE', 'HOMEPOS', 'REPEAT']:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors='coerce')
            if vals.notna().sum() > len(vals) * 0.1:
                vals = vals.fillna(vals.median())
                X_cols.append(vals.values.astype(float))
                X_names.append(col)
    
    # Country one-hot (if multiple countries)
    if 'CNT' in df.columns and df['CNT'].nunique() > 1 and df['CNT'].nunique() < 100:
        cnt_dummies = pd.get_dummies(df['CNT'], prefix='CNT', drop_first=True)
        for c in cnt_dummies.columns:
            X_cols.append(cnt_dummies[c].values.astype(float))
            X_names.append(c)
    
    if not X_cols:
        X = np.ones((len(Y), 1))
        X_names = ['intercept']
    else:
        X = np.column_stack(X_cols)
    
    # ─── Drop missing Y / A ───
    valid = ~(np.isnan(Y) | np.isnan(A))
    if not valid.all():
        if verbose:
            print(f"  Dropping {(~valid).sum()} rows with missing Y or A")
        Y, A, M, X, S = Y[valid], A[valid], M[valid], X[valid], S[valid]
    
    # ─── Standardize ───
    if X.shape[1] > 1 or X_names != ['intercept']:
        X_std = X.std(axis=0)
        X_std[X_std < 1e-6] = 1.0
        X = (X - X.mean(axis=0)) / X_std
    
    M_std = M.std(axis=0)
    M_std[M_std < 1e-6] = 1.0
    M = (M - M.mean(axis=0)) / M_std
    
    # Final cluster count
    n_clusters = len(np.unique(S))
    
    metadata = {
        'dataset': 'PISA',
        'protected': protected,
        'outcome': outcome,
        'n': len(Y),
        'n_clusters': n_clusters,
        'countries': sorted(df['CNT'].unique().tolist()) if 'CNT' in df.columns else [],
        'A_balance': float(A.mean()),
        'Y_mean': float(Y.mean()),
        'sampling_weights_used': use_sampling_weights,
        'warnings': [
            'Single plausible value used (not Rubin combination)',
            'Sampling weights not applied' if not use_sampling_weights else '',
            f'School clusters: {n_clusters}',
        ],
    }
    
    if verbose:
        print(f"\n  Final:")
        print(f"    n              = {len(Y):,}")
        print(f"    n_clusters     = {n_clusters}")
        print(f"    A balance      = {A.mean():.3f}")
        print(f"    Y mean         = {Y.mean():.3f}")
        print(f"    Mediators      = {M_names}")
        print(f"    X dim          = {X.shape[1]}")
        if metadata['countries']:
            print(f"    Countries      = {metadata['countries'][:5]}{'...' if len(metadata['countries']) > 5 else ''}")
    
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


__all__ = ['load_pisa', 'DEFAULT_VARIABLES']
