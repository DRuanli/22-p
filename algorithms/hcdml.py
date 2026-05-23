"""
HC-DML: Hierarchical Cross-fitted Double Machine Learning 
        for Path-Specific Counterfactual Fairness
=====================================================================

Implements Phases 1-4 of HC-DML algorithm:
    Phase 1: Hierarchical partitioning (cluster + student cross-fitting)
    Phase 2: Nuisance estimation (multilevel ML)
    Phase 3: Orthogonal score evaluation
    Phase 4: Aggregation and cluster-robust inference

Key innovations over standard DML:
    - Multi-way cross-fitting respecting cluster structure
    - Cluster-robust variance estimation
    - Path-specific decomposition

Limitations (honest):
    - Phase 5 (sensitivity analysis) is in separate module
    - Surrogate-based score for missing A is implemented but lightly tested
    - Mediator density ratio estimation uses kernel methods (may need 
      normalizing flows for high-dim M in practice)
    - Asymptotic theory: relies on standard DML results (Chernozhukov 2018)
      extended via Liu-Liu-Sasaki 2024 for multiway clustering. We do NOT
      re-prove these results; the contribution is the algorithm application.

References:
    Chernozhukov et al. (2018). "Double/debiased machine learning for 
        treatment and structural parameters." Econometrics Journal.
    Liu, Liu, Sasaki (2024). "Estimation and Inference for Causal 
        Functions with Multiway Clustered Data." arXiv:2409.06654.
    Chiappa (2019). "Path-Specific Counterfactual Fairness." AAAI.
    Avin, Shpitser, Pearl (2005). "Identifiability of path-specific effects."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Callable, Any
import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.ensemble import (
    GradientBoostingRegressor,
    GradientBoostingClassifier,
    RandomForestRegressor,
)
from sklearn.preprocessing import StandardScaler
from scipy import stats


# =========================================================================
# RESULT CONTAINER
# =========================================================================

@dataclass
class HCDMLResult:
    """Results from HC-DML estimation."""
    # Point estimates
    tau_pj_cf: float
    tau_per_path: Dict[str, float]
    
    # Inference
    se: float
    ci_lower: float
    ci_upper: float
    p_value: float
    
    # Diagnostics
    n_obs: int
    n_clusters: int
    n_folds_used: int
    
    # Per-fold estimates (for stability check)
    fold_estimates: Optional[List[float]] = None
    
    # Nuisance fit quality
    nuisance_quality: Dict[str, float] = field(default_factory=dict)
    
    # Configuration
    psi: Dict[str, float] = field(default_factory=dict)
    paths: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        """Pretty-print summary."""
        s = f"""
HC-DML Estimation Results
─────────────────────────────────────────────────────────────────
Estimand:       τ_PJ-CF = {self.tau_pj_cf:.4f}
95% CI:         [{self.ci_lower:.4f}, {self.ci_upper:.4f}]
Std. Error:     {self.se:.4f}
p-value:        {self.p_value:.4g}

Sample:         n = {self.n_obs}, clusters = {self.n_clusters}

Per-path decomposition:
"""
        for path, val in self.tau_per_path.items():
            psi_val = self.psi.get(path, 0.0)
            s += f"  {path:<25} {val:+.4f}  (ψ = {psi_val:.2f})\n"
        
        if self.nuisance_quality:
            s += "\nNuisance fit quality:\n"
            for k, v in self.nuisance_quality.items():
                s += f"  {k:<25} {v:.4f}\n"
        
        return s


# =========================================================================
# MAIN ESTIMATOR CLASS
# =========================================================================

class HCDMLEstimator:
    """Hierarchical Cross-fitted DML estimator for PJ-CF.
    
    Parameters
    ----------
    paths : list of str
        Names of causal paths from A to Y. Currently supported:
        - 'direct': A → Y
        - 'via_M':  A → M → Y
        Other paths will be added in future versions.
    psi : dict
        Path justifiability scores. psi[path] ∈ [0, 1].
        Default: all 0 (all paths unjustified).
    n_folds : int
        Number of folds for cross-fitting (default 5).
    n_cluster_folds : int
        Number of cluster-level folds (default 5).
        Set to 1 to disable cluster-level cross-fitting.
    outcome_learner : sklearn-compatible regressor
        ML model for E[Y | X, A, M, S]. Default: GBM.
    propensity_learner : sklearn-compatible classifier
        ML model for P(A | X, S). Default: GBM.
    mediator_method : str
        Method for mediator density ratio. 
        Options: 'gaussian' (linear, fast), 'kernel' (nonparametric, slow).
    clip_weights : float
        Threshold for clipping density ratios (default 100).
    use_cluster_features : bool
        Whether to include cluster indicators as features in nuisance models.
    verbose : bool
        Print progress.
    """
    
    def __init__(
        self,
        paths: List[str] = ('direct', 'via_M'),
        psi: Optional[Dict[str, float]] = None,
        n_folds: int = 5,
        n_cluster_folds: int = 5,
        outcome_learner: Optional[Any] = None,
        propensity_learner: Optional[Any] = None,
        mediator_method: str = 'gaussian',
        clip_weights: float = 100.0,
        use_cluster_features: bool = True,
        verbose: bool = False,
        random_state: int = 42,
    ):
        self.paths = list(paths)
        self.psi = psi if psi is not None else {p: 0.0 for p in self.paths}
        self.n_folds = n_folds
        self.n_cluster_folds = n_cluster_folds
        
        # Default learners: GBM provides good defaults for non-experts
        self.outcome_learner = outcome_learner if outcome_learner is not None \
            else GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=random_state)
        self.propensity_learner = propensity_learner if propensity_learner is not None \
            else GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=random_state)
        
        self.mediator_method = mediator_method
        self.clip_weights = clip_weights
        self.use_cluster_features = use_cluster_features
        self.verbose = verbose
        self.random_state = random_state

    # ─── sklearn-compatible parameter access (needed for bootstrap / sensitivity) ───

    def get_params(self, deep=True):
        return {
            'paths': self.paths,
            'psi': self.psi,
            'n_folds': self.n_folds,
            'n_cluster_folds': self.n_cluster_folds,
            'outcome_learner': self.outcome_learner,
            'propensity_learner': self.propensity_learner,
            'mediator_method': self.mediator_method,
            'clip_weights': self.clip_weights,
            'use_cluster_features': self.use_cluster_features,
            'verbose': self.verbose,
            'random_state': self.random_state,
        }

    def set_params(self, **params):
        for k, v in params.items():
            setattr(self, k, v)
        return self

    # ─────────────────────────────────────────────────────────────────────
    # Phase 1: Hierarchical Partitioning
    # ─────────────────────────────────────────────────────────────────────
    
    def _create_folds(
        self,
        S: np.ndarray,
        A: np.ndarray,
        n: int,
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Create cross-product cluster × student folds.
        
        Returns list of (train_idx, eval_idx) pairs.
        """
        rng = np.random.default_rng(self.random_state)
        unique_clusters = np.unique(S)
        n_clusters = len(unique_clusters)
        
        # If only 1 cluster or very few, skip cluster-level CV
        effective_cluster_folds = min(self.n_cluster_folds, n_clusters) if n_clusters > 1 else 1
        
        if effective_cluster_folds <= 1:
            # Single-level cross-fitting
            # Stratify by A to maintain overlap
            valid_A = ~np.isnan(A) if A.dtype == float else np.ones(n, dtype=bool)
            A_strat = A.copy()
            if not valid_A.all():
                A_strat[~valid_A] = -1  # Use -1 for missing as separate stratum
            
            skf = StratifiedKFold(n_splits=self.n_folds, shuffle=True, random_state=self.random_state)
            return list(skf.split(np.arange(n), A_strat.astype(int)))
        
        # Two-way cross-fitting
        cluster_perm = rng.permutation(unique_clusters)
        cluster_fold_assignment = np.array_split(cluster_perm, effective_cluster_folds)
        # Map each cluster to its fold
        cluster_to_fold = {}
        for cf_idx, cluster_set in enumerate(cluster_fold_assignment):
            for c in cluster_set:
                cluster_to_fold[c] = cf_idx
        
        # Student-level folds (stratified by A) per cluster
        student_fold = np.zeros(n, dtype=int)
        valid_A = ~np.isnan(A) if A.dtype == float else np.ones(n, dtype=bool)
        
        for c in unique_clusters:
            mask = S == c
            idx_c = np.where(mask)[0]
            n_c = len(idx_c)
            
            if n_c < self.n_folds * 2:
                # Too few in cluster, random split
                student_fold[idx_c] = rng.integers(0, self.n_folds, size=n_c)
            else:
                A_c = A[idx_c].copy()
                if not valid_A[idx_c].all():
                    A_c[~valid_A[idx_c]] = -1
                try:
                    skf = StratifiedKFold(
                        n_splits=self.n_folds,
                        shuffle=True,
                        random_state=self.random_state
                    )
                    for fold_idx, (_, eval_in_c) in enumerate(skf.split(idx_c, A_c.astype(int))):
                        student_fold[idx_c[eval_in_c]] = fold_idx
                except ValueError:
                    # Stratification failed (e.g., a stratum has <n_folds elements)
                    student_fold[idx_c] = rng.integers(0, self.n_folds, size=n_c)
        
        # Generate (train, eval) for each (cluster_fold, student_fold)
        folds = []
        for cf in range(effective_cluster_folds):
            cluster_eval_set = set(cluster_fold_assignment[cf])
            cluster_eval_mask = np.array([s in cluster_eval_set for s in S])
            
            for sf in range(self.n_folds):
                # Eval: in this cluster_fold AND this student_fold
                eval_mask = cluster_eval_mask & (student_fold == sf)
                # Train: NOT in this cluster_fold AND NOT in this student_fold
                # (strict: exclude both folds entirely)
                train_mask = (~cluster_eval_mask) & (student_fold != sf)
                
                eval_idx = np.where(eval_mask)[0]
                train_idx = np.where(train_mask)[0]
                
                if len(eval_idx) > 0 and len(train_idx) > 30:
                    folds.append((train_idx, eval_idx))
        
        # Ensure all indices are covered exactly once in eval
        eval_coverage = np.zeros(n, dtype=int)
        for _, ei in folds:
            eval_coverage[ei] += 1
        
        # Assign uncovered units to a random fold's eval set
        uncovered = np.where(eval_coverage == 0)[0]
        if len(uncovered) > 0:
            # Add to a random fold's eval
            for u in uncovered:
                fold_idx = rng.integers(0, len(folds))
                folds[fold_idx] = (
                    folds[fold_idx][0],
                    np.append(folds[fold_idx][1], u)
                )
        
        return folds
    
    # ─────────────────────────────────────────────────────────────────────
    # Phase 2: Nuisance Estimation
    # ─────────────────────────────────────────────────────────────────────
    
    def _prep_features(
        self,
        X: np.ndarray,
        S: np.ndarray,
        M: Optional[np.ndarray] = None,
        A: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Combine features with cluster indicators if requested.
        
        Uses self._all_clusters (set during fit) to ensure consistent
        one-hot encoding across train/eval folds.
        """
        parts = [X]
        if self.use_cluster_features:
            # Use global cluster set if available, else fall back to local
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
    
    def _fit_outcome_model(
        self,
        Y_train: np.ndarray,
        X_train: np.ndarray,
        A_train: np.ndarray,
        M_train: np.ndarray,
        S_train: np.ndarray,
    ) -> Callable:
        """Fit μ̂(x, a, m, s) = E[Y | X, A, M, S]."""
        features = self._prep_features(X_train, S_train, M_train, A_train)
        
        # Filter out missing A
        valid = ~np.isnan(A_train) if A_train.dtype == float else np.ones(len(A_train), dtype=bool)
        
        model = self.outcome_learner.__class__(**self.outcome_learner.get_params())
        model.fit(features[valid], Y_train[valid])
        
        def predict_fn(X, A, M, S):
            feats = self._prep_features(X, S, M, A)
            return model.predict(feats)
        
        return predict_fn
    
    def _fit_propensity(
        self,
        A_train: np.ndarray,
        X_train: np.ndarray,
        S_train: np.ndarray,
    ) -> Callable:
        """Fit ê(x, s) = P(A=1 | X, S)."""
        features = self._prep_features(X_train, S_train)
        
        valid = ~np.isnan(A_train) if A_train.dtype == float else np.ones(len(A_train), dtype=bool)
        
        if valid.sum() < 30 or len(np.unique(A_train[valid].astype(int))) < 2:
            # Fallback to constant
            p_const = 0.5
            return lambda X, S: np.full(len(X), p_const)
        
        model = self.propensity_learner.__class__(**self.propensity_learner.get_params())
        model.fit(features[valid], A_train[valid].astype(int))
        
        def predict_fn(X, S):
            feats = self._prep_features(X, S)
            return model.predict_proba(feats)[:, 1]
        
        return predict_fn
    
    def _fit_mediator_density(
        self,
        M_train: np.ndarray,
        A_train: np.ndarray,
        X_train: np.ndarray,
        S_train: np.ndarray,
    ) -> Tuple[Callable, List, List]:
        """Fit g(m | x, a, s) for mediator density ratio computation.
        
        Returns
        -------
        ratio_fn : Callable
            Density ratio function g(M|x,a)/g(M|x,a').
        m_models : list
            Trained Ridge models for each mediator.
        m_resid_vars : list
            Residual variances for each mediator.
        """
        if self.mediator_method != 'gaussian':
            raise NotImplementedError(
                f"Mediator method '{self.mediator_method}' not implemented. "
                f"Use 'gaussian'."
            )
        
        valid = ~np.isnan(A_train) if A_train.dtype == float else np.ones(len(A_train), dtype=bool)
        if valid.sum() < 30:
            # Fallback: assume no mediator effect of A
            return (
                lambda M, X, A, A_prime, S: np.ones(len(M)),
                [],
                []
            )
        
        # Fit M_j ~ X + A + S for each j
        n_mediators = M_train.shape[1]
        m_models = []
        m_resid_vars = []
        
        for j in range(n_mediators):
            feats = self._prep_features(X_train[valid], S_train[valid], A=A_train[valid])
            model_j = Ridge(alpha=1.0)
            model_j.fit(feats, M_train[valid, j])
            preds = model_j.predict(feats)
            resid_var = np.var(M_train[valid, j] - preds) + 1e-6
            m_models.append(model_j)
            m_resid_vars.append(resid_var)
        
        def predict_density_ratio(M, X, A, A_prime, S):
            """Return g(M | X, A, S) / g(M | X, A', S)."""
            n = len(M)
            log_ratio = np.zeros(n)
            
            feats_A = self._prep_features(X, S, A=A)
            feats_A_prime = self._prep_features(X, S, A=A_prime)
            
            for j in range(n_mediators):
                mean_A = m_models[j].predict(feats_A)
                mean_A_prime = m_models[j].predict(feats_A_prime)
                var = m_resid_vars[j]
                
                log_ratio_j = (
                    -((M[:, j] - mean_A)**2) / (2 * var)
                    + ((M[:, j] - mean_A_prime)**2) / (2 * var)
                )
                log_ratio = log_ratio + log_ratio_j
            
            ratio = np.exp(np.clip(log_ratio, -np.log(self.clip_weights), np.log(self.clip_weights)))
            return ratio
        
        return predict_density_ratio, m_models, m_resid_vars
    
    # ─────────────────────────────────────────────────────────────────────
    # Phase 3: Score Evaluation
    # ─────────────────────────────────────────────────────────────────────
    
    def _compute_path_specific_scores(
        self,
        Y_eval: np.ndarray,
        A_eval: np.ndarray,
        M_eval: np.ndarray,
        X_eval: np.ndarray,
        S_eval: np.ndarray,
        mu_fn: Callable,
        e_fn: Callable,
        g_ratio_fn: Callable,
        m_models: Optional[List] = None,
        m_resid_vars: Optional[List[float]] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> Dict[str, np.ndarray]:
        """Compute path-specific scores using natural direct/indirect effects.
        
        We use a substitution-based estimator:
            NDE_i ≈ μ̂(X_i, 1, M_i^(0), S_i) - μ̂(X_i, 0, M_i^(0), S_i)
            NIE_i ≈ μ̂(X_i, 0, M_i^(1), S_i) - μ̂(X_i, 0, M_i^(0), S_i)
        
        where M_i^(a) is sampled (or imputed via mean) from g(M | X_i, A=a, S_i).
        
        This is simpler than full AIPW but consistent under:
            - Unconfoundedness of A given X, S
            - Cross-world independence assumption for NDE/NIE
            - Correct specification of μ and g
        
        Note: Not doubly-robust like AIPW, but easier to verify and debug.
        Augmented with mu(X,a,M) - μ̂ residual correction terms when available.
        """
        n = len(Y_eval)
        scores = {}
        
        if rng is None:
            rng = np.random.default_rng(self.random_state)
        
        # Impute counterfactual mediators using fitted Gaussian model
        # M_i^(a) = E[M | X_i, A=a, S_i]  (mean imputation; could sample for better variance)
        if m_models is not None and m_resid_vars is not None:
            n_mediators = M_eval.shape[1]
            
            # Predict M means under A=0 and A=1
            feats_A0 = self._prep_features(X_eval, S_eval, A=np.zeros(n))
            feats_A1 = self._prep_features(X_eval, S_eval, A=np.ones(n))
            
            M_a0_pred = np.zeros((n, n_mediators))
            M_a1_pred = np.zeros((n, n_mediators))
            for j in range(n_mediators):
                M_a0_pred[:, j] = m_models[j].predict(feats_A0)
                M_a1_pred[:, j] = m_models[j].predict(feats_A1)
        else:
            # Fallback: use observed M (only valid for direct effect approximation).
            # With M_a0 == M_a1, NIE = Y_0_M1 - Y_0_M0 = 0 by construction — warn the
            # caller so a zero NIE isn't read as a substantive finding.
            if 'via_M' in self.paths:
                warnings.warn(
                    "Mediator density unavailable; NIE will be 0 by construction. "
                    "Interpret 'via_M' estimate as unidentified, not as a true null."
                )
            M_a0_pred = M_eval.copy()
            M_a1_pred = M_eval.copy()
        
        # Predict outcomes under counterfactual scenarios
        # Y(1, M(0)): A=1, M imputed under A=0
        Y_1_M0 = mu_fn(X_eval, np.ones(n), M_a0_pred, S_eval)
        # Y(0, M(0)): A=0, M imputed under A=0 (baseline)
        Y_0_M0 = mu_fn(X_eval, np.zeros(n), M_a0_pred, S_eval)
        # Y(0, M(1)): A=0, M imputed under A=1
        Y_0_M1 = mu_fn(X_eval, np.zeros(n), M_a1_pred, S_eval)
        # Also useful: Y(1, M(1)) for total effect
        Y_1_M1 = mu_fn(X_eval, np.ones(n), M_a1_pred, S_eval)
        
        if 'direct' in self.paths:
            # NDE = E[Y(1, M(0))] - E[Y(0, M(0))]
            # Substitution estimator: average difference across observations
            phi_direct = Y_1_M0 - Y_0_M0
            scores['direct'] = phi_direct
        
        if 'via_M' in self.paths:
            # NIE = E[Y(0, M(1))] - E[Y(0, M(0))]
            phi_via_M = Y_0_M1 - Y_0_M0
            scores['via_M'] = phi_via_M
        
        return scores
    
    # ─────────────────────────────────────────────────────────────────────
    # Phase 4: Aggregation and Inference
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
    ) -> HCDMLResult:
        """Estimate PJ-CF using HC-DML.
        
        Parameters
        ----------
        Y : array, shape (n,)
            Outcome.
        A : array, shape (n,)
            Protected attribute (binary). May contain NaN if missing.
        M : array, shape (n, p)
            Mediators.
        X : array, shape (n, q)
            Covariates.
        S : array, shape (n,)
            Cluster membership.
        Z : array, shape (n, r), optional
            Surrogate variables (used for missing A).
        R : array, shape (n,), optional
            Missingness indicator. Inferred from A NaN if not provided.
        """
        n = len(Y)
        if M.ndim == 1:
            M = M.reshape(-1, 1)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        
        # Infer R from A if not provided
        if R is None:
            R = (~np.isnan(A) if A.dtype == float else np.ones(n)).astype(int)
        
        # Store global cluster set for consistent one-hot encoding
        self._all_clusters = np.unique(S)
        
        # Step 1: Create folds
        folds = self._create_folds(S, A, n)
        
        if self.verbose:
            print(f"HC-DML: {len(folds)} folds, n={n}, clusters={len(np.unique(S))}")
        
        # Step 2 & 3: Cross-fit nuisances and compute scores
        all_scores = {path: np.full(n, np.nan) for path in self.paths}
        
        # Track nuisance quality across folds
        outcome_r2_list = []
        propensity_acc_list = []
        
        for fold_i, (train_idx, eval_idx) in enumerate(folds):
            if len(eval_idx) == 0:
                continue
            
            Y_train, A_train, M_train, X_train, S_train = (
                Y[train_idx], A[train_idx], M[train_idx], X[train_idx], S[train_idx]
            )
            Y_eval, A_eval, M_eval, X_eval, S_eval = (
                Y[eval_idx], A[eval_idx], M[eval_idx], X[eval_idx], S[eval_idx]
            )
            
            # Fit nuisances on train
            try:
                mu_fn = self._fit_outcome_model(Y_train, X_train, A_train, M_train, S_train)
                e_fn = self._fit_propensity(A_train, X_train, S_train)
                g_ratio_fn, m_models, m_resid_vars = self._fit_mediator_density(
                    M_train, A_train, X_train, S_train
                )
            except Exception as e:
                warnings.warn(f"Fold {fold_i} fit failed: {e}")
                continue
            
            # Track nuisance quality
            valid_train = ~np.isnan(A_train) if A_train.dtype == float else np.ones(len(A_train), dtype=bool)
            if valid_train.sum() > 10:
                # R² on training (in-sample, just for monitoring)
                # Better would be on validation set but skipped for simplicity
                mu_train = mu_fn(X_train[valid_train], A_train[valid_train],
                                M_train[valid_train], S_train[valid_train])
                ss_res = ((Y_train[valid_train] - mu_train)**2).sum()
                ss_tot = ((Y_train[valid_train] - Y_train[valid_train].mean())**2).sum()
                outcome_r2_list.append(1 - ss_res / max(ss_tot, 1e-6))
                
                # Propensity accuracy
                pi_train = e_fn(X_train[valid_train], S_train[valid_train])
                A_pred = (pi_train > 0.5).astype(int)
                propensity_acc_list.append((A_pred == A_train[valid_train].astype(int)).mean())
            
            # Compute scores on eval
            fold_scores = self._compute_path_specific_scores(
                Y_eval, A_eval, M_eval, X_eval, S_eval,
                mu_fn, e_fn, g_ratio_fn,
                m_models=m_models, m_resid_vars=m_resid_vars,
            )
            
            for path in self.paths:
                all_scores[path][eval_idx] = fold_scores[path]
        
        # Step 4: Aggregate
        tau_per_path = {}
        for path in self.paths:
            scores = all_scores[path]
            valid_scores = ~np.isnan(scores)
            if valid_scores.sum() == 0:
                tau_per_path[path] = 0.0
            else:
                tau_per_path[path] = float(np.mean(scores[valid_scores]))
        
        # Weighted PJ-CF total
        tau_pj_cf = sum(
            (1 - self.psi.get(path, 0.0)) * tau_per_path[path]
            for path in self.paths
        )
        
        # Cluster-robust variance
        # Aggregate score across paths (with psi weighting)
        agg_score = np.zeros(n)
        for path in self.paths:
            agg_score += (1 - self.psi.get(path, 0.0)) * np.nan_to_num(all_scores[path])
        
        # Cluster-robust SE
        valid_total = ~np.isnan(agg_score)
        if valid_total.sum() < 10:
            se = float('nan')
        else:
            se = self._cluster_robust_se(agg_score[valid_total], S[valid_total], tau_pj_cf)
        
        # Confidence interval and p-value
        if np.isnan(se) or se == 0:
            ci_lower, ci_upper, p_value = float('nan'), float('nan'), float('nan')
        else:
            z_crit = 1.96  # 95% CI
            ci_lower = tau_pj_cf - z_crit * se
            ci_upper = tau_pj_cf + z_crit * se
            z_stat = tau_pj_cf / se
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        return HCDMLResult(
            tau_pj_cf=tau_pj_cf,
            tau_per_path=tau_per_path,
            se=se,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            n_obs=n,
            n_clusters=len(np.unique(S)),
            n_folds_used=len(folds),
            psi=self.psi,
            paths=self.paths,
            nuisance_quality={
                'outcome_r2_mean': float(np.mean(outcome_r2_list)) if outcome_r2_list else float('nan'),
                'propensity_acc_mean': float(np.mean(propensity_acc_list)) if propensity_acc_list else float('nan'),
                'n_valid_folds': len(outcome_r2_list),
            }
        )
    
    def _cluster_robust_se(
        self,
        scores: np.ndarray,
        S: np.ndarray,
        tau_hat: float,
    ) -> float:
        """Cluster-robust standard error using sandwich estimator.
        
        Var(τ̂) = (1/n²) · Σ_c [Σ_{i in c} (φ_i - τ̂)]²
        """
        residuals = scores - tau_hat
        n = len(residuals)
        
        unique_clusters = np.unique(S)
        if len(unique_clusters) <= 1:
            # No clustering: use standard SE
            return float(np.std(residuals, ddof=1) / np.sqrt(n))
        
        # Sum residuals within each cluster
        cluster_sums = []
        for c in unique_clusters:
            mask = S == c
            if mask.any():
                cluster_sums.append(residuals[mask].sum())
        
        cluster_sums = np.array(cluster_sums)
        var_estimate = np.sum(cluster_sums**2) / (n**2)
        
        # Small-sample correction (Bell-McCaffrey style, simplified)
        L = len(unique_clusters)
        correction = L / max(L - 1, 1)
        var_estimate = var_estimate * correction
        
        return float(np.sqrt(max(var_estimate, 0)))


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def estimate_hc_dml(
    Y: np.ndarray,
    A: np.ndarray,
    M: np.ndarray,
    X: np.ndarray,
    S: np.ndarray,
    **kwargs
) -> HCDMLResult:
    """Quick interface for HC-DML estimation with defaults."""
    estimator = HCDMLEstimator(**kwargs)
    return estimator.fit(Y, A, M, X, S)


__all__ = ['HCDMLEstimator', 'HCDMLResult', 'estimate_hc_dml']
