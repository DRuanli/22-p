"""
OULAD Dataset Loader for HC-DML
=================================

Loads and preprocesses the Open University Learning Analytics Dataset
(Kuzilek, Hlosta & Zdrahal 2017) into HC-DML format.

DOWNLOAD:
    Visit https://analyse.kmi.open.ac.uk/open-dataset
    Or use ucimlrepo: fetch_ucirepo(id=349)
    
    Place these 7 CSV files in OULAD_PATH:
        - courses.csv
        - assessments.csv
        - vle.csv
        - studentInfo.csv
        - studentRegistration.csv
        - studentAssessment.csv
        - studentVle.csv  (LARGE: ~480MB)

CAUSAL DAG (for fairness analysis):
    A: gender (binary: F=1)
    X: age_band, region, imd_band, highest_education, disability,
       num_prev_attempts, studied_credits
    M: sum_clicks (engagement), first_assessment_score,
       avg_assessment_score, days_late_registration
    Y: final_result (binary: Pass/Distinction = 1; Fail/Withdrawn = 0)
    S: code_module × code_presentation (22 clusters)

LIMITATIONS:
    - DAG choices are subjective; alternatives possible
    - studentVle.csv aggregation can be memory-intensive
    - We use cumulative pre-assessment clicks only (avoid leakage)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, List

import numpy as np
import pandas as pd


# =========================================================================
# MAIN LOADER
# =========================================================================

def load_oulad(
    oulad_path: str,
    protected: str = 'gender',
    outcome: str = 'pass_distinction',
    aggregate_clicks_by: str = 'cumulative',  # 'cumulative' or 'first_quarter'
    min_assessments: int = 1,
    verbose: bool = True,
) -> Dict[str, np.ndarray]:
    """Load and preprocess OULAD into HC-DML format.
    
    Parameters
    ----------
    oulad_path : str
        Path to directory containing the 7 OULAD CSV files.
    protected : str
        'gender' (M/F → binary) or 'disability' (Y/N → binary).
    outcome : str
        'pass_distinction' (binary: Pass or Distinction = 1)
        'distinction' (binary: Distinction only = 1)
        'completion' (binary: NOT Withdrawn = 1)
    aggregate_clicks_by : str
        How to aggregate VLE clicks.
        'cumulative': total clicks before final assessment (largest M)
        'first_quarter': clicks in first 25% of module days (avoid leakage)
    min_assessments : int
        Filter students with at least this many assessments.
    verbose : bool
        Print progress.
    
    Returns
    -------
    dict with keys: Y, A, M, X, S, feature_names, metadata
    """
    oulad_path = Path(oulad_path)
    
    required_files = [
        'courses.csv', 'assessments.csv', 'studentInfo.csv',
        'studentRegistration.csv', 'studentAssessment.csv',
    ]
    # studentVle is optional (large); we'll check
    
    for fname in required_files:
        if not (oulad_path / fname).exists():
            raise FileNotFoundError(
                f"Required file not found: {oulad_path / fname}. "
                f"Download OULAD from https://analyse.kmi.open.ac.uk/open-dataset"
            )
    
    if verbose:
        print(f"\n{'═' * 60}")
        print(f" Loading OULAD from {oulad_path} ".center(60, "═"))
        print(f"{'═' * 60}")
    
    # ─── Load core tables ───
    student_info = pd.read_csv(oulad_path / 'studentInfo.csv')
    student_reg = pd.read_csv(oulad_path / 'studentRegistration.csv')
    student_assess = pd.read_csv(oulad_path / 'studentAssessment.csv')
    assessments = pd.read_csv(oulad_path / 'assessments.csv')
    courses = pd.read_csv(oulad_path / 'courses.csv')
    
    if verbose:
        print(f"\n  studentInfo:     {len(student_info):,} rows")
        print(f"  studentReg:      {len(student_reg):,} rows")
        print(f"  studentAssess:   {len(student_assess):,} rows")
        print(f"  assessments:     {len(assessments):,} rows")
        print(f"  courses:         {len(courses):,} rows (clusters)")
    
    # ─── Build base dataset on (id_student, code_module, code_presentation) ───
    df = student_info.copy()
    
    # Merge registration info
    df = df.merge(
        student_reg[['id_student', 'code_module', 'code_presentation',
                    'date_registration', 'date_unregistration']],
        on=['id_student', 'code_module', 'code_presentation'],
        how='left'
    )
    
    # Merge course length
    df = df.merge(courses, on=['code_module', 'code_presentation'], how='left')
    
    # ─── Compute assessment-based mediators ───
    # Filter assessments to those tied to a student session
    assess_with_meta = student_assess.merge(
        assessments[['id_assessment', 'code_module', 'code_presentation', 'date', 'weight']],
        on='id_assessment',
        how='left'
    )
    
    # FIX: OULAD score column may contain '?' for missing → convert to numeric
    assess_with_meta['score'] = pd.to_numeric(assess_with_meta['score'], errors='coerce')
    
    # Sort by date so 'first' aggregation returns chronologically first assessment
    if 'date' in assess_with_meta.columns:
        assess_with_meta['date'] = pd.to_numeric(assess_with_meta['date'], errors='coerce')
        assess_with_meta = assess_with_meta.sort_values(
            ['id_student', 'code_module', 'code_presentation', 'date']
        )
    
    # Average and first assessment scores per student-session
    assess_agg = assess_with_meta.groupby(
        ['id_student', 'code_module', 'code_presentation']
    ).agg(
        n_assessments=('score', 'count'),  # count of NON-NULL scores
        avg_assessment_score=('score', 'mean'),
        first_assessment_score=('score', 'first'),
    ).reset_index()
    
    df = df.merge(assess_agg, on=['id_student', 'code_module', 'code_presentation'], how='left')
    
    # Filter students with sufficient assessments
    n_before = len(df)
    df = df[df['n_assessments'].fillna(0) >= min_assessments].copy()
    if verbose:
        print(f"\n  Filtered to ≥{min_assessments} assessments: {len(df):,} (from {n_before:,})")
    
    # ─── Aggregate VLE clicks (if available) ───
    vle_path = oulad_path / 'studentVle.csv'
    if vle_path.exists():
        if verbose:
            print(f"\n  Aggregating VLE clicks from {vle_path.name}...")
        
        if aggregate_clicks_by == 'cumulative':
            # Total clicks across all days
            vle_agg = _aggregate_vle_cumulative(vle_path, df, verbose=verbose)
        elif aggregate_clicks_by == 'first_quarter':
            # Clicks in first 25% of module days (avoid outcome leakage)
            vle_agg = _aggregate_vle_first_quarter(vle_path, df, courses, verbose=verbose)
        else:
            raise ValueError(f"Unknown aggregate_clicks_by: {aggregate_clicks_by}")
        
        df = df.merge(vle_agg, on=['id_student', 'code_module', 'code_presentation'], how='left')
        df['sum_clicks'] = df['sum_clicks'].fillna(0)
    else:
        if verbose:
            print(f"\n  No studentVle.csv found; sum_clicks set to 0")
        df['sum_clicks'] = 0
    
    # ─── Build final variables ───
    n_total = len(df)
    
    # Protected attribute A
    if protected == 'gender':
        A = (df['gender'] == 'F').astype(int).values  # 1 = Female
    elif protected == 'disability':
        A = (df['disability'] == 'Y').astype(int).values  # 1 = disabled
    else:
        raise ValueError(f"Unknown protected: {protected}")
    
    # Outcome Y
    if outcome == 'pass_distinction':
        Y = df['final_result'].isin(['Pass', 'Distinction']).astype(int).values
    elif outcome == 'distinction':
        Y = (df['final_result'] == 'Distinction').astype(int).values
    elif outcome == 'completion':
        Y = (df['final_result'] != 'Withdrawn').astype(int).values
    else:
        raise ValueError(f"Unknown outcome: {outcome}")
    
    # Cluster S: code_module × code_presentation
    df['cluster_id'] = df['code_module'] + '_' + df['code_presentation']
    cluster_map = {c: i for i, c in enumerate(sorted(df['cluster_id'].unique()))}
    S = df['cluster_id'].map(cluster_map).values.astype(int)
    
    # Mediators M
    # Convert assessment scores to standardized form
    M_components = {}
    M_components['sum_clicks'] = df['sum_clicks'].values.astype(float)
    M_components['first_assessment_score'] = df['first_assessment_score'].fillna(
        df['first_assessment_score'].mean()
    ).values.astype(float)
    M_components['avg_assessment_score'] = df['avg_assessment_score'].fillna(
        df['avg_assessment_score'].mean()
    ).values.astype(float)
    
    # Registration lateness (relative to module start)
    # FIX: date_registration may contain '?' or be string dtype → coerce
    df['date_registration'] = pd.to_numeric(df['date_registration'], errors='coerce').fillna(0)
    M_components['days_late_registration'] = df['date_registration'].values.astype(float)
    
    M = np.column_stack(list(M_components.values()))
    
    # Standardize M
    M_std = M.std(axis=0)
    M_std[M_std < 1e-6] = 1.0
    M = (M - M.mean(axis=0)) / M_std
    
    # Covariates X
    X_components = []
    X_feature_names = []
    
    # Continuous (with safety coercion in case of '?' missing markers)
    df['num_of_prev_attempts'] = pd.to_numeric(
        df['num_of_prev_attempts'], errors='coerce'
    ).fillna(0)
    df['studied_credits'] = pd.to_numeric(
        df['studied_credits'], errors='coerce'
    )
    df['studied_credits'] = df['studied_credits'].fillna(df['studied_credits'].median())
    X_components.append(df['num_of_prev_attempts'].values.astype(float))
    X_feature_names.append('num_prev_attempts')
    X_components.append(df['studied_credits'].values.astype(float))
    X_feature_names.append('studied_credits')
    
    # Categorical (one-hot)
    for col in ['age_band', 'region', 'imd_band', 'highest_education']:
        if col not in df.columns:
            continue
        vals = df[col].fillna('Missing')
        dummies = pd.get_dummies(vals, prefix=col, drop_first=True)
        for c in dummies.columns:
            X_components.append(dummies[c].values.astype(float))
            X_feature_names.append(c)
    
    X = np.column_stack(X_components)
    
    # Standardize X
    X_std = X.std(axis=0)
    X_std[X_std < 1e-6] = 1.0
    X = (X - X.mean(axis=0)) / X_std
    
    metadata = {
        'dataset': 'OULAD',
        'protected': protected,
        'outcome': outcome,
        'aggregate_clicks_by': aggregate_clicks_by,
        'n': n_total,
        'n_clusters': len(cluster_map),
        'A_balance': float(A.mean()),
        'Y_mean': float(Y.mean()),
        'cluster_map': cluster_map,
    }
    
    if verbose:
        print(f"\n  Final shape:")
        print(f"    n           = {n_total:,}")
        print(f"    n_clusters  = {len(cluster_map)}")
        print(f"    A balance   = {A.mean():.3f}")
        print(f"    Y mean      = {Y.mean():.3f}")
        print(f"    X shape     = {X.shape}")
        print(f"    M shape     = {M.shape}")
    
    return {
        'Y': Y,
        'A': A.astype(float),
        'M': M,
        'X': X,
        'S': S,
        'feature_names_X': X_feature_names,
        'mediator_names': list(M_components.keys()),
        'metadata': metadata,
    }


# =========================================================================
# VLE AGGREGATION HELPERS
# =========================================================================

def _aggregate_vle_cumulative(
    vle_path: Path,
    df_students: pd.DataFrame,
    verbose: bool = True,
    chunksize: int = 1_000_000,
) -> pd.DataFrame:
    """Aggregate total VLE clicks per (student, module, presentation).
    
    Reads in chunks to handle large file.
    """
    if verbose:
        print(f"    Reading studentVle.csv in chunks of {chunksize:,}...")
    
    # We need (id_student, code_module, code_presentation, sum_click)
    # Aggregate as we go
    agg_results = {}
    
    valid_students = set(zip(
        df_students['id_student'],
        df_students['code_module'],
        df_students['code_presentation']
    ))
    
    n_chunks = 0
    for chunk in pd.read_csv(vle_path, chunksize=chunksize):
        n_chunks += 1
        if verbose and n_chunks % 5 == 0:
            print(f"    Processed {n_chunks} chunks...")
        
        chunk_agg = chunk.groupby(
            ['id_student', 'code_module', 'code_presentation']
        )['sum_click'].sum()
        
        for key, val in chunk_agg.items():
            if key in valid_students:
                agg_results[key] = agg_results.get(key, 0) + val
    
    if verbose:
        print(f"    Total chunks processed: {n_chunks}")
        print(f"    Aggregated for {len(agg_results):,} student-sessions")
    
    # Convert to DataFrame
    rows = []
    for (sid, mod, pres), clicks in agg_results.items():
        rows.append({
            'id_student': sid,
            'code_module': mod,
            'code_presentation': pres,
            'sum_clicks': clicks,
        })
    return pd.DataFrame(rows)


def _aggregate_vle_first_quarter(
    vle_path: Path,
    df_students: pd.DataFrame,
    courses: pd.DataFrame,
    verbose: bool = True,
    chunksize: int = 1_000_000,
) -> pd.DataFrame:
    """Aggregate VLE clicks only in first 25% of module days.
    
    More conservative — avoids leakage where late clicks reflect
    outcome (struggling students may click more or less near assessments).
    """
    if verbose:
        print(f"    Reading studentVle.csv (first-quarter aggregation)...")
    
    # Build cutoff per (module, presentation)
    cutoff = courses.copy()
    cutoff['quarter_day'] = cutoff['module_presentation_length'] * 0.25
    cutoff_dict = {
        (row['code_module'], row['code_presentation']): row['quarter_day']
        for _, row in cutoff.iterrows()
    } if 'module_presentation_length' in cutoff.columns else {
        (row['code_module'], row['code_presentation']): row['length'] * 0.25
        for _, row in cutoff.iterrows()
    }
    
    valid_students = set(zip(
        df_students['id_student'],
        df_students['code_module'],
        df_students['code_presentation']
    ))
    
    agg_results = {}
    n_chunks = 0
    
    for chunk in pd.read_csv(vle_path, chunksize=chunksize):
        n_chunks += 1
        if verbose and n_chunks % 5 == 0:
            print(f"    Processed {n_chunks} chunks...")
        
        # Apply cutoff filter
        chunk['cutoff'] = chunk.apply(
            lambda r: cutoff_dict.get((r['code_module'], r['code_presentation']), 1e9),
            axis=1
        )
        chunk_filtered = chunk[chunk['date'] <= chunk['cutoff']]
        
        chunk_agg = chunk_filtered.groupby(
            ['id_student', 'code_module', 'code_presentation']
        )['sum_click'].sum()
        
        for key, val in chunk_agg.items():
            if key in valid_students:
                agg_results[key] = agg_results.get(key, 0) + val
    
    rows = []
    for (sid, mod, pres), clicks in agg_results.items():
        rows.append({
            'id_student': sid,
            'code_module': mod,
            'code_presentation': pres,
            'sum_clicks': clicks,
        })
    return pd.DataFrame(rows)


__all__ = ['load_oulad']
