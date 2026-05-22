"""
Synthetic Data Generation for HC-DML Validation
================================================

This module provides 6 DGP variants for validating the HC-DML estimator.
Each variant isolates a specific challenge to test the algorithm.

Variants (increasing complexity):
    1. LinearDGP            - All linear, IID, no missing. Sanity check.
    2. HierarchicalDGP      - Adds cluster structure (school/cohort).
    3. NonlinearDGP         - Adds nonlinear outcome / mediator functions.
    4. ConfoundedDGP        - Adds unobserved confounder U.
    5. MissingPADGP         - Protected attribute missing under MAR.
    6. FullComplexDGP       - All challenges combined; closest to OULAD.

Design principles:
    - Reproducibility: all DGPs accept and use a `seed` parameter.
    - Standardization: outputs are standardized to avoid varsortability
      artifacts (Reisach et al. 2021).
    - Documented assumptions: each DGP class lists assumptions in docstring.
    - Analytical ground truth where possible; Monte Carlo otherwise.

References:
    Reisach, Seiler, Weichwald (2021). "Beware of the simulated DAG!"
        Causal discovery benchmarks may be easy to game. NeurIPS.
    Plecko & Bareinboim (2024). "Causal Fairness Analysis." 
        Foundations and Trends in Machine Learning.
    Chiappa (2019). "Path-Specific Counterfactual Fairness." AAAI.

Author: [Your name]
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Callable

import numpy as np
import pandas as pd
from scipy import stats


# =========================================================================
# DATA STRUCTURES
# =========================================================================

@dataclass
class SyntheticData:
    """Container for generated synthetic data with metadata.
    
    Attributes
    ----------
    Y : np.ndarray, shape (n,)
        Outcome variable (continuous or binary).
    A : np.ndarray, shape (n,)
        Protected attribute (binary {0, 1}). May contain NaN if missing.
    M : np.ndarray, shape (n, p)
        Mediator variables.
    X : np.ndarray, shape (n, q)
        Covariates (pre-treatment, non-mediator).
    Z : np.ndarray, shape (n, r), optional
        Surrogate variables for missing A imputation.
    R : np.ndarray, shape (n,), optional
        Missingness indicator: 1 if A_i observed, 0 otherwise.
    S : np.ndarray, shape (n,)
        Cluster (school/cohort) membership indicator.
    U : np.ndarray, shape (n,), optional
        Unobserved confounder (for ground-truth-only inspection;
        NOT to be used by estimator).
    metadata : dict
        DGP parameters and ground truth values.
    """
    Y: np.ndarray
    A: np.ndarray
    M: np.ndarray
    X: np.ndarray
    S: np.ndarray
    Z: Optional[np.ndarray] = None
    R: Optional[np.ndarray] = None
    U: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)
    
    @property
    def n(self) -> int:
        return len(self.Y)
    
    @property
    def n_clusters(self) -> int:
        return len(np.unique(self.S))
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame for convenience."""
        df = pd.DataFrame({
            'Y': self.Y,
            'A': self.A,
            'S': self.S,
        })
        for j in range(self.M.shape[1]):
            df[f'M{j+1}'] = self.M[:, j]
        for j in range(self.X.shape[1]):
            df[f'X{j+1}'] = self.X[:, j]
        if self.Z is not None:
            for j in range(self.Z.shape[1]):
                df[f'Z{j+1}'] = self.Z[:, j]
        if self.R is not None:
            df['R'] = self.R
        return df


# =========================================================================
# ABSTRACT BASE CLASS
# =========================================================================

class BaseDGP(ABC):
    """Abstract base class for all synthetic DGPs.
    
    Each DGP must implement:
        - generate(n, seed): produce SyntheticData
        - true_pj_cf(psi): compute ground truth PJ-CF estimand
    
    Standardization is applied automatically to prevent varsortability.
    """
    
    def __init__(self, name: str = "BaseDGP"):
        self.name = name
        self._cached_truth: Dict = {}
    
    @abstractmethod
    def generate(self, n: int, seed: int = 42) -> SyntheticData:
        """Generate synthetic data of size n.
        
        Parameters
        ----------
        n : int
            Number of individuals (total across clusters).
        seed : int
            Random seed for reproducibility.
        
        Returns
        -------
        SyntheticData
            Generated dataset with metadata including ground truth.
        """
        pass
    
    @abstractmethod
    def true_pj_cf(
        self,
        psi: Dict[str, float],
        n_mc: int = 100_000,
        seed: int = 12345
    ) -> Dict[str, float]:
        """Compute ground truth PJ-CF estimand.
        
        Parameters
        ----------
        psi : dict
            Path justifiability values, e.g., {'direct': 0.0, 'M->Y': 1.0}.
            Keys must match path names defined in the DGP.
        n_mc : int
            Sample size for Monte Carlo estimation (if analytical unavailable).
        seed : int
            Seed for Monte Carlo.
        
        Returns
        -------
        dict
            {'total': τ_PJ-CF, 'direct': τ_direct, 'indirect': τ_indirect, ...}
        """
        pass
    
    def _standardize_features(
        self,
        X: np.ndarray,
        scale: bool = True
    ) -> np.ndarray:
        """Standardize features to unit variance.
        
        Reisach et al. 2021 showed that ANM-generated data often has
        varsortability artifacts (causal order = variance order).
        Standardization mitigates this in raw form, though residual
        patterns may remain.
        """
        if not scale:
            return X
        sd = X.std(axis=0, keepdims=True)
        sd[sd < 1e-8] = 1.0  # Avoid division by zero
        return (X - X.mean(axis=0, keepdims=True)) / sd


# =========================================================================
# VARIANT 1: LinearDGP — Simplest, analytical ground truth
# =========================================================================

class LinearDGP(BaseDGP):
    """Linear, IID DGP with binary protected attribute and continuous outcome.
    
    Causal structure (path notation):
        X → A (covariate confounding)
        X → M, X → Y (covariate effects)
        A → M (mediator path origin)
        A → Y (DIRECT effect — typically unjustified)
        M → Y (mediated effect — justifiability varies)
    
    Generative model:
        X ~ N(0, I_q)
        A | X ~ Bernoulli(σ(γ_X^T X))
        M | X, A = β_X^T X + β_A · A + ε_M,    ε_M ~ N(0, σ²_M I_p)
        Y | X, A, M = α_X^T X + α_A · A + α_M^T M + ε_Y,  ε_Y ~ N(0, σ²_Y)
    
    Paths from A to Y:
        - 'direct':  A → Y     (effect = α_A)
        - 'via_M':   A → M → Y (effect = β_A · α_M^T 1)
    
    Ground truth (analytical):
        PSE_direct = α_A
        PSE_via_M  = β_A · sum(α_M)
        PJ-CF(ψ)   = (1-ψ['direct']) · α_A + (1-ψ['via_M']) · β_A · sum(α_M)
    """
    
    def __init__(
        self,
        q: int = 5,                    # Covariate dim
        p: int = 3,                    # Mediator dim
        alpha_A: float = 0.30,         # Direct effect of A on Y (UNFAIR)
        alpha_M: Optional[np.ndarray] = None,  # M -> Y coefficients
        alpha_X: Optional[np.ndarray] = None,  # X -> Y coefficients
        beta_A: float = 0.20,          # A -> M effect (mediated path)
        beta_X: Optional[np.ndarray] = None,   # X -> M coefficients
        gamma_X: Optional[np.ndarray] = None,  # X -> A coefficients (logit)
        sigma_M: float = 1.0,
        sigma_Y: float = 1.0,
        standardize: bool = True,
        name: str = "LinearDGP"
    ):
        super().__init__(name=name)
        self.q = q
        self.p = p
        self.alpha_A = alpha_A
        self.alpha_M = alpha_M if alpha_M is not None else np.ones(p) * 0.5
        self.alpha_X = alpha_X if alpha_X is not None else np.ones(q) * 0.3
        self.beta_A = beta_A
        self.beta_X = beta_X if beta_X is not None else np.ones((q, p)) * 0.2
        self.gamma_X = gamma_X if gamma_X is not None else np.ones(q) * 0.3
        self.sigma_M = sigma_M
        self.sigma_Y = sigma_Y
        self.standardize = standardize
        
        # Validate dimensions
        assert self.alpha_M.shape == (p,), f"alpha_M shape {self.alpha_M.shape} != ({p},)"
        assert self.alpha_X.shape == (q,), f"alpha_X shape {self.alpha_X.shape} != ({q},)"
        assert self.beta_X.shape == (q, p), f"beta_X shape {self.beta_X.shape} != ({q}, {p})"
        assert self.gamma_X.shape == (q,), f"gamma_X shape {self.gamma_X.shape} != ({q},)"
    
    def generate(self, n: int, seed: int = 42) -> SyntheticData:
        rng = np.random.default_rng(seed)
        
        # Step 1: Covariates
        X = rng.standard_normal(size=(n, self.q))
        if self.standardize:
            X = self._standardize_features(X)
        
        # Step 2: Protected attribute (depends on X)
        logit_A = X @ self.gamma_X
        p_A = 1.0 / (1.0 + np.exp(-logit_A))
        A = rng.binomial(1, p_A).astype(float)
        
        # Step 3: Mediators (depend on X and A)
        M_mean = X @ self.beta_X + np.outer(A, np.ones(self.p) * self.beta_A)
        M = M_mean + rng.standard_normal(size=(n, self.p)) * self.sigma_M
        
        # Step 4: Outcome (depends on X, A, M)
        Y_mean = X @ self.alpha_X + A * self.alpha_A + M @ self.alpha_M
        Y = Y_mean + rng.standard_normal(size=n) * self.sigma_Y
        
        # No clusters in this DGP — single cluster
        S = np.zeros(n, dtype=int)
        
        # No missing A
        R = np.ones(n, dtype=int)
        
        # Compute and cache ground truth
        truth = self._analytical_truth()
        
        metadata = {
            'dgp_name': self.name,
            'n': n,
            'seed': seed,
            'true_PSE_direct': truth['PSE_direct'],
            'true_PSE_via_M': truth['PSE_via_M'],
            'parameters': {
                'q': self.q, 'p': self.p,
                'alpha_A': self.alpha_A,
                'beta_A': self.beta_A,
                'sigma_M': self.sigma_M,
                'sigma_Y': self.sigma_Y,
            }
        }
        
        return SyntheticData(
            Y=Y, A=A, M=M, X=X, S=S, R=R,
            metadata=metadata
        )
    
    def _analytical_truth(self) -> Dict[str, float]:
        """Compute path-specific effects analytically."""
        return {
            'PSE_direct': self.alpha_A,
            'PSE_via_M': self.beta_A * np.sum(self.alpha_M),
        }
    
    def true_pj_cf(
        self,
        psi: Dict[str, float],
        n_mc: int = 100_000,
        seed: int = 12345
    ) -> Dict[str, float]:
        """Analytical PJ-CF computation (no Monte Carlo needed)."""
        truth = self._analytical_truth()
        
        pse_direct = truth['PSE_direct']
        pse_via_M = truth['PSE_via_M']
        
        # Default psi: both paths unjustified
        psi_direct = psi.get('direct', 0.0)
        psi_via_M = psi.get('via_M', 0.0)
        
        # PJ-CF = sum over unjustified paths of (1 - psi) * PSE
        pj_cf = (1 - psi_direct) * pse_direct + (1 - psi_via_M) * pse_via_M
        
        return {
            'total': pj_cf,
            'direct': (1 - psi_direct) * pse_direct,
            'via_M': (1 - psi_via_M) * pse_via_M,
            'PSE_direct': pse_direct,    # Raw effect (no psi weighting)
            'PSE_via_M': pse_via_M,
        }


# =========================================================================
# VARIANT 2: HierarchicalDGP — Adds cluster structure
# =========================================================================

class HierarchicalDGP(LinearDGP):
    """Linear DGP with cluster (school/cohort) structure.
    
    Extends LinearDGP by adding cluster-level random effects:
        - λ_s ~ N(0, σ²_λ)  (cluster random intercepts for A, M, Y)
        - μ_s ~ N(0, σ²_μ)  (cluster-level X means)
    
    This tests HC-DML's ability to handle multilevel data correctly.
    
    Parameters
    ----------
    n_clusters : int
        Number of clusters (e.g., schools).
    icc : float
        Intra-class correlation coefficient for Y (0 = no clustering, 1 = all variance).
    cluster_size_range : (int, int)
        Min and max cluster sizes (sampled uniformly).
    """
    
    def __init__(
        self,
        n_clusters: int = 50,
        icc: float = 0.10,
        cluster_size_range: Tuple[int, int] = (30, 200),
        name: str = "HierarchicalDGP",
        **kwargs
    ):
        super().__init__(name=name, **kwargs)
        self.n_clusters = n_clusters
        self.icc = icc
        self.cluster_size_range = cluster_size_range
        
        # Compute cluster effect variance from ICC
        # ICC = σ²_λ / (σ²_λ + σ²_Y)  =>  σ²_λ = ICC * σ²_Y / (1 - ICC)
        self.sigma_lambda = np.sqrt(
            self.icc * self.sigma_Y**2 / (1 - self.icc)
        )
    
    def generate(self, n: Optional[int] = None, seed: int = 42) -> SyntheticData:
        """Generate hierarchical data.
        
        If n is None, total sample size = sum of randomly sampled cluster sizes.
        If n is provided, cluster sizes are adjusted to match approximately.
        """
        rng = np.random.default_rng(seed)
        
        # Step 1: Sample cluster sizes
        if n is None:
            cluster_sizes = rng.integers(
                low=self.cluster_size_range[0],
                high=self.cluster_size_range[1] + 1,
                size=self.n_clusters
            )
        else:
            # Distribute n approximately uniformly
            avg = n // self.n_clusters
            cluster_sizes = np.full(self.n_clusters, avg)
            remainder = n - cluster_sizes.sum()
            cluster_sizes[:remainder] += 1
        
        # Step 2: Sample cluster-level random effects
        lambda_A = rng.normal(0, self.sigma_lambda * 0.5, size=self.n_clusters)
        lambda_M = rng.normal(0, self.sigma_lambda * 0.5, size=self.n_clusters)
        lambda_Y = rng.normal(0, self.sigma_lambda, size=self.n_clusters)
        
        # Cluster-level X means (capture between-cluster variation)
        mu_X = rng.normal(0, 0.3, size=(self.n_clusters, self.q))
        
        # Step 3: Generate data per cluster, then concatenate
        all_X, all_A, all_M, all_Y, all_S = [], [], [], [], []
        
        for s in range(self.n_clusters):
            n_s = cluster_sizes[s]
            
            # X: cluster-mean shift + individual variation
            X_s = mu_X[s] + rng.standard_normal(size=(n_s, self.q))
            
            # A: cluster effect on logit
            logit_A_s = X_s @ self.gamma_X + lambda_A[s]
            p_A_s = 1.0 / (1.0 + np.exp(-logit_A_s))
            # Ensure overlap in each cluster (positivity)
            p_A_s = np.clip(p_A_s, 0.05, 0.95)
            A_s = rng.binomial(1, p_A_s).astype(float)
            
            # M: cluster effect
            M_mean_s = X_s @ self.beta_X + np.outer(A_s, np.ones(self.p) * self.beta_A)
            M_mean_s = M_mean_s + lambda_M[s]  # Broadcast cluster effect
            M_s = M_mean_s + rng.standard_normal(size=(n_s, self.p)) * self.sigma_M
            
            # Y: cluster effect
            Y_mean_s = (
                X_s @ self.alpha_X
                + A_s * self.alpha_A
                + M_s @ self.alpha_M
                + lambda_Y[s]
            )
            Y_s = Y_mean_s + rng.standard_normal(size=n_s) * self.sigma_Y
            
            all_X.append(X_s)
            all_A.append(A_s)
            all_M.append(M_s)
            all_Y.append(Y_s)
            all_S.append(np.full(n_s, s, dtype=int))
        
        X = np.vstack(all_X)
        A = np.concatenate(all_A)
        M = np.vstack(all_M)
        Y = np.concatenate(all_Y)
        S = np.concatenate(all_S)
        n_total = len(Y)
        
        if self.standardize:
            X = self._standardize_features(X)
            # NOTE: Do NOT standardize M or Y — preserves causal interpretation
        
        R = np.ones(n_total, dtype=int)
        
        truth = self._analytical_truth()
        metadata = {
            'dgp_name': self.name,
            'n': n_total,
            'n_clusters': self.n_clusters,
            'cluster_sizes': cluster_sizes.tolist(),
            'icc': self.icc,
            'seed': seed,
            'true_PSE_direct': truth['PSE_direct'],
            'true_PSE_via_M': truth['PSE_via_M'],
            'true_lambda_A_var': self.sigma_lambda**2 * 0.25,
            'true_lambda_Y_var': self.sigma_lambda**2,
        }
        
        return SyntheticData(
            Y=Y, A=A, M=M, X=X, S=S, R=R,
            metadata=metadata
        )
    
    def true_pj_cf(
        self,
        psi: Dict[str, float],
        n_mc: int = 100_000,
        seed: int = 12345
    ) -> Dict[str, float]:
        """PJ-CF unchanged by cluster random intercepts.
        
        Because cluster effects are additive and independent of A,
        they don't change the marginal path-specific effects.
        Analytical truth is same as LinearDGP.
        """
        return super().true_pj_cf(psi, n_mc, seed)


# =========================================================================
# VARIANT 3: NonlinearDGP — Nonlinear outcome / mediator
# =========================================================================

class NonlinearDGP(HierarchicalDGP):
    """Hierarchical DGP with nonlinear outcome and mediator functions.
    
    Tests HC-DML's ability to handle nonparametric nuisance functions.
    
    Nonlinearity:
        - Outcome: Y = ... + Σ_j f_j(X_j) + g(M)
          where f_j and g are nonlinear (sin, exp, polynomial).
        - Path-specific effects must be computed via Monte Carlo.
    """
    
    def __init__(
        self,
        nonlinearity: str = "moderate",  # "mild" | "moderate" | "strong"
        name: str = "NonlinearDGP",
        **kwargs
    ):
        super().__init__(name=name, **kwargs)
        self.nonlinearity = nonlinearity
        
        # Nonlinearity strength
        nl_map = {"mild": 0.1, "moderate": 0.3, "strong": 0.6}
        self.nl_strength = nl_map.get(nonlinearity, 0.3)
    
    def _f_nonlin(self, X: np.ndarray) -> np.ndarray:
        """Nonlinear transformation of X for outcome model."""
        # Combination of sin and quadratic
        return self.nl_strength * (
            np.sin(X[:, 0]) + 0.5 * X[:, 0]**2
            + (np.exp(np.clip(X[:, 1], -2, 2)) - 1) * 0.3
        )
    
    def _g_nonlin(self, M: np.ndarray) -> np.ndarray:
        """Nonlinear transformation of M for outcome model."""
        return self.nl_strength * (
            np.tanh(M[:, 0]) + 0.3 * M[:, 0] * M[:, 1] if M.shape[1] > 1
            else np.tanh(M[:, 0])
        )
    
    def generate(self, n: Optional[int] = None, seed: int = 42) -> SyntheticData:
        # Use parent to generate baseline linear structure
        data = super().generate(n, seed)
        
        # Add nonlinearity to outcome
        f_X = self._f_nonlin(data.X)
        g_M = self._g_nonlin(data.M)
        data.Y = data.Y + f_X + g_M
        
        data.metadata['nonlinearity'] = self.nonlinearity
        data.metadata['nl_strength'] = self.nl_strength
        
        # NOTE: Path-specific effects approximately unchanged because
        # f(X) doesn't depend on A, and g(M) added uniformly.
        # But coefficient interpretation changes — must verify with MC.
        data.metadata['note'] = (
            "Nonlinearity in X and M components added. "
            "True PJ-CF computed via Monte Carlo."
        )
        
        return data
    
    def true_pj_cf(
        self,
        psi: Dict[str, float],
        n_mc: int = 500_000,
        seed: int = 12345
    ) -> Dict[str, float]:
        """Monte Carlo estimation of PJ-CF.
        
        Strategy:
            1. Sample large MC dataset
            2. For each path π:
                - Compute E[Y | do(A=1, M(a=1))] - E[Y | do(A=0, M(a=0))]
                  using nested potential outcomes
            3. Aggregate via psi weighting
        """
        rng = np.random.default_rng(seed)
        
        # Generate large MC sample for ground truth
        # Use direct sampling without clustering for simplicity
        # (cluster effects average out in expectation)
        X = rng.standard_normal(size=(n_mc, self.q))
        if self.standardize:
            X = self._standardize_features(X)
        
        # Compute path-specific effects
        # PSE_direct: E[Y(a=1, M(a=0))] - E[Y(a=0, M(a=0))]
        # PSE_via_M:  E[Y(a=0, M(a=1))] - E[Y(a=0, M(a=0))]
        
        # Generate M under a=0 and a=1 counterfactually
        M_a0 = X @ self.beta_X + 0  # A=0
        M_a0 = M_a0 + rng.standard_normal(size=(n_mc, self.p)) * self.sigma_M
        
        M_a1 = X @ self.beta_X + np.ones(self.p) * self.beta_A  # A=1
        M_a1 = M_a1 + rng.standard_normal(size=(n_mc, self.p)) * self.sigma_M
        
        # Counterfactual outcomes
        f_X = self._f_nonlin(X)
        
        # Y(a=0, M(a=0)): both at a=0
        Y_a0_M0 = (
            X @ self.alpha_X + 0 * self.alpha_A + M_a0 @ self.alpha_M
            + f_X + self._g_nonlin(M_a0)
        )
        
        # Y(a=1, M(a=0)): direct path only
        Y_a1_M0 = (
            X @ self.alpha_X + 1 * self.alpha_A + M_a0 @ self.alpha_M
            + f_X + self._g_nonlin(M_a0)
        )
        
        # Y(a=0, M(a=1)): mediator path only
        Y_a0_M1 = (
            X @ self.alpha_X + 0 * self.alpha_A + M_a1 @ self.alpha_M
            + f_X + self._g_nonlin(M_a1)
        )
        
        pse_direct = np.mean(Y_a1_M0 - Y_a0_M0)
        pse_via_M = np.mean(Y_a0_M1 - Y_a0_M0)
        
        psi_direct = psi.get('direct', 0.0)
        psi_via_M = psi.get('via_M', 0.0)
        
        pj_cf = (1 - psi_direct) * pse_direct + (1 - psi_via_M) * pse_via_M
        
        # MC standard errors for transparency
        se_direct = np.std(Y_a1_M0 - Y_a0_M0) / np.sqrt(n_mc)
        se_via_M = np.std(Y_a0_M1 - Y_a0_M0) / np.sqrt(n_mc)
        
        return {
            'total': pj_cf,
            'direct': (1 - psi_direct) * pse_direct,
            'via_M': (1 - psi_via_M) * pse_via_M,
            'PSE_direct': pse_direct,
            'PSE_via_M': pse_via_M,
            'PSE_direct_se_mc': se_direct,
            'PSE_via_M_se_mc': se_via_M,
            'n_mc': n_mc,
        }


# =========================================================================
# VARIANT 4: ConfoundedDGP — Unobserved confounder U
# =========================================================================

class ConfoundedDGP(HierarchicalDGP):
    """Hierarchical DGP with unobserved confounder U affecting (A, Y).
    
    Tests HC-DML's sensitivity analysis bounds.
    Estimator should NOT use U; ground truth uses U internally.
    
    Causal structure adds:
        U ~ N(0, 1)  (unobserved, e.g., motivation, family support)
        U → A  (with strength gamma_U)
        U → Y  (with strength alpha_U)
    
    Without adjusting for U, naive estimator will be BIASED.
    Sensitivity analysis should bracket the true effect.
    """
    
    def __init__(
        self,
        alpha_U: float = 0.3,    # U -> Y strength (educational confounder)
        gamma_U: float = 0.4,    # U -> A strength
        name: str = "ConfoundedDGP",
        **kwargs
    ):
        super().__init__(name=name, **kwargs)
        self.alpha_U = alpha_U
        self.gamma_U = gamma_U
    
    def generate(self, n: Optional[int] = None, seed: int = 42) -> SyntheticData:
        rng = np.random.default_rng(seed)
        
        # First generate baseline data (note: parent uses different rng state)
        # We re-implement to inject U at correct point
        if n is None:
            cluster_sizes = rng.integers(
                low=self.cluster_size_range[0],
                high=self.cluster_size_range[1] + 1,
                size=self.n_clusters
            )
        else:
            avg = n // self.n_clusters
            cluster_sizes = np.full(self.n_clusters, avg)
            remainder = n - cluster_sizes.sum()
            cluster_sizes[:remainder] += 1
        
        # Cluster effects
        lambda_A = rng.normal(0, self.sigma_lambda * 0.5, size=self.n_clusters)
        lambda_M = rng.normal(0, self.sigma_lambda * 0.5, size=self.n_clusters)
        lambda_Y = rng.normal(0, self.sigma_lambda, size=self.n_clusters)
        mu_X = rng.normal(0, 0.3, size=(self.n_clusters, self.q))
        
        all_X, all_A, all_M, all_Y, all_S, all_U = [], [], [], [], [], []
        
        for s in range(self.n_clusters):
            n_s = cluster_sizes[s]
            
            # Unobserved confounder
            U_s = rng.standard_normal(size=n_s)
            
            # X
            X_s = mu_X[s] + rng.standard_normal(size=(n_s, self.q))
            
            # A: depends on X, U, cluster
            logit_A_s = X_s @ self.gamma_X + self.gamma_U * U_s + lambda_A[s]
            p_A_s = 1.0 / (1.0 + np.exp(-logit_A_s))
            p_A_s = np.clip(p_A_s, 0.05, 0.95)
            A_s = rng.binomial(1, p_A_s).astype(float)
            
            # M: depends on X, A, cluster (NOT U, in this DGP)
            M_mean_s = X_s @ self.beta_X + np.outer(A_s, np.ones(self.p) * self.beta_A)
            M_mean_s = M_mean_s + lambda_M[s]
            M_s = M_mean_s + rng.standard_normal(size=(n_s, self.p)) * self.sigma_M
            
            # Y: depends on X, A, M, U, cluster
            Y_mean_s = (
                X_s @ self.alpha_X
                + A_s * self.alpha_A
                + M_s @ self.alpha_M
                + self.alpha_U * U_s
                + lambda_Y[s]
            )
            Y_s = Y_mean_s + rng.standard_normal(size=n_s) * self.sigma_Y
            
            all_X.append(X_s)
            all_A.append(A_s)
            all_M.append(M_s)
            all_Y.append(Y_s)
            all_S.append(np.full(n_s, s, dtype=int))
            all_U.append(U_s)
        
        X = np.vstack(all_X)
        A = np.concatenate(all_A)
        M = np.vstack(all_M)
        Y = np.concatenate(all_Y)
        S = np.concatenate(all_S)
        U = np.concatenate(all_U)
        n_total = len(Y)
        
        if self.standardize:
            X = self._standardize_features(X)
        
        R = np.ones(n_total, dtype=int)
        
        # Compute strength of confounding for sensitivity calibration
        # Sensitivity parameter Γ ≈ exp(|gamma_U| * |alpha_U|)
        gamma_sensitivity = np.exp(np.abs(self.gamma_U * self.alpha_U))
        
        metadata = {
            'dgp_name': self.name,
            'n': n_total,
            'n_clusters': self.n_clusters,
            'seed': seed,
            'alpha_U': self.alpha_U,
            'gamma_U': self.gamma_U,
            'implied_gamma_sensitivity': gamma_sensitivity,
            'note': (
                f"Unobserved confounder U with alpha_U={self.alpha_U}, "
                f"gamma_U={self.gamma_U}. Implied sensitivity Γ ≈ "
                f"{gamma_sensitivity:.3f}."
            )
        }
        
        # Include U for ground-truth inspection only
        return SyntheticData(
            Y=Y, A=A, M=M, X=X, S=S, R=R, U=U,
            metadata=metadata
        )
    
    def true_pj_cf(
        self,
        psi: Dict[str, float],
        n_mc: int = 500_000,
        seed: int = 12345
    ) -> Dict[str, float]:
        """Monte Carlo PJ-CF accounting for U.
        
        True path-specific effects are still the structural coefficients,
        but naive estimation (without U) will be biased.
        
        Bias on PSE_direct ≈ alpha_U * gamma_U * Var(U) / Var(A | X)
        """
        # PJ-CF based on TRUE structural coefficients (would need oracle adj.)
        # Truth same as LinearDGP since paths A→M→Y and A→Y unchanged
        return super().true_pj_cf(psi, n_mc, seed)


# =========================================================================
# VARIANT 5: MissingPADGP — Missing protected attribute under MAR
# =========================================================================

class MissingPADGP(HierarchicalDGP):
    """Hierarchical DGP with protected attribute A missing under MAR.
    
    Missingness mechanism:
        R | X, Z, A, S ~ Bernoulli(σ(δ_X^T X + δ_Z^T Z + δ_S λ_R[S]))
        
        Notably, R does NOT directly depend on A (MAR assumption).
        Surrogate Z is correlated with A and helps imputation.
    
    Tests HC-DML's surrogate-based score for missing A.
    """
    
    def __init__(
        self,
        missing_rate: float = 0.3,
        surrogate_strength: float = 0.6,  # Correlation of Z with A
        n_surrogates: int = 2,
        name: str = "MissingPADGP",
        **kwargs
    ):
        super().__init__(name=name, **kwargs)
        self.missing_rate = missing_rate
        self.surrogate_strength = surrogate_strength
        self.n_surrogates = n_surrogates
    
    def generate(self, n: Optional[int] = None, seed: int = 42) -> SyntheticData:
        # Generate baseline complete data
        data = super().generate(n, seed)
        
        rng = np.random.default_rng(seed + 1000)  # Different stream for missing
        n_total = data.n
        
        # Generate surrogates Z correlated with A (but not directly causal)
        # Z_j | A ~ N(surrogate_strength * (A - 0.5) * 2, 1)
        Z = np.zeros((n_total, self.n_surrogates))
        for j in range(self.n_surrogates):
            # Different strength per surrogate
            strength_j = self.surrogate_strength * (1 - 0.1 * j)
            Z[:, j] = (
                strength_j * (data.A - 0.5) * 2
                + rng.standard_normal(size=n_total) * np.sqrt(1 - strength_j**2)
            )
        
        # Missingness mechanism (MAR: depends on X and Z, not A directly)
        delta_X = np.ones(self.q) * 0.1
        delta_Z = np.ones(self.n_surrogates) * 0.2
        
        # Calibrate intercept to achieve target missing rate
        logit_R = data.X @ delta_X + Z @ delta_Z
        # Solve for intercept: P(R=0) = missing_rate
        # σ(logit + c) where c set so mean ≈ 1 - missing_rate
        target_R = 1 - self.missing_rate
        c_intercept = np.log(target_R / (1 - target_R)) - logit_R.mean()
        logit_R = logit_R + c_intercept
        
        p_R = 1.0 / (1.0 + np.exp(-logit_R))
        R = rng.binomial(1, p_R).astype(int)
        
        # Apply missingness: set A to NaN where R=0
        A_missing = data.A.copy()
        A_missing[R == 0] = np.nan
        
        # Update data
        data.A = A_missing
        data.Z = Z
        data.R = R
        
        data.metadata.update({
            'missing_rate_target': self.missing_rate,
            'missing_rate_actual': 1 - R.mean(),
            'surrogate_strength': self.surrogate_strength,
            'n_surrogates': self.n_surrogates,
            'note': (
                f"MAR missing in A with rate ~{1-R.mean():.2%}. "
                f"Surrogates Z provided with strength {self.surrogate_strength}."
            )
        })
        
        return data
    
    # true_pj_cf inherited — structural effects unchanged by missingness


# =========================================================================
# VARIANT 6: FullComplexDGP — All challenges combined
# =========================================================================

class FullComplexDGP(BaseDGP):
    """Full-complexity DGP combining all challenges.
    
    Includes:
        - Cluster structure (multilevel)
        - Nonlinearity in outcome
        - Unobserved confounder U
        - Missing protected attribute (MAR)
        - Multiple mediators with different path roles
    
    This is the closest synthetic analog to real educational data like OULAD.
    Use for final paper results, not initial development.
    """
    
    def __init__(
        self,
        n_clusters: int = 100,
        icc: float = 0.10,
        cluster_size_range: Tuple[int, int] = (50, 300),
        q: int = 8,
        p: int = 4,
        alpha_A: float = 0.25,
        beta_A: float = 0.20,
        alpha_U: float = 0.30,
        gamma_U: float = 0.35,
        missing_rate: float = 0.25,
        surrogate_strength: float = 0.55,
        nonlinearity: str = "moderate",
        name: str = "FullComplexDGP"
    ):
        super().__init__(name=name)
        
        # Use composition pattern: chain through HierarchicalDGP → Confounded → Missing
        # But add nonlinearity directly here for clarity
        
        self.n_clusters = n_clusters
        self.icc = icc
        self.cluster_size_range = cluster_size_range
        self.q = q
        self.p = p
        self.alpha_A = alpha_A
        self.beta_A = beta_A
        self.alpha_U = alpha_U
        self.gamma_U = gamma_U
        self.missing_rate = missing_rate
        self.surrogate_strength = surrogate_strength
        self.nonlinearity = nonlinearity
        
        # Pre-build component DGPs
        common_args = dict(
            q=q, p=p,
            alpha_A=alpha_A,
            alpha_M=np.linspace(0.3, 0.6, p),  # Heterogeneous mediator effects
            alpha_X=np.linspace(0.2, 0.4, q),
            beta_A=beta_A,
            beta_X=np.random.RandomState(42).normal(0, 0.2, size=(q, p)),
            gamma_X=np.linspace(0.2, 0.4, q),
            sigma_M=1.0,
            sigma_Y=1.0,
        )
        
        self._confounded = ConfoundedDGP(
            n_clusters=n_clusters,
            icc=icc,
            cluster_size_range=cluster_size_range,
            alpha_U=alpha_U,
            gamma_U=gamma_U,
            **common_args
        )
        
        # Nonlinearity setup
        nl_map = {"mild": 0.1, "moderate": 0.3, "strong": 0.6}
        self.nl_strength = nl_map.get(nonlinearity, 0.3)
    
    def _f_nonlin(self, X: np.ndarray) -> np.ndarray:
        return self.nl_strength * (
            np.sin(X[:, 0]) + 0.5 * X[:, 0]**2
            + (np.exp(np.clip(X[:, 1], -2, 2)) - 1) * 0.3
        )
    
    def _g_nonlin(self, M: np.ndarray) -> np.ndarray:
        return self.nl_strength * (
            np.tanh(M[:, 0]) + 0.3 * M[:, 0] * M[:, 1] if M.shape[1] > 1
            else np.tanh(M[:, 0])
        )
    
    def generate(self, n: Optional[int] = None, seed: int = 42) -> SyntheticData:
        # Step 1: Generate via confounded DGP (clusters + U)
        data = self._confounded.generate(n, seed)
        
        # Step 2: Add nonlinearity to Y
        f_X = self._f_nonlin(data.X)
        g_M = self._g_nonlin(data.M)
        data.Y = data.Y + f_X + g_M
        
        # Step 3: Add missing A under MAR
        rng = np.random.default_rng(seed + 2000)
        n_total = data.n
        
        # Generate surrogates
        n_surrogates = 2
        Z = np.zeros((n_total, n_surrogates))
        for j in range(n_surrogates):
            strength_j = self.surrogate_strength * (1 - 0.1 * j)
            Z[:, j] = (
                strength_j * (data.A - 0.5) * 2
                + rng.standard_normal(size=n_total) * np.sqrt(1 - strength_j**2)
            )
        
        # MAR mechanism
        delta_X = np.ones(self.q) * 0.1
        delta_Z = np.ones(n_surrogates) * 0.2
        logit_R = data.X @ delta_X + Z @ delta_Z
        target_R = 1 - self.missing_rate
        c_intercept = np.log(target_R / (1 - target_R)) - logit_R.mean()
        logit_R = logit_R + c_intercept
        p_R = 1.0 / (1.0 + np.exp(-logit_R))
        R = rng.binomial(1, p_R).astype(int)
        
        A_missing = data.A.copy()
        A_missing[R == 0] = np.nan
        data.A = A_missing
        data.Z = Z
        data.R = R
        
        data.metadata.update({
            'dgp_name': self.name,
            'nonlinearity': self.nonlinearity,
            'missing_rate_actual': 1 - R.mean(),
            'note': 'Full complexity: hierarchy + nonlin + unobs U + missing A',
        })
        
        return data
    
    def true_pj_cf(
        self,
        psi: Dict[str, float],
        n_mc: int = 500_000,
        seed: int = 12345
    ) -> Dict[str, float]:
        """Monte Carlo ground truth using the underlying structural model."""
        # Delegate to nonlinear computation but include all aspects
        rng = np.random.default_rng(seed)
        
        X = rng.standard_normal(size=(n_mc, self.q))
        sd = X.std(axis=0, keepdims=True)
        sd[sd < 1e-8] = 1.0
        X = (X - X.mean(axis=0, keepdims=True)) / sd
        
        # Counterfactual mediators
        M_a0 = X @ self._confounded.beta_X + rng.standard_normal(size=(n_mc, self.p)) * 1.0
        M_a1 = X @ self._confounded.beta_X + np.ones(self.p) * self.beta_A + \
               rng.standard_normal(size=(n_mc, self.p)) * 1.0
        
        f_X = self._f_nonlin(X)
        
        Y_a0_M0 = X @ self._confounded.alpha_X + 0 * self.alpha_A + M_a0 @ self._confounded.alpha_M + f_X + self._g_nonlin(M_a0)
        Y_a1_M0 = X @ self._confounded.alpha_X + 1 * self.alpha_A + M_a0 @ self._confounded.alpha_M + f_X + self._g_nonlin(M_a0)
        Y_a0_M1 = X @ self._confounded.alpha_X + 0 * self.alpha_A + M_a1 @ self._confounded.alpha_M + f_X + self._g_nonlin(M_a1)
        
        pse_direct = np.mean(Y_a1_M0 - Y_a0_M0)
        pse_via_M = np.mean(Y_a0_M1 - Y_a0_M0)
        
        psi_direct = psi.get('direct', 0.0)
        psi_via_M = psi.get('via_M', 0.0)
        
        pj_cf = (1 - psi_direct) * pse_direct + (1 - psi_via_M) * pse_via_M
        
        return {
            'total': pj_cf,
            'direct': (1 - psi_direct) * pse_direct,
            'via_M': (1 - psi_via_M) * pse_via_M,
            'PSE_direct': pse_direct,
            'PSE_via_M': pse_via_M,
            'n_mc': n_mc,
        }


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def get_dgp(name: str, **kwargs) -> BaseDGP:
    """Factory function for getting DGP by name.
    
    Examples
    --------
    >>> dgp = get_dgp("linear", q=5, p=3, alpha_A=0.3)
    >>> data = dgp.generate(n=1000, seed=42)
    >>> truth = dgp.true_pj_cf(psi={'direct': 0.0, 'via_M': 1.0})
    """
    name = name.lower()
    if name in ("linear", "v1"):
        return LinearDGP(**kwargs)
    elif name in ("hierarchical", "v2"):
        return HierarchicalDGP(**kwargs)
    elif name in ("nonlinear", "v3"):
        return NonlinearDGP(**kwargs)
    elif name in ("confounded", "v4"):
        return ConfoundedDGP(**kwargs)
    elif name in ("missing_pa", "v5"):
        return MissingPADGP(**kwargs)
    elif name in ("full_complex", "v6", "full"):
        return FullComplexDGP(**kwargs)
    else:
        raise ValueError(
            f"Unknown DGP name: {name}. "
            f"Choose from: linear, hierarchical, nonlinear, "
            f"confounded, missing_pa, full_complex"
        )


__all__ = [
    'SyntheticData',
    'BaseDGP',
    'LinearDGP',
    'HierarchicalDGP',
    'NonlinearDGP',
    'ConfoundedDGP',
    'MissingPADGP',
    'FullComplexDGP',
    'get_dgp',
]
