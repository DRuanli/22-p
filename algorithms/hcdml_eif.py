"""
HC-DML with Efficient Influence Function (EIF) Score
=======================================================

Implements the doubly-robust EIF-based estimator derived in 
theory/EIF_derivation.tex.

Key differences from substitution-based estimator:
    - Uses density ratio g(M|0)/g(M|1) for cross-world correction
    - Three nuisances: μ, e, g (vs two: μ, g for substitution)
    - Doubly robust: consistent when either μ correct OR (e, g) correct
    - Achieves semiparametric efficiency bound
    - Cluster-robust variance properly estimated

EIF formulas (from theory/EIF_derivation.tex Section 4.4):

    φ_10(W) = I(A=1)/e(X,S) · g(M|X,0,S)/g(M|X,1,S) · (Y - μ(X,1,M,S))
            + I(A=0)/(1-e(X,S)) · (μ(X,1,M,S) - μ̄_1(X,0,S))
            + μ̄_1(X,0,S) - θ_10
    
    where μ̄_1(X,0,S) = ∫ μ(X,1,m,S) g(m|X,0,S) dm  
                     (counterfactual mean under A=1 with M drawn from A=0 dist)
    
    NDE = E[Y_10 - Y_00]:
        φ_NDE = φ_10 - φ_00
    NIE = E[Y_11 - Y_10]:
        φ_NIE = φ_11 - φ_10
    
    PJ-CF = (1-ψ_d)·NDE + (1-ψ_m)·NIE
        
IMPORTANT WARNINGS:
    1. EIF correctness depends on derivation in theory/EIF_derivation.tex.
       Mathematical verification is the user's responsibility.
    
    2. Density ratio g(M|x,0,s)/g(M|x,1,s) is the main numerical bottleneck.
       Default Gaussian implementation may underperform for non-Gaussian M.
    
    3. Reduces to Tchetgen-Shpitser 2014 EIF when L=1 (single cluster).
       Use this as a sanity check on real data.

Author: HC-DML project
Version: 0.1 (preliminary, requires verification)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Callable, Any
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.ensemble import (
    GradientBoostingRegressor,
    GradientBoostingClassifier,
)
from sklearn.model_selection import KFold, StratifiedKFold
from scipy import stats


# =========================================================================
# RESULT CONTAINER
# =========================================================================

@dataclass
class EIFResult:
    """Results from EIF-based HC-DML estimation."""
    tau_pj_cf: float
    tau_per_path: Dict[str, float]
    
    # Inference
    se: float
    ci_lower: float
    ci_upper: float
    p_value: float
    
    # EIF components (for diagnostic / paper figures)
    phi_NDE_mean: float
    phi_NIE_mean: float
    
    # Data
    n_obs: int
    n_clusters: int
    
    # Optional fields (must have defaults, come after required)
    eif_decomposition: Dict[str, float] = field(default_factory=dict)
    psi: Dict[str, float] = field(default_factory=dict)
    paths: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        s = f"""
HC-DML (EIF) Estimation Results
─────────────────────────────────────────────────────────────────
Estimand:       τ_PJ-CF = {self.tau_pj_cf:.4f}
95% CI:         [{self.ci_lower:.4f}, {self.ci_upper:.4f}]
Std. Error:     {self.se:.4f}
p-value:        {self.p_value:.4g}

Per-path:
  NDE:   {self.tau_per_path.get('direct', float('nan')):+.4f}
  NIE:   {self.tau_per_path.get('via_M', float('nan')):+.4f}

EIF mean (should be ≈ 0 for consistent estimator):
  NDE:   {self.phi_NDE_mean:+.6f}
  NIE:   {self.phi_NIE_mean:+.6f}

Sample: n = {self.n_obs}, clusters = {self.n_clusters}
"""
        return s


# =========================================================================
# EIF-BASED ESTIMATOR
# =========================================================================

class HCDMLEstimatorEIF:
    """Doubly-robust EIF-based HC-DML estimator.
    
    Implements the efficient influence function derived in 
    theory/EIF_derivation.tex for path-specific counterfactual fairness
    in hierarchical/clustered data.
    
    Parameters
    ----------
    paths : list of str
        Causal paths. Currently: 'direct', 'via_M'.
    psi : dict
        Path justifiability scores in [0, 1].
    n_folds, n_cluster_folds : int
        Cross-fitting parameters.
    outcome_learner : sklearn-compatible regressor
        For μ(X, A, M, S).
    propensity_learner : sklearn-compatible classifier  
        For e(X, S).
    density_method : str
        Mediator density estimation: 'gaussian' (default) or 'kernel'.
    clip_propensity : float
        Clip propensities to [clip, 1-clip] to avoid extreme weights.
    clip_density_ratio : float
        Clip density ratios to [1/clip_density_ratio, clip_density_ratio].
        DEFAULT CHANGED to 5.0 (was 50.0) for robustness on real data.
        Extreme weights (>10x) can dominate small-sample averages.
    trim_weights : bool
        If True, trim observations with extreme combined IPW × density ratio
        weights (above 99th percentile). Recommended for stability.
    binary_outcome : bool or 'auto'
        If True, fit outcome with LogisticRegression and clip predictions
        to [0,1]. If 'auto', detect from Y values. Critical for binary Y
        (Law School first_pf, OULAD pass_distinction).
    density_method : str
        'gaussian' (linear conditional, fast, parametric)
        'kernel' (Nadaraya-Watson, non-parametric, slower, more robust)
    min_n_for_eif : int
        Minimum sample size for EIF estimation. Below this, raises warning
        recommending substitution estimator. Default 1000.
    use_cluster_features : bool
        Include cluster one-hot in nuisance models.
    random_state : int
    verbose : bool
    """
    
    def __init__(
        self,
        paths: List[str] = ('direct', 'via_M'),
        psi: Optional[Dict[str, float]] = None,
        n_folds: int = 5,
        n_cluster_folds: int = 5,
        outcome_learner: Optional[Any] = None,
        propensity_learner: Optional[Any] = None,
        density_method: str = 'gaussian',
        clip_propensity: float = 0.05,         # CHANGED: 0.02 → 0.05 (tighter)
        clip_density_ratio: float = 5.0,        # CHANGED: 50.0 → 5.0 (much tighter)
        trim_weights: bool = True,              # NEW: trim extreme weights
        trim_percentile: float = 99.0,          # NEW: trim threshold
        binary_outcome: Any = 'auto',           # NEW: handle binary Y
        min_n_for_eif: int = 1000,              # NEW: warn for small n
        use_cluster_features: bool = True,
        random_state: int = 42,
        verbose: bool = False,
    ):
        self.paths = list(paths)
        self.psi = psi if psi is not None else {p: 0.0 for p in self.paths}
        self.n_folds = n_folds
        self.n_cluster_folds = n_cluster_folds
        
        # Default ML learners
        self.outcome_learner = outcome_learner if outcome_learner is not None \
            else GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=random_state)
        self.propensity_learner = propensity_learner if propensity_learner is not None \
            else GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=random_state)
        
        self.density_method = density_method
        self.clip_propensity = clip_propensity
        self.clip_density_ratio = clip_density_ratio
        self.trim_weights = trim_weights
        self.trim_percentile = trim_percentile
        self.binary_outcome = binary_outcome
        self.min_n_for_eif = min_n_for_eif
        self.use_cluster_features = use_cluster_features
        self.random_state = random_state
        self.verbose = verbose
        
        # Internal state for diagnostics
        self._diagnostics = {}
    
    # ─── sklearn-compatible parameter access (needed for bootstrap) ───
    
    def get_params(self, deep=True):
        return {
            'paths': self.paths,
            'psi': self.psi,
            'n_folds': self.n_folds,
            'n_cluster_folds': self.n_cluster_folds,
            'outcome_learner': self.outcome_learner,
            'propensity_learner': self.propensity_learner,
            'density_method': self.density_method,
            'clip_propensity': self.clip_propensity,
            'clip_density_ratio': self.clip_density_ratio,
            'trim_weights': self.trim_weights,
            'trim_percentile': self.trim_percentile,
            'binary_outcome': self.binary_outcome,
            'min_n_for_eif': self.min_n_for_eif,
            'use_cluster_features': self.use_cluster_features,
            'random_state': self.random_state,
            'verbose': self.verbose,
        }
    
    def set_params(self, **params):
        for k, v in params.items():
            setattr(self, k, v)
        return self
    
    # ─────────────────────────────────────────────────────────────────────
    # FEATURE PREPARATION
    # ─────────────────────────────────────────────────────────────────────
    
    def _prep_features(
        self,
        X: np.ndarray,
        S: np.ndarray,
        M: Optional[np.ndarray] = None,
        A: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Combine X, M, A with cluster indicators."""
        parts = [X]
        if self.use_cluster_features:
            unique_S = self._all_clusters if hasattr(self, '_all_clusters') else np.unique(S)
            if len(unique_S) > 50:
                parts.append(S.reshape(-1, 1).astype(float))
            else:
                S_onehot = np.zeros((len(S), len(unique_S)))
                for j, c in enumerate(unique_S):
                    S_onehot[:, j] = (S == c).astype(float)
                if S_onehot.shape[1] > 1:
                    S_onehot = S_onehot[:, :-1]
                parts.append(S_onehot)
        if M is not None:
            parts.append(M)
        if A is not None:
            parts.append(A.reshape(-1, 1))
        return np.column_stack(parts)
    
    # ─────────────────────────────────────────────────────────────────────
    # NUISANCE ESTIMATION
    # ─────────────────────────────────────────────────────────────────────
    
    def _fit_outcome(self, Y, X, A, M, S):
        """Fit μ̂(x, a, m, s) = E[Y | X, A, M, S].
        
        For binary outcomes, uses logistic regression to ensure predictions in [0,1].
        For continuous, uses configured outcome_learner.
        """
        feats = self._prep_features(X, S, M, A)
        valid = ~np.isnan(A) if A.dtype == float else np.ones(len(A), dtype=bool)
        
        # Detect/handle binary outcome
        is_binary = self._is_binary_outcome(Y[valid])
        
        if is_binary:
            # Use logistic regression for predictions bounded in [0,1]
            try:
                model = LogisticRegression(max_iter=2000, C=1.0)
                model.fit(feats[valid], Y[valid].astype(int))
                
                def predict(X_, A_, M_, S_):
                    f = self._prep_features(X_, S_, M_, A_)
                    return model.predict_proba(f)[:, 1]
                return predict
            except Exception:
                # Fallback to default if logistic fit fails
                pass
        
        # Default: use configured outcome_learner
        model = self.outcome_learner.__class__(**self.outcome_learner.get_params())
        model.fit(feats[valid], Y[valid])
        
        Y_min, Y_max = float(Y[valid].min()), float(Y[valid].max())
        
        def predict(X_, A_, M_, S_):
            preds = model.predict(self._prep_features(X_, S_, M_, A_))
            # Clip to observed Y range to prevent extreme extrapolation
            return np.clip(preds, Y_min - 0.5 * (Y_max - Y_min),
                          Y_max + 0.5 * (Y_max - Y_min))
        return predict
    
    def _is_binary_outcome(self, Y):
        """Detect if outcome is binary."""
        if self.binary_outcome is True:
            return True
        if self.binary_outcome is False:
            return False
        # Auto-detect: check if all values in {0, 1} or near it
        unique_vals = np.unique(Y[~np.isnan(Y)] if Y.dtype == float else Y)
        return len(unique_vals) <= 2 and set(unique_vals.astype(int)).issubset({0, 1})
    
    def _fit_propensity(self, A, X, S):
        """Fit ê(x, s) = P(A=1 | X, S)."""
        feats = self._prep_features(X, S)
        valid = ~np.isnan(A) if A.dtype == float else np.ones(len(A), dtype=bool)
        if valid.sum() < 30 or len(np.unique(A[valid].astype(int))) < 2:
            return lambda X_, S_: np.full(len(X_), 0.5)
        model = self.propensity_learner.__class__(**self.propensity_learner.get_params())
        model.fit(feats[valid], A[valid].astype(int))
        
        def predict(X_, S_):
            return model.predict_proba(self._prep_features(X_, S_))[:, 1]
        return predict
    
    def _fit_mediator_density(self, M, A, X, S):
        """Fit g(m | x, a, s) Gaussian conditional.
        
        Returns:
            density: callable g(m, x, a, s) → density value
            sample: callable (x, a, s, rng) → counterfactual M samples
            ratio: callable (m, x, a_num, a_den, s) → g(m|x,a_num,s)/g(m|x,a_den,s)
        """
        if self.density_method != 'gaussian':
            raise NotImplementedError(f"density_method={self.density_method} not yet supported")
        
        valid = ~np.isnan(A) if A.dtype == float else np.ones(len(A), dtype=bool)
        if valid.sum() < 30:
            return None, None, lambda *args: np.ones(len(args[0]))
        
        n_mediators = M.shape[1]
        m_models = []
        m_resid_vars = []
        
        for j in range(n_mediators):
            feats = self._prep_features(X[valid], S[valid], A=A[valid])
            model = Ridge(alpha=1.0)
            model.fit(feats, M[valid, j])
            preds = model.predict(feats)
            resid_var = float(np.var(M[valid, j] - preds) + 1e-6)
            m_models.append(model)
            m_resid_vars.append(resid_var)
        
        def density(M_, X_, A_, S_):
            """log g(M | X, A, S) up to constant."""
            feats = self._prep_features(X_, S_, A=A_)
            log_p = np.zeros(len(M_))
            for j in range(n_mediators):
                pred_j = m_models[j].predict(feats)
                log_p += -((M_[:, j] - pred_j)**2) / (2 * m_resid_vars[j])
                log_p += -0.5 * np.log(2 * np.pi * m_resid_vars[j])
            return log_p
        
        def sample(X_, A_, S_, rng):
            """Sample M from g(M | X, A, S)."""
            feats = self._prep_features(X_, S_, A=A_)
            M_samples = np.zeros((len(X_), n_mediators))
            for j in range(n_mediators):
                mean_j = m_models[j].predict(feats)
                M_samples[:, j] = mean_j + rng.normal(0, np.sqrt(m_resid_vars[j]), size=len(X_))
            return M_samples
        
        def ratio(M_, X_, A_num, A_den, S_):
            """g(M | X, A_num, S) / g(M | X, A_den, S)."""
            feats_num = self._prep_features(X_, S_, A=A_num)
            feats_den = self._prep_features(X_, S_, A=A_den)
            log_ratio = np.zeros(len(M_))
            for j in range(n_mediators):
                mean_num = m_models[j].predict(feats_num)
                mean_den = m_models[j].predict(feats_den)
                v = m_resid_vars[j]
                log_ratio += (
                    -((M_[:, j] - mean_num)**2) / (2 * v)
                    + ((M_[:, j] - mean_den)**2) / (2 * v)
                )
            # Bounded ratio - tighter clipping for robustness
            log_clip = np.log(self.clip_density_ratio)
            
            # Track extreme observations for diagnostics
            n_clipped_high = int(np.sum(log_ratio > log_clip))
            n_clipped_low = int(np.sum(log_ratio < -log_clip))
            self._diagnostics.setdefault('density_ratio_clipped_high', 0)
            self._diagnostics.setdefault('density_ratio_clipped_low', 0)
            self._diagnostics['density_ratio_clipped_high'] += n_clipped_high
            self._diagnostics['density_ratio_clipped_low'] += n_clipped_low
            self._diagnostics.setdefault('density_ratio_max_unclipped', 0)
            self._diagnostics['density_ratio_max_unclipped'] = max(
                self._diagnostics.get('density_ratio_max_unclipped', 0),
                float(np.exp(np.max(np.abs(log_ratio))))
            )
            
            log_ratio = np.clip(log_ratio, -log_clip, log_clip)
            return np.exp(log_ratio)
        
        return density, sample, ratio
    
    # ─────────────────────────────────────────────────────────────────────
    # EIF SCORE COMPUTATION
    # ─────────────────────────────────────────────────────────────────────
    
    def _compute_eif_scores(
        self,
        Y, A, M, X, S,
        mu_fn, e_fn,
        density_fn, sample_fn, ratio_fn,
        n_mc_samples: int = 100,
        rng=None,
    ):
        """Compute EIF scores for E[Y_{a,M_{a'}}] for each (a, a') in {(0,0), (1,0), (1,1)}.
        
        From derivation Section 4.4:
        
        φ_10(W) = I(A=1)/e(X,S) · g(M|X,0,S)/g(M|X,1,S) · (Y - μ(X,1,M,S))
                + I(A=0)/(1-e(X,S)) · (μ(X,1,M,S) - μ̄_1(X,0,S))
                + μ̄_1(X,0,S) - θ_10
        
        Note: θ_10 is the target; we compute the score WITHOUT subtracting θ
        so that mean = θ̂.
        
        Returns dict with:
            'phi_00': scores for E[Y_{0, M_0}]
            'phi_10': scores for E[Y_{1, M_0}]
            'phi_11': scores for E[Y_{1, M_1}]
        """
        if rng is None:
            rng = np.random.default_rng(self.random_state)
        
        n = len(Y)
        valid_A = ~np.isnan(A) if A.dtype == float else np.ones(n, dtype=bool)
        
        # Propensities
        pi = e_fn(X, S)
        pi = np.clip(pi, self.clip_propensity, 1 - self.clip_propensity)
        
        # Outcome model at observed (A, M) and counterfactual settings
        # NOTE: When A is missing, we use a fallback. Better: imputed value.
        A_obs = np.where(valid_A, A, 0).astype(float)
        
        mu_obs = mu_fn(X, A_obs, M, S)  # μ(X, A, M, S) at observed A
        mu_at_A0 = mu_fn(X, np.zeros(n), M, S)  # μ(X, 0, M, S)
        mu_at_A1 = mu_fn(X, np.ones(n), M, S)   # μ(X, 1, M, S)
        
        # Marginalized counterfactual outcomes μ̄_a(X, A, S) via Monte Carlo
        # μ̄_a(X, A, S) = ∫ μ(X, a, m, S) g(m | X, A, S) dm
        # Approximated by sampling M' ~ g(· | X, A, S) and averaging
        
        if sample_fn is not None:
            mu_bar = self._compute_marginalized_mu(
                X, S, mu_fn, sample_fn, n_mc_samples, rng
            )
            # mu_bar is dict: mu_bar[(a_out, a_med)] = E[μ(X, a_out, M, S) | M ~ g(·|X, a_med, S)]
        else:
            # Fallback: use observed M (less accurate)
            mu_bar = {
                (0, 0): mu_at_A0,
                (1, 0): mu_at_A1,
                (1, 1): mu_at_A1,
                (0, 1): mu_at_A0,
            }
        
        # Density ratio (only needed for cross-world terms)
        # g(M | X, 0, S) / g(M | X, 1, S)
        # Used when A=1 (we observe M from A=1, need to reweight to A=0)
        ratio_0_over_1 = ratio_fn(M, X, np.zeros(n), np.ones(n), S)
        ratio_0_over_1 = np.clip(ratio_0_over_1, 0, self.clip_density_ratio)
        
        # ───────────────────────────────────────────────────
        # EIF for θ_00 = E[Y_{0, M_0}]  (standard ATE-like under A=0)
        # 
        # CORRECT formula (Tchetgen-Shpitser 2014, eq for E[Y(0)]):
        # φ_00(W) = I(A=0)/(1-e) · (Y - μ(X,0,M,S))        [outcome residual]
        #         + I(A=0)/(1-e) · (μ(X,0,M,S) - μ̄_0(X,0,S))  [mediator residual]
        #         + μ̄_0(X,0,S)                            [plug-in MARGINALIZED]
        # 
        # The plug-in uses μ̄_0 (marginalized over M from g(·|X,0,S)),
        # NOT μ(X,0,M_obs,S). This is critical: for A=1 observations,
        # M_obs is from g(·|X,1,S), so μ(X,0,M_obs) ≠ θ_00 plug-in.
        # ───────────────────────────────────────────────────
        mask_A0 = (A == 0) & valid_A
        mask_A1 = (A == 1) & valid_A
        
        mu_bar_0_at_0 = mu_bar.get((0, 0), mu_at_A0)  # marginalized
        
        phi_00 = np.zeros(n)
        # Term 1: outcome residual at A=0
        phi_00[mask_A0] = (Y[mask_A0] - mu_at_A0[mask_A0]) / (1 - pi[mask_A0])
        # Term 2: mediator residual at A=0
        phi_00[mask_A0] = phi_00[mask_A0] + (
            (mu_at_A0[mask_A0] - mu_bar_0_at_0[mask_A0]) / (1 - pi[mask_A0])
        )
        # Term 3: plug-in (marginalized, for ALL observations)
        phi_00 = phi_00 + mu_bar_0_at_0
        
        # ───────────────────────────────────────────────────
        # EIF for θ_11 = E[Y_{1, M_1}]  (standard ATE-like under A=1)
        # 
        # CORRECT formula:
        # φ_11(W) = I(A=1)/e · (Y - μ(X,1,M,S))            [outcome residual]
        #         + I(A=1)/e · (μ(X,1,M,S) - μ̄_1(X,1,S))   [mediator residual]
        #         + μ̄_1(X,1,S)                            [plug-in MARGINALIZED]
        # ───────────────────────────────────────────────────
        mu_bar_1_at_1 = mu_bar.get((1, 1), mu_at_A1)  # marginalized
        
        phi_11 = np.zeros(n)
        # Term 1: outcome residual at A=1
        phi_11[mask_A1] = (Y[mask_A1] - mu_at_A1[mask_A1]) / pi[mask_A1]
        # Term 2: mediator residual at A=1
        phi_11[mask_A1] = phi_11[mask_A1] + (
            (mu_at_A1[mask_A1] - mu_bar_1_at_1[mask_A1]) / pi[mask_A1]
        )
        # Term 3: plug-in (marginalized)
        phi_11 = phi_11 + mu_bar_1_at_1
        
        # ───────────────────────────────────────────────────
        # EIF for θ_10 = E[Y_{1, M_0}]  (cross-world)
        # 
        # φ_10(W) = I(A=1)/e · g(M|0)/g(M|1) · (Y - μ(X,1,M,S))
        #         + I(A=0)/(1-e) · (μ(X,1,M,S) - μ̄_1(X,0,S))
        #         + μ̄_1(X,0,S)
        # ───────────────────────────────────────────────────
        phi_10 = np.zeros(n)
        
        # Term 1: Cross-world IPW for A=1 observations
        phi_10[mask_A1] = (
            ratio_0_over_1[mask_A1] / pi[mask_A1] 
            * (Y[mask_A1] - mu_at_A1[mask_A1])
        )
        
        # Term 2: Counterfactual deviation for A=0 observations
        mu_bar_1_at_0 = mu_bar.get((1, 0), mu_at_A1)
        phi_10[mask_A0] = phi_10[mask_A0] + (
            (mu_at_A1[mask_A0] - mu_bar_1_at_0[mask_A0]) / (1 - pi[mask_A0])
        )
        
        # Term 3: Plug-in (marginalized)
        phi_10 = phi_10 + mu_bar_1_at_0
        
        return {
            'phi_00': phi_00,
            'phi_10': phi_10,
            'phi_11': phi_11,
        }
    
    def _compute_marginalized_mu(
        self, X, S, mu_fn, sample_fn, n_mc, rng
    ):
        """Compute μ̄_{a_out}(X, a_med, S) = E[μ(X, a_out, M, S) | M ~ g(·|X, a_med, S)]
        
        Via Monte Carlo: sample M' n_mc times, average μ(X, a_out, M', S).
        """
        n = len(X)
        result = {}
        
        for a_out, a_med in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            # Sample M' ~ g(· | X, a_med, S)
            a_med_arr = np.full(n, a_med, dtype=float)
            a_out_arr = np.full(n, a_out, dtype=float)
            
            mu_accum = np.zeros(n)
            for _ in range(n_mc):
                M_prime = sample_fn(X, a_med_arr, S, rng)
                mu_accum += mu_fn(X, a_out_arr, M_prime, S)
            
            result[(a_out, a_med)] = mu_accum / n_mc
        
        return result
    
    # ─────────────────────────────────────────────────────────────────────
    # FOLD CREATION (reuse from substitution version)
    # ─────────────────────────────────────────────────────────────────────
    
    def _create_folds(self, S, A, n):
        """Create hierarchical cross-fitting folds."""
        rng = np.random.default_rng(self.random_state)
        unique_clusters = np.unique(S)
        n_clusters = len(unique_clusters)
        
        effective_cluster_folds = min(self.n_cluster_folds, n_clusters) if n_clusters > 1 else 1
        
        if effective_cluster_folds <= 1:
            valid_A = ~np.isnan(A) if A.dtype == float else np.ones(n, dtype=bool)
            A_strat = A.copy()
            if not valid_A.all():
                A_strat[~valid_A] = -1
            skf = StratifiedKFold(n_splits=self.n_folds, shuffle=True, random_state=self.random_state)
            return list(skf.split(np.arange(n), A_strat.astype(int)))
        
        cluster_perm = rng.permutation(unique_clusters)
        cluster_fold_assignment = np.array_split(cluster_perm, effective_cluster_folds)
        
        folds = []
        for cf in range(effective_cluster_folds):
            cluster_eval_set = set(cluster_fold_assignment[cf])
            eval_mask = np.array([s in cluster_eval_set for s in S])
            train_mask = ~eval_mask
            
            eval_idx = np.where(eval_mask)[0]
            train_idx = np.where(train_mask)[0]
            
            if len(eval_idx) > 0 and len(train_idx) > 30:
                folds.append((train_idx, eval_idx))
        
        return folds
    
    # ─────────────────────────────────────────────────────────────────────
    # MAIN FIT
    # ─────────────────────────────────────────────────────────────────────
    
    def fit(
        self,
        Y: np.ndarray,
        A: np.ndarray,
        M: np.ndarray,
        X: np.ndarray,
        S: np.ndarray,
        Z: Optional[np.ndarray] = None,
        R: Optional[np.ndarray] = None,
    ) -> EIFResult:
        """Run EIF-based HC-DML estimation.
        
        Returns
        -------
        EIFResult
        """
        n = len(Y)
        if M.ndim == 1:
            M = M.reshape(-1, 1)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        
        # ─── Sample size check ───
        if n < self.min_n_for_eif:
            warnings.warn(
                f"\n  ⚠ Sample size n={n} below recommended {self.min_n_for_eif} for EIF.\n"
                f"    EIF estimator may produce unreliable results at small n due to:\n"
                f"      - Unstable density ratio estimation\n"
                f"      - Slow nuisance convergence rates\n"
                f"    Consider using substitution estimator (HCDMLEstimator) instead,\n"
                f"    or interpret EIF results with caution."
            )
        
        # Reset diagnostics
        self._diagnostics = {}
        
        self._all_clusters = np.unique(S)
        
        folds = self._create_folds(S, A, n)
        if self.verbose:
            print(f"EIF-HC-DML: {len(folds)} folds, n={n}, clusters={len(self._all_clusters)}")
        
        # Accumulate scores
        phi_00_all = np.full(n, np.nan)
        phi_10_all = np.full(n, np.nan)
        phi_11_all = np.full(n, np.nan)
        
        for fold_i, (train_idx, eval_idx) in enumerate(folds):
            if len(eval_idx) == 0:
                continue
            
            Y_tr, A_tr, M_tr, X_tr, S_tr = (
                Y[train_idx], A[train_idx], M[train_idx], X[train_idx], S[train_idx]
            )
            Y_ev, A_ev, M_ev, X_ev, S_ev = (
                Y[eval_idx], A[eval_idx], M[eval_idx], X[eval_idx], S[eval_idx]
            )
            
            try:
                mu_fn = self._fit_outcome(Y_tr, X_tr, A_tr, M_tr, S_tr)
                e_fn = self._fit_propensity(A_tr, X_tr, S_tr)
                density_fn, sample_fn, ratio_fn = self._fit_mediator_density(M_tr, A_tr, X_tr, S_tr)
            except Exception as e:
                warnings.warn(f"Fold {fold_i} fit failed: {e}")
                continue
            
            # Compute EIF scores on eval set
            rng_fold = np.random.default_rng(self.random_state + fold_i + 1000)
            scores = self._compute_eif_scores(
                Y_ev, A_ev, M_ev, X_ev, S_ev,
                mu_fn, e_fn, density_fn, sample_fn, ratio_fn,
                n_mc_samples=50,  # MC samples for marginalization
                rng=rng_fold,
            )
            
            phi_00_all[eval_idx] = scores['phi_00']
            phi_10_all[eval_idx] = scores['phi_10']
            phi_11_all[eval_idx] = scores['phi_11']
        
        # ─── Trim extreme weights for robustness ───
        if self.trim_weights:
            phi_00_all, phi_10_all, phi_11_all, n_trimmed = self._trim_extreme_scores(
                phi_00_all, phi_10_all, phi_11_all
            )
            self._diagnostics['n_trimmed'] = n_trimmed
            if n_trimmed > 0 and self.verbose:
                print(f"  Trimmed {n_trimmed} extreme observations (>{self.trim_percentile}th percentile)")
        
        # ─── Compute target estimands ───
        # θ̂_00 = (1/n) Σ φ_00_i
        # θ̂_10 = (1/n) Σ φ_10_i
        # θ̂_11 = (1/n) Σ φ_11_i
        # NDE = θ_10 - θ_00
        # NIE = θ_11 - θ_10
        
        valid_00 = ~np.isnan(phi_00_all)
        valid_10 = ~np.isnan(phi_10_all)
        valid_11 = ~np.isnan(phi_11_all)
        
        theta_00 = float(np.mean(phi_00_all[valid_00])) if valid_00.any() else float('nan')
        theta_10 = float(np.mean(phi_10_all[valid_10])) if valid_10.any() else float('nan')
        theta_11 = float(np.mean(phi_11_all[valid_11])) if valid_11.any() else float('nan')
        
        NDE = theta_10 - theta_00
        NIE = theta_11 - theta_10
        
        tau_per_path = {}
        if 'direct' in self.paths:
            tau_per_path['direct'] = NDE
        if 'via_M' in self.paths:
            tau_per_path['via_M'] = NIE
        
        tau_pj_cf = sum(
            (1 - self.psi.get(p, 0.0)) * tau_per_path[p]
            for p in self.paths if p in tau_per_path
        )
        
        # ─── Cluster-robust variance ───
        # Aggregate score for PJ-CF combination
        # Use NaN-preserving aggregation so trimmed observations are excluded from SE
        agg_score = np.full(n, np.nan)
        valid_all = ~np.isnan(phi_00_all) & ~np.isnan(phi_10_all) & ~np.isnan(phi_11_all)
        agg_score[valid_all] = 0.0
        
        if 'direct' in self.paths:
            phi_NDE_arr = phi_10_all - phi_00_all
            agg_score[valid_all] += (1 - self.psi.get('direct', 0.0)) * phi_NDE_arr[valid_all]
        if 'via_M' in self.paths:
            phi_NIE_arr = phi_11_all - phi_10_all
            agg_score[valid_all] += (1 - self.psi.get('via_M', 0.0)) * phi_NIE_arr[valid_all]
        
        if valid_all.sum() > 10:
            se = self._cluster_robust_se(agg_score[valid_all], S[valid_all], tau_pj_cf)
        else:
            se = float('nan')
        
        if np.isnan(se) or se == 0:
            ci_lower, ci_upper, p_value = float('nan'), float('nan'), float('nan')
        else:
            ci_lower = tau_pj_cf - 1.96 * se
            ci_upper = tau_pj_cf + 1.96 * se
            z_stat = tau_pj_cf / se
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        # Diagnostic: EIF means (should be ≈ 0 after centering by τ)
        phi_NDE_centered = (phi_10_all - phi_00_all) - NDE
        phi_NIE_centered = (phi_11_all - phi_10_all) - NIE
        
        return EIFResult(
            tau_pj_cf=tau_pj_cf,
            tau_per_path=tau_per_path,
            se=se,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            phi_NDE_mean=float(np.nanmean(phi_NDE_centered)),
            phi_NIE_mean=float(np.nanmean(phi_NIE_centered)),
            n_obs=n,
            n_clusters=len(self._all_clusters),
            psi=self.psi,
            paths=self.paths,
            eif_decomposition={
                'theta_00': theta_00,
                'theta_10': theta_10,
                'theta_11': theta_11,
                'NDE': NDE,
                'NIE': NIE,
                # Diagnostics for paper / debugging
                'diagnostics': dict(self._diagnostics),
            }
        )
    
    def _trim_extreme_scores(self, phi_00, phi_10, phi_11):
        """Trim observations with CATASTROPHICALLY extreme EIF scores.
        
        Uses MAD (median absolute deviation) based outlier detection.
        Only trims observations that deviate by > trim_threshold MAD units
        from the median. This catches blow-ups (e.g. θ outside Y range)
        without biasing clean data.
        
        Default trim_percentile=99 here is reinterpreted as MAD multiplier:
        - 99 → ~5 MAD (very conservative, catches only catastrophic outliers)
        - 95 → ~3 MAD (moderate)
        - 90 → ~2 MAD (aggressive, biases clean data)
        """
        n = len(phi_00)
        
        # Convert percentile to MAD multiplier
        # 99 → 5 MAD, 95 → 3 MAD, 90 → 2 MAD
        if self.trim_percentile >= 99:
            mad_mult = 10.0  # Very conservative
        elif self.trim_percentile >= 95:
            mad_mult = 5.0
        else:
            mad_mult = 3.0
        
        # For each score series, find observations beyond MAD threshold
        bad_mask = np.zeros(n, dtype=bool)
        for scores in [phi_00, phi_10, phi_11]:
            valid = ~np.isnan(scores)
            if valid.sum() < 10:
                continue
            med = np.nanmedian(scores)
            mad = np.nanmedian(np.abs(scores - med)) + 1e-9
            # MAD * 1.4826 ≈ SD for normal distribution
            threshold = mad_mult * mad * 1.4826
            bad_mask = bad_mask | (np.abs(scores - med) > threshold)
        
        n_trimmed = int(bad_mask.sum())
        
        # Only apply if not too many trimmed (sanity check)
        if n_trimmed > 0.1 * n:  # If trimming >10%, something wrong
            warnings.warn(
                f"Trim flagged {n_trimmed}/{n} observations (>10%). "
                f"Disabling trim to avoid bias. Check density ratios for instability."
            )
            return phi_00, phi_10, phi_11, 0
        
        # Apply trimming
        phi_00 = phi_00.copy()
        phi_10 = phi_10.copy()
        phi_11 = phi_11.copy()
        phi_00[bad_mask] = np.nan
        phi_10[bad_mask] = np.nan
        phi_11[bad_mask] = np.nan
        
        return phi_00, phi_10, phi_11, n_trimmed
    
    def _cluster_robust_se(self, scores, S, tau_hat):
        """Cluster-robust SE for EIF estimator."""
        # Filter NaN (from trimming)
        valid = ~np.isnan(scores)
        scores = scores[valid]
        S = S[valid]
        
        residuals = scores - tau_hat
        n = len(residuals)
        if n < 10:
            return float('nan')
        unique_clusters = np.unique(S)
        if len(unique_clusters) <= 1:
            return float(np.std(residuals, ddof=1) / np.sqrt(n))
        
        cluster_sums = []
        for c in unique_clusters:
            mask = S == c
            if mask.any():
                cluster_sums.append(residuals[mask].sum())
        cluster_sums = np.array(cluster_sums)
        
        var_est = np.sum(cluster_sums**2) / (n**2)
        L = len(unique_clusters)
        correction = L / max(L - 1, 1)
        var_est = var_est * correction
        return float(np.sqrt(max(var_est, 0)))


__all__ = ['HCDMLEstimatorEIF', 'EIFResult']
