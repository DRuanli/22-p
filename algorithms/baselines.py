"""
Baseline Methods for HC-DML Comparison
========================================

Implements three baseline approaches:

1. NaivePlugIn: Simple regression-based path-specific effect estimator.
   Uses Pearl's mediation formula with linear/ML regression.
   No cluster handling, no robust inference.

2. SingleLevelDML: Same as HC-DML but without hierarchical cross-fitting.
   Demonstrates the value of cluster-aware cross-fitting.

3. ChiappaVAE: Simplified version of Chiappa 2019 PSCF.
   The original uses VAE with MMD constraints — we implement a 
   simpler neural latent-variable approach that captures the key idea.

Honest limitations:
    - ChiappaVAE is a *simplified* re-implementation, not exact replication.
      Original Chiappa 2019 uses specific VAE architecture with MMD losses.
    - NaivePlugIn assumes correct linear specification — will be biased
      under nonlinearity.
    - These baselines focus on PSE estimation, not fair classifier training.

References:
    Pearl (2001). Direct and indirect effects. UAI.
    Chiappa (2019). Path-Specific Counterfactual Fairness. AAAI.
    Imai, Keele, Yamamoto (2010). Identification, inference and 
        sensitivity analysis for causal mediation effects. 
        Statistical Science.
"""

from __future__ import annotations

from typing import Optional, Dict, List, Tuple, Any
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.ensemble import GradientBoostingRegressor
from scipy import stats


# =========================================================================
# RESULT CONTAINER (shared with HC-DML)
# =========================================================================

from dataclasses import dataclass, field

@dataclass
class BaselineResult:
    """Result container for baseline estimators."""
    method_name: str
    tau_pj_cf: float
    tau_per_path: Dict[str, float]
    se: float
    ci_lower: float
    ci_upper: float
    p_value: float
    n_obs: int
    n_clusters: int
    notes: str = ""
    
    def summary(self) -> str:
        s = f"\n{self.method_name}\n"
        s += "─" * 60 + "\n"
        s += f"τ_PJ-CF = {self.tau_pj_cf:.4f}  "
        s += f"[{self.ci_lower:.4f}, {self.ci_upper:.4f}]  "
        s += f"SE={self.se:.4f}, p={self.p_value:.4g}\n"
        for path, val in self.tau_per_path.items():
            s += f"  {path}: {val:+.4f}\n"
        if self.notes:
            s += f"  Note: {self.notes}\n"
        return s


# =========================================================================
# BASELINE 1: Naive Plug-In Estimator
# =========================================================================

class NaivePlugIn:
    """Pearl mediation formula with simple regression.
    
    NDE_i = μ̂(X_i, 1, M_i^(0)) - μ̂(X_i, 0, M_i^(0))
    NIE_i = μ̂(X_i, 0, M_i^(1)) - μ̂(X_i, 0, M_i^(0))
    
    Where M^(a) is predicted from a simple linear regression of M on (X, A).
    
    Uses ALL data (no cross-fitting) and SINGLE regression model.
    This is the textbook approach taught in mediation analysis courses.
    """
    
    def __init__(
        self,
        paths: List[str] = ('direct', 'via_M'),
        psi: Optional[Dict[str, float]] = None,
        outcome_model: str = 'linear',  # 'linear' or 'gbm'
        bootstrap_n: int = 0,  # 0 = no bootstrap; otherwise # iterations
    ):
        self.paths = list(paths)
        self.psi = psi if psi is not None else {p: 0.0 for p in self.paths}
        self.outcome_model = outcome_model
        self.bootstrap_n = bootstrap_n
    
    def fit(
        self,
        Y: np.ndarray,
        A: np.ndarray,
        M: np.ndarray,
        X: np.ndarray,
        S: Optional[np.ndarray] = None,
        Z: Optional[np.ndarray] = None,
        R: Optional[np.ndarray] = None,
    ) -> BaselineResult:
        n = len(Y)
        if M.ndim == 1:
            M = M.reshape(-1, 1)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if S is None:
            S = np.zeros(n, dtype=int)
        
        # Filter observed A
        valid = ~np.isnan(A) if A.dtype == float else np.ones(n, dtype=bool)
        Y_v, A_v, M_v, X_v = Y[valid], A[valid].astype(float), M[valid], X[valid]
        
        # Fit mediator models: M_j ~ X + A
        m_models = []
        for j in range(M.shape[1]):
            feats = np.column_stack([X_v, A_v.reshape(-1, 1)])
            m = Ridge(alpha=1.0).fit(feats, M_v[:, j])
            m_models.append(m)
        
        # Impute M^(0) and M^(1)
        feats_a0 = np.column_stack([X, np.zeros(n)])
        feats_a1 = np.column_stack([X, np.ones(n)])
        M_a0 = np.column_stack([m.predict(feats_a0) for m in m_models])
        M_a1 = np.column_stack([m.predict(feats_a1) for m in m_models])
        
        # Fit outcome model: Y ~ X + A + M
        outcome_features_v = np.column_stack([X_v, A_v.reshape(-1, 1), M_v])
        if self.outcome_model == 'linear':
            mu_model = LinearRegression().fit(outcome_features_v, Y_v)
        else:
            mu_model = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42).fit(
                outcome_features_v, Y_v
            )
        
        # Predict counterfactual outcomes
        Y_1_M0 = mu_model.predict(np.column_stack([X, np.ones(n), M_a0]))
        Y_0_M0 = mu_model.predict(np.column_stack([X, np.zeros(n), M_a0]))
        Y_0_M1 = mu_model.predict(np.column_stack([X, np.zeros(n), M_a1]))
        
        tau_per_path = {}
        if 'direct' in self.paths:
            tau_per_path['direct'] = float(np.mean(Y_1_M0 - Y_0_M0))
        if 'via_M' in self.paths:
            tau_per_path['via_M'] = float(np.mean(Y_0_M1 - Y_0_M0))
        
        tau_pj_cf = sum(
            (1 - self.psi.get(p, 0.0)) * tau_per_path[p]
            for p in self.paths
        )
        
        # Inference: bootstrap or naive SE
        if self.bootstrap_n > 0:
            boot_estimates = []
            rng = np.random.default_rng(42)
            # Inner fits use bootstrap_n=0 and will emit the "SE collapsed"
            # warning each time for linear outcomes; that's expected here
            # because we use their point estimates only.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for b in range(self.bootstrap_n):
                    idx = rng.integers(0, n, size=n)
                    boot_result = NaivePlugIn(
                        paths=self.paths, psi=self.psi,
                        outcome_model=self.outcome_model, bootstrap_n=0
                    ).fit(Y[idx], A[idx], M[idx], X[idx], S[idx] if S is not None else None)
                    boot_estimates.append(boot_result.tau_pj_cf)
            se = float(np.std(boot_estimates))
        else:
            # Naive SE (assumes IID): use sample-level variance.
            scores = np.zeros(n)
            for p in self.paths:
                if p == 'direct':
                    scores += (1 - self.psi.get(p, 0.0)) * (Y_1_M0 - Y_0_M0)
                elif p == 'via_M':
                    scores += (1 - self.psi.get(p, 0.0)) * (Y_0_M1 - Y_0_M0)
            se = float(np.std(scores, ddof=1) / np.sqrt(n))
            # Linear outcome models make per-obs NDE/NIE constant across i, so
            # the score variance collapses and SE looks like a true zero. That
            # is a degeneracy of the formula, not a precise estimate — surface
            # it as NaN so callers don't build zero-width CIs and report 0%
            # coverage. Set bootstrap_n > 0 for valid inference.
            if se < 1e-10:
                warnings.warn(
                    "NaivePlugIn naive SE collapsed to ~0 (linear outcome makes "
                    "per-observation NDE/NIE constant). Pass bootstrap_n>0 for "
                    "valid inference."
                )
                se = float('nan')

        if not np.isnan(se) and se > 0:
            ci_lower = tau_pj_cf - 1.96 * se
            ci_upper = tau_pj_cf + 1.96 * se
            p_value = 2 * (1 - stats.norm.cdf(abs(tau_pj_cf) / se))
        else:
            ci_lower, ci_upper, p_value = float('nan'), float('nan'), float('nan')
        
        return BaselineResult(
            method_name=f"NaivePlugIn ({self.outcome_model})",
            tau_pj_cf=tau_pj_cf,
            tau_per_path=tau_per_path,
            se=se,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_obs=n,
            n_clusters=len(np.unique(S)) if S is not None else 1,
            notes="No cross-fitting, no cluster-robust SE."
        )


# =========================================================================
# BASELINE 2: Single-Level DML (no cluster handling)
# =========================================================================

class SingleLevelDML:
    """DML with single-level cross-fitting (no cluster awareness).
    
    Same scoring as HC-DML but treats data as IID.
    Cluster information is NOT used.
    
    Purpose: Demonstrates the importance of cluster-aware cross-fitting.
    """
    
    def __init__(
        self,
        paths: List[str] = ('direct', 'via_M'),
        psi: Optional[Dict[str, float]] = None,
        n_folds: int = 5,
    ):
        self.paths = list(paths)
        self.psi = psi if psi is not None else {p: 0.0 for p in self.paths}
        self.n_folds = n_folds
    
    def fit(
        self,
        Y: np.ndarray,
        A: np.ndarray,
        M: np.ndarray,
        X: np.ndarray,
        S: Optional[np.ndarray] = None,
        Z: Optional[np.ndarray] = None,
        R: Optional[np.ndarray] = None,
    ) -> BaselineResult:
        # Delegate to HCDMLEstimator with n_cluster_folds=1 (no cluster CV)
        # and use_cluster_features=False (ignore cluster)
        from hcdml import HCDMLEstimator
        
        if S is None:
            S = np.zeros(len(Y), dtype=int)
        
        est = HCDMLEstimator(
            paths=self.paths,
            psi=self.psi,
            n_folds=self.n_folds,
            n_cluster_folds=1,
            use_cluster_features=False,
            random_state=42,
        )
        result = est.fit(Y, A, M, X, S, Z, R)
        
        return BaselineResult(
            method_name="SingleLevelDML",
            tau_pj_cf=result.tau_pj_cf,
            tau_per_path=result.tau_per_path,
            se=result.se,
            ci_lower=result.ci_lower,
            ci_upper=result.ci_upper,
            p_value=result.p_value,
            n_obs=result.n_obs,
            n_clusters=result.n_clusters,
            notes="Same algorithm as HC-DML but cluster structure ignored."
        )


# =========================================================================
# BASELINE 3: Chiappa 2019 PSCF (simplified)
# =========================================================================

class ChiappaVAE:
    """Simplified implementation of Chiappa 2019 path-specific CF.
    
    Original paper uses VAE with MMD constraints. We implement a 
    simpler latent-variable approach:
    
    1. Infer latent confounders H from observed data via VAE-like model
    2. Use H to predict M and Y while controlling for "unfair" pathways
    3. Compute path-specific effects via counterfactual prediction
    
    Key difference from HC-DML:
    - Uses latent variables to handle unobserved confounders
    - Does NOT use cluster structure
    - Does NOT use cross-fitting (single fit)
    - VAE training is stochastic; results vary across runs
    
    HONEST LIMITATION: This is a 'sketch' of Chiappa 2019, not an
    exact replication. The original paper uses specific architectural
    choices and MMD-based regularization. Our version captures the 
    spirit but not all details. For exact replication, refer to
    Chiappa's original code (if available).
    
    For comparison purposes, this provides a 'latent variable baseline'
    representing the class of methods using deep generative models.
    """
    
    def __init__(
        self,
        paths: List[str] = ('direct', 'via_M'),
        psi: Optional[Dict[str, float]] = None,
        latent_dim: int = 5,
        n_epochs: int = 200,
        learning_rate: float = 0.01,
        bootstrap_n: int = 50,
    ):
        self.paths = list(paths)
        self.psi = psi if psi is not None else {p: 0.0 for p in self.paths}
        self.latent_dim = latent_dim
        self.n_epochs = n_epochs
        self.learning_rate = learning_rate
        self.bootstrap_n = bootstrap_n
    
    def _fit_latent_model(
        self,
        Y: np.ndarray,
        A: np.ndarray,
        M: np.ndarray,
        X: np.ndarray,
    ):
        """Fit a simple latent factor model H ~ Normal | X.
        
        We use a simple linear factor model rather than full VAE for
        reproducibility and simplicity. The latent H captures 
        unobserved variation in (M, Y) not explained by (X, A).
        """
        n = len(Y)
        
        # Step 1: Compute residuals of M and Y after controlling for X, A
        feats_XA = np.column_stack([X, A.reshape(-1, 1)])
        
        M_resid = np.zeros_like(M)
        for j in range(M.shape[1]):
            m_model = Ridge(alpha=1.0).fit(feats_XA, M[:, j])
            M_resid[:, j] = M[:, j] - m_model.predict(feats_XA)
        
        y_model = Ridge(alpha=1.0).fit(np.column_stack([feats_XA, M]), Y)
        Y_resid = Y - y_model.predict(np.column_stack([feats_XA, M]))
        
        # Step 2: Extract latent factors via PCA on residual matrix
        # This is the "latent confounder inference" step in Chiappa 2019
        from sklearn.decomposition import PCA
        residual_matrix = np.column_stack([M_resid, Y_resid.reshape(-1, 1)])
        pca = PCA(n_components=min(self.latent_dim, residual_matrix.shape[1]))
        H = pca.fit_transform(residual_matrix)
        
        # Step 3: Use H + X + A to refit M and Y models (now with H as additional control)
        feats_with_H = np.column_stack([X, A.reshape(-1, 1), H])
        
        m_models_with_H = []
        for j in range(M.shape[1]):
            m_model = Ridge(alpha=1.0).fit(feats_with_H, M[:, j])
            m_models_with_H.append(m_model)
        
        feats_full = np.column_stack([X, A.reshape(-1, 1), M, H])
        y_model_with_H = Ridge(alpha=1.0).fit(feats_full, Y)
        
        return H, m_models_with_H, y_model_with_H
    
    def fit(
        self,
        Y: np.ndarray,
        A: np.ndarray,
        M: np.ndarray,
        X: np.ndarray,
        S: Optional[np.ndarray] = None,
        Z: Optional[np.ndarray] = None,
        R: Optional[np.ndarray] = None,
    ) -> BaselineResult:
        n = len(Y)
        if M.ndim == 1:
            M = M.reshape(-1, 1)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        
        # Filter observed A
        valid = ~np.isnan(A) if A.dtype == float else np.ones(n, dtype=bool)
        Y_v, A_v, M_v, X_v = Y[valid], A[valid].astype(float), M[valid], X[valid]
        n_v = len(Y_v)
        
        # Fit latent model
        H, m_models, y_model = self._fit_latent_model(Y_v, A_v, M_v, X_v)
        
        # Now predict counterfactual outcomes using H + X + A + M
        # For full sample, project to H using PCA fit
        # Simplification: assume H computed only on valid data; use 0 for invalid
        H_full = np.zeros((n, H.shape[1]))
        H_full[valid] = H
        
        # Mediator predictions under A=0 and A=1
        feats_a0_H = np.column_stack([X, np.zeros(n), H_full])
        feats_a1_H = np.column_stack([X, np.ones(n), H_full])
        M_a0 = np.column_stack([m.predict(feats_a0_H) for m in m_models])
        M_a1 = np.column_stack([m.predict(feats_a1_H) for m in m_models])
        
        # Outcome predictions
        Y_1_M0 = y_model.predict(np.column_stack([X, np.ones(n), M_a0, H_full]))
        Y_0_M0 = y_model.predict(np.column_stack([X, np.zeros(n), M_a0, H_full]))
        Y_0_M1 = y_model.predict(np.column_stack([X, np.zeros(n), M_a1, H_full]))
        
        tau_per_path = {}
        if 'direct' in self.paths:
            tau_per_path['direct'] = float(np.mean(Y_1_M0 - Y_0_M0))
        if 'via_M' in self.paths:
            tau_per_path['via_M'] = float(np.mean(Y_0_M1 - Y_0_M0))
        
        tau_pj_cf = sum(
            (1 - self.psi.get(p, 0.0)) * tau_per_path[p]
            for p in self.paths
        )
        
        # Bootstrap for inference
        if self.bootstrap_n > 0 and n > 100:
            boot_estimates = []
            rng = np.random.default_rng(42)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for b in range(self.bootstrap_n):
                    idx = rng.integers(0, n, size=n)
                    try:
                        boot = ChiappaVAE(
                            paths=self.paths, psi=self.psi,
                            latent_dim=self.latent_dim, bootstrap_n=0
                        ).fit(Y[idx], A[idx], M[idx], X[idx])
                        boot_estimates.append(boot.tau_pj_cf)
                    except Exception:
                        continue
            se = float(np.std(boot_estimates)) if boot_estimates else float('nan')
        else:
            # Simple SE from scores. ChiappaVAE's final regression is linear
            # (Ridge), so per-observation NDE/NIE are constant across i and
            # this collapses to ~0 — surface as NaN with a warning rather than
            # producing a misleading zero-width CI.
            scores = np.zeros(n)
            for p in self.paths:
                if p == 'direct':
                    scores += (1 - self.psi.get(p, 0.0)) * (Y_1_M0 - Y_0_M0)
                elif p == 'via_M':
                    scores += (1 - self.psi.get(p, 0.0)) * (Y_0_M1 - Y_0_M0)
            se = float(np.std(scores, ddof=1) / np.sqrt(n))
            if se < 1e-10:
                warnings.warn(
                    "ChiappaVAE naive SE collapsed to ~0 (Ridge outcome makes "
                    "per-observation NDE/NIE constant). Pass bootstrap_n>0 for "
                    "valid inference."
                )
                se = float('nan')
        
        if se > 0 and not np.isnan(se):
            ci_lower = tau_pj_cf - 1.96 * se
            ci_upper = tau_pj_cf + 1.96 * se
            p_value = 2 * (1 - stats.norm.cdf(abs(tau_pj_cf) / se))
        else:
            ci_lower, ci_upper, p_value = float('nan'), float('nan'), float('nan')
        
        return BaselineResult(
            method_name="ChiappaVAE (simplified)",
            tau_pj_cf=tau_pj_cf,
            tau_per_path=tau_per_path,
            se=se,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_obs=n,
            n_clusters=1,
            notes="Simplified Chiappa 2019: PCA latent factors instead of VAE. "
                  f"Bootstrap n={self.bootstrap_n}."
        )


__all__ = ['NaivePlugIn', 'SingleLevelDML', 'ChiappaVAE', 'BaselineResult']
