"""
Real Data Loaders for Causal Fairness Validation
=================================================

Provides standardized loading for:
    - UCI Student Performance (Cortez & Silva 2008): math and Portuguese
    - xAPI Educational dataset (Aljarah)

Each loader returns data in the format expected by HC-DML:
    Y: outcome
    A: protected attribute (binary)
    M: mediators
    X: covariates
    S: cluster (school/section)

HONEST NOTES about real data:
    - No ground truth for path-specific effects on real data
    - DAG specifications are subjective; we provide defaults but recommend
      sensitivity analysis with multiple DAGs
    - Sample sizes are small: limits power of inference
    - Cluster structure is weak (e.g., UCI has only 2 schools)
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Dict, Optional

import numpy as np
import pandas as pd


# =========================================================================
# UCI STUDENT PERFORMANCE
# =========================================================================

def load_uci_student(
    dataset_path: str,
    subject: str = 'math',  # 'math' or 'portuguese'
    outcome: str = 'G3',     # 'G3' (final), 'G2' (period 2), or binary 'pass'
    protected: str = 'sex',  # 'sex' or 'address'
    binary_outcome_threshold: int = 10,
) -> Dict[str, np.ndarray]:
    """Load UCI Student Performance dataset.
    
    Dataset: Cortez & Silva 2008
    Source: https://archive.ics.uci.edu/ml/datasets/Student+Performance
    
    Parameters
    ----------
    dataset_path : str
        Path to student-mat.csv or student-por.csv
    subject : str
        'math' or 'portuguese'
    outcome : str
        Outcome variable. G3 = final grade (0-20).
        Use 'pass' for binary outcome (G3 >= threshold).
    protected : str
        Protected attribute. Options: 'sex' (binary M/F), 'address' (U/R)
    binary_outcome_threshold : int
        Threshold for binary pass/fail outcome.
    
    Returns
    -------
    dict with keys: Y, A, M, X, S, feature_names, metadata
    
    DAG used:
        - X (pre-attributes): age, school, famsize, Pstatus, Medu, Fedu, 
                             Mjob, Fjob, reason, guardian, traveltime,
                             famrel, internet (etc. — pre-treatment-like)
        - A: sex (or address)
        - M (mediators — affected by A, may affect Y):
            studytime, failures, paid (extra paid classes), 
            activities, nursery, higher (wants higher ed), romantic,
            G1 (period 1 grade), G2 (period 2 grade — for G3 outcome only),
            absences
        - Y: G3 (final grade)
        - S (cluster): school (GP or MS — only 2 clusters! limited)
    
    NOTE: The DAG above is one choice. Mediator/covariate distinction
    is subjective. For example, "famsup" could be either depending on
    whether you think it's affected by student's gender.
    """
    if subject not in ('math', 'portuguese'):
        raise ValueError(f"Unknown subject: {subject}")
    
    # Load CSV (semicolon-separated)
    df = pd.read_csv(dataset_path, sep=';')
    
    # Rename columns to remove special chars
    df.columns = [c.strip() for c in df.columns]
    
    # Define attribute roles
    pre_treatment = [
        'age', 'famsize', 'Pstatus', 'Medu', 'Fedu',
        'Mjob', 'Fjob', 'reason', 'guardian', 'traveltime',
        'famrel', 'internet', 'nursery', 'higher',
    ]
    
    # Mediators: things that could plausibly be affected by sex
    # (e.g., studytime, paid classes, romantic involvement, absences, G1)
    mediators = ['studytime', 'failures', 'paid', 'activities',
                'romantic', 'absences', 'G1']
    
    if outcome == 'G3':
        mediators.append('G2')  # G2 mediates G3 prediction
    
    # Protected attribute
    if protected == 'sex':
        A = (df['sex'] == 'F').astype(int).values  # 1 = Female
    elif protected == 'address':
        A = (df['address'] == 'U').astype(int).values  # 1 = Urban
    else:
        raise ValueError(f"Unknown protected: {protected}")
    
    # Outcome
    if outcome == 'pass':
        Y = (df['G3'] >= binary_outcome_threshold).astype(int).values
    else:
        Y = df[outcome].values.astype(float)
    
    # Cluster: school
    school_map = {'GP': 0, 'MS': 1}
    S = df['school'].map(school_map).values
    
    # Build M matrix
    M_cols = []
    for col in mediators:
        if col in df.columns:
            vals = df[col]
            # Check if string-like (yes/no, etc.)
            if vals.dtype == object or pd.api.types.is_string_dtype(vals):
                vals_str = vals.astype(str).str.lower()
                vals = (vals_str == 'yes').astype(int)
            M_cols.append(vals.values.astype(float))
    M = np.column_stack(M_cols)
    
    # Build X matrix
    X_cols = []
    feature_names_X = []
    for col in pre_treatment:
        if col not in df.columns:
            continue
        vals = df[col]
        if vals.dtype == object or pd.api.types.is_string_dtype(vals):
            # One-hot encode categoricals
            dummies = pd.get_dummies(vals, prefix=col, drop_first=True)
            for c in dummies.columns:
                X_cols.append(dummies[c].values.astype(float))
                feature_names_X.append(c)
        else:
            X_cols.append(vals.values.astype(float))
            feature_names_X.append(col)
    X = np.column_stack(X_cols)
    
    # Standardize X for stability
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_std[X_std < 1e-6] = 1.0
    X = (X - X_mean) / X_std
    
    # Standardize M for interpretation 
    M_mean = M.mean(axis=0)
    M_std = M.std(axis=0)
    M_std[M_std < 1e-6] = 1.0
    M = (M - M_mean) / M_std
    
    return {
        'Y': Y,
        'A': A.astype(float),
        'M': M,
        'X': X,
        'S': S,
        'feature_names_X': feature_names_X,
        'mediator_names': [m for m in mediators if m in df.columns],
        'metadata': {
            'subject': subject,
            'outcome': outcome,
            'protected': protected,
            'n': len(Y),
            'n_clusters': len(np.unique(S)),
            'A_balance': float(A.mean()),
            'Y_mean': float(Y.mean()),
        }
    }


# =========================================================================
# xAPI EDUCATIONAL DATASET
# =========================================================================

def load_xapi(
    dataset_path: str,
    outcome: str = 'class',  # 'class' (L/M/H) or binary 'high'
    protected: str = 'gender',
) -> Dict[str, np.ndarray]:
    """Load xAPI Educational dataset.
    
    Dataset: Amrieh, Hamtini & Aljarah (2016)
    Source: https://www.kaggle.com/datasets/aljarah/xAPI-Edu-Data
    
    Structure:
        - 480 students
        - Engagement metrics (raisedhands, VisITedResources, etc.) → mediators
        - Performance class (L/M/H) → outcome
        - Protected: gender, nationality
        - Cluster proxy: Topic + Semester
    
    DAG:
        X (pre): NationalITy, PlaceofBirth, StageID, GradeID, Topic, Semester
        A: gender (M/F)
        M (engagement mediators):
            raisedhands, VisITedResources, AnnouncementsView, Discussion,
            ParentAnsweringSurvey, ParentschoolSatisfaction, StudentAbsenceDays
        Y: Class (L/M/H → 0/1/2 or binary 'high')
        S: Topic (12 topics) or combination
    """
    df = pd.read_csv(dataset_path)
    
    # Protected attribute
    if protected == 'gender':
        A = (df['gender'] == 'F').astype(int).values
    elif protected == 'nationality':
        # Binarize: Kuwait (largest) vs others
        A = (df['NationalITy'] == 'KW').astype(int).values
    else:
        raise ValueError(f"Unknown protected: {protected}")
    
    # Outcome
    if outcome == 'high':
        # Binary: H = 1, M/L = 0
        Y = (df['Class'] == 'H').astype(int).values
    elif outcome == 'pass':
        # Binary: H or M = 1, L = 0
        Y = (df['Class'].isin(['H', 'M'])).astype(int).values
    elif outcome == 'class':
        # Continuous-ish: L=0, M=1, H=2
        class_map = {'L': 0, 'M': 1, 'H': 2}
        Y = df['Class'].map(class_map).values.astype(float)
    else:
        raise ValueError(f"Unknown outcome: {outcome}")
    
    # Cluster: Topic (12 unique values)
    topic_codes = pd.Categorical(df['Topic']).codes
    S = topic_codes.astype(int)
    
    # Mediators: engagement + parent
    mediators = [
        'raisedhands', 'VisITedResources', 
        'AnnouncementsView', 'Discussion'
    ]
    M = df[mediators].values.astype(float)
    
    # Parent variables — could be mediators or pre
    # We treat as additional mediators per Aljarah convention
    parent_vars = []
    if 'ParentAnsweringSurvey' in df.columns:
        parent_vars.append((df['ParentAnsweringSurvey'] == 'Yes').astype(int).values)
    if 'ParentschoolSatisfaction' in df.columns:
        parent_vars.append((df['ParentschoolSatisfaction'] == 'Good').astype(int).values)
    if 'StudentAbsenceDays' in df.columns:
        parent_vars.append((df['StudentAbsenceDays'] == 'Above-7').astype(int).values)
    if parent_vars:
        M = np.column_stack([M] + parent_vars)
    
    # Pre-treatment X: stage, grade, semester, relation
    X_cols = []
    feature_names_X = []
    for col in ['StageID', 'GradeID', 'Semester', 'Relation', 'NationalITy', 'PlaceofBirth']:
        if col in df.columns:
            dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
            for c in dummies.columns:
                X_cols.append(dummies[c].values.astype(float))
                feature_names_X.append(c)
    
    if X_cols:
        X = np.column_stack(X_cols)
    else:
        # Fallback: just intercept
        X = np.ones((len(Y), 1))
    
    # Standardize
    X_std = X.std(axis=0)
    X_std[X_std < 1e-6] = 1.0
    X = (X - X.mean(axis=0)) / X_std
    
    M_std = M.std(axis=0)
    M_std[M_std < 1e-6] = 1.0
    M = (M - M.mean(axis=0)) / M_std
    
    return {
        'Y': Y,
        'A': A.astype(float),
        'M': M,
        'X': X,
        'S': S,
        'feature_names_X': feature_names_X,
        'mediator_names': mediators + ['ParentSurvey', 'ParentSatisf', 'AbsenceDays'],
        'metadata': {
            'outcome': outcome,
            'protected': protected,
            'n': len(Y),
            'n_clusters': len(np.unique(S)),
            'A_balance': float(A.mean()),
        }
    }


# =========================================================================
# UTILITY: Print dataset summary
# =========================================================================

def print_dataset_summary(data: Dict, name: str = "Dataset"):
    """Print structured summary of loaded dataset."""
    print(f"\n{'═' * 60}")
    print(f" {name} ".center(60, "═"))
    print(f"{'═' * 60}")
    
    meta = data['metadata']
    print(f"  n           = {meta['n']}")
    print(f"  clusters    = {meta['n_clusters']}")
    print(f"  A balance   = {meta['A_balance']:.3f}")
    if 'Y_mean' in meta:
        print(f"  Y mean      = {meta['Y_mean']:.3f}")
    print(f"  outcome     = {meta['outcome']}")
    print(f"  protected   = {meta['protected']}")
    print(f"\n  X shape     = {data['X'].shape}")
    print(f"  M shape     = {data['M'].shape}")
    print(f"  Mediators   = {data['mediator_names'][:5]}...")
    print()


__all__ = ['load_uci_student', 'load_xapi', 'print_dataset_summary']
