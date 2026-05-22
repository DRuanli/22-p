"""
UC Berkeley Graduate Admissions Dataset Loader
================================================

Famous fairness benchmark dataset. Used directly in Chiappa 2019 PSCF paper.

The Berkeley admissions data (Bickel et al. 1975) shows Simpson's paradox:
    - Marginally: 45.5% males admitted vs 30.4% females (apparent bias)
    - Conditional on department: female admission slightly HIGHER (no bias)
    
This is because women applied to more competitive departments.
The "fair" path is: Sex → Department → Admit
The "unfair" path is: Sex → Admit (direct discrimination)

POSSIBLE DATA SOURCES:
    1. R built-in: `data(UCBAdmissions)` - aggregated 4D table
    2. CSV reconstruction from R data:
       https://github.com/yumiko-sato/UC-Berkeley-Admissions-Data
    3. Chiappa 2019 may provide preprocessed version in their repo
    
EXPECTED SCHEMA (after preprocessing to individual-level):
    The dataset can be in two forms:
    
    Form 1 (aggregated):
        Admit  : str ("Admitted" / "Rejected")
        Gender : str ("Male" / "Female")
        Dept   : str ("A", "B", "C", "D", "E", "F")
        Freq   : int (count)
    
    Form 2 (individual-level, expanded):
        admit  : binary (1 if admitted)
        gender : binary (1 if female)
        dept   : categorical (A-F)
    
    This loader handles BOTH forms.

CAUSAL DAG (Chiappa 2019):
    A : gender (binary, F=1)
    M : department (the "fair" mediator - choice of competitive department)
    Y : admission decision
    
    Path-specific consideration:
        gender → department → admit  : Considered FAIR (women's department choice)
                                       UNLESS we believe steering exists
        gender → admit                : UNFAIR (direct discrimination)

CLUSTER STRUCTURE:
    - 6 departments → can use as clusters (S = department)
    - Note: department is BOTH mediator AND cluster — interesting case!
    - For HC-DML, this means cluster random effects ARE the mediator

NOTE ON DATASET LIMITATIONS:
    - Original is aggregated (cell counts), not individual-level
    - Expanding to individual-level loses no info but creates "synthetic" individuals
    - All variables are CATEGORICAL — limits estimation flexibility
    - n = 4,526 applicants
    - Famous but tiny by modern standards
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd


def load_berkeley_admission(
    dataset_path: str,
    expand_from_counts: Optional[bool] = None,  # auto-detect
    col_mapping: Optional[Dict[str, str]] = None,
    verbose: bool = True,
) -> Dict[str, np.ndarray]:
    """Load UC Berkeley graduate admissions dataset.
    
    Parameters
    ----------
    dataset_path : str
        Path to CSV file.
    expand_from_counts : bool, optional
        If True, expand aggregated counts to individual rows.
        If None, auto-detect based on presence of 'Freq' or 'count' column.
    col_mapping : dict, optional
        Override column names.
    verbose : bool
        Print info.
    
    Returns
    -------
    dict with HC-DML format
    """
    df = pd.read_csv(dataset_path)
    
    if verbose:
        print(f"\n{'═' * 60}")
        print(f" Loading Berkeley from {dataset_path} ".center(60, "═"))
        print(f"{'═' * 60}")
        print(f"  Raw shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
    
    col_mapping = col_mapping or {}
    
    # Detect column names
    def find(*aliases):
        for a in aliases:
            if a in df.columns:
                return a
            if a in col_mapping.values():
                # Reverse lookup
                for k, v in col_mapping.items():
                    if v == a:
                        return v
        return None
    
    col_admit = col_mapping.get('admit') or find('admit', 'Admit', 'admitted', 'Y')
    col_gender = col_mapping.get('gender') or find('gender', 'Gender', 'sex', 'Sex', 'A')
    col_dept = col_mapping.get('dept') or find('dept', 'Dept', 'department', 'M')
    col_freq = col_mapping.get('freq') or find('Freq', 'freq', 'count', 'Count', 'N')
    
    if verbose:
        print(f"\n  Column detection:")
        print(f"    admit    → {col_admit}")
        print(f"    gender   → {col_gender}")
        print(f"    dept     → {col_dept}")
        print(f"    freq     → {col_freq} (None = individual-level)")
    
    if col_admit is None or col_gender is None or col_dept is None:
        raise ValueError(
            f"Missing required columns. Need admit, gender, dept. "
            f"Available: {list(df.columns)}. "
            f"Use col_mapping={{'admit': 'your_col', ...}} to override."
        )
    
    # Auto-detect format
    if expand_from_counts is None:
        expand_from_counts = (col_freq is not None)
    
    # ─── Expand aggregated counts to individual rows if needed ───
    if expand_from_counts and col_freq is not None:
        if verbose:
            print(f"\n  Expanding from counts...")
        df = df.loc[df.index.repeat(df[col_freq])].reset_index(drop=True)
        if verbose:
            print(f"  Expanded shape: {df.shape}")
    
    # ─── Encode variables ───
    # Y: admission (binary)
    admit_vals = df[col_admit]
    if pd.api.types.is_numeric_dtype(admit_vals):
        Y = admit_vals.astype(float).values
    else:
        admit_str = admit_vals.astype(str).str.lower().str.strip()
        Y = admit_str.isin({'admitted', 'admit', 'yes', '1', 'accepted'}).astype(float).values
    
    # A: gender (binary, F=1)
    gender_vals = df[col_gender]
    if pd.api.types.is_numeric_dtype(gender_vals):
        A = gender_vals.astype(float).values
    else:
        gender_str = gender_vals.astype(str).str.lower().str.strip()
        A = gender_str.isin({'female', 'f', '1', 'women', 'woman'}).astype(float).values
    
    # M: department (one-hot encoded)
    dept_vals = df[col_dept].astype(str)
    unique_depts = sorted(dept_vals.unique())
    
    # Department one-hot encoding (mediator)
    M_oh = pd.get_dummies(dept_vals, drop_first=True).values.astype(float)
    # Keep all departments for cluster
    M = M_oh  # Mediator is department choice (one-hot)
    
    # S: department also acts as cluster
    dept_map = {d: i for i, d in enumerate(unique_depts)}
    S = dept_vals.map(dept_map).values.astype(int)
    
    # X: no additional covariates in classic Berkeley DAG
    # Add intercept (constant) for compatibility
    X = np.ones((len(Y), 1))
    
    metadata = {
        'dataset': 'Berkeley',
        'protected': 'gender',
        'outcome': 'admit',
        'n': len(Y),
        'n_clusters': len(unique_depts),
        'departments': unique_depts,
        'A_balance': float(A.mean()),
        'Y_mean': float(Y.mean()),
        'note': 'Department is BOTH mediator AND cluster — special case for HC-DML',
    }
    
    if verbose:
        print(f"\n  Final:")
        print(f"    n           = {len(Y):,}")
        print(f"    departments = {unique_depts}")
        print(f"    A balance   = {A.mean():.3f}  (Female fraction)")
        print(f"    Y mean      = {Y.mean():.3f}  (Admission rate)")
        print(f"    Admission rate by gender:")
        for g in [0, 1]:
            mask = A == g
            label = 'Female' if g == 1 else 'Male'
            print(f"      {label}: {Y[mask].mean():.3f} (n={mask.sum()})")
    
    return {
        'Y': Y,
        'A': A,
        'M': M,
        'X': X,
        'S': S,
        'feature_names_X': ['intercept'],
        'mediator_names': [f'dept_{d}' for d in unique_depts[1:]],
        'metadata': metadata,
    }


__all__ = ['load_berkeley_admission']
