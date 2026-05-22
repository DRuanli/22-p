"""
Sensitivity Analysis for Path-Specific Counterfactual Fairness
================================================================

Implements sensitivity bounds under unobserved confounding for the 
HC-DML estimator. Addresses the critical assumption violation that 
hierarchical sequential ignorability rarely holds exactly in practice.

THREE SENSITIVITY LEVELS:

LEVEL A: Sensitivity to ψ (pedagogical justifiability)
    How does τ_PJ-CF change as ψ varies across [0,1]?
    Trace curves showing fairness verdict robustness.

LEVEL B: Sensitivity to unobserved confounding (Phase 5 main)
    Extends Marginal Sensitivity Model (Tan 2006, Zhao et al. 2019) 
    to path-specific effects in clustered data.
    
    Bounds:
        τ_lower(Γ) ≤ τ_true ≤ τ_upper(Γ)
    
    where Γ ≥ 1 quantifies max odds ratio violation of ignorability:
        Γ = 1: no unobserved confounding (point identification)
        Γ = 2: P(A=1|X,U) at most 2x or 1/2x of P(A=1|X)
        Γ → ∞: nonparametric bounds (uninformative)

LEVEL C: Sensitivity to DAG specification
    Re-run estimation across alternative DAGs.
    Report range of estimates as DAG uncertainty.

REFERENCES:
    - Tan (2006) "A distributional approach for causal inference using
      propensity scores"
    - Zhao, Small, & Bhattacharya (2019) "Sensitivity analysis for 
      inverse probability weighting estimators"
    - Schröder, Frauen, Feuerriegel (2024) "Causal fairness under 
      unobserved confounding: A neural sensitivity framework"
    - Tchetgen-Tchetgen & Shpitser (2014) Section 5 on sensitivity
      for natural direct/indirect effects

WARNINGS:
    1. Sensitivity bounds for PATH-SPECIFIC effects are more complex 
       than for total effects. Cross-world independence assumption 
       cannot be tested even with sensitivity analysis.
    2. Bounds presented here are POINT-WISE bounds, not uniform across
       all values. Joint inference requires multiple testing correction.
    3. Implementation uses Gaussian assumption on Y residuals — verify
       this empirically on your data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any
import warnings

import numpy as np
import pandas as pd
from scipy import stats, optimize


# =========================================================================
# RESULT CONTAINERS
# =========================================================================

@dataclass
class PsiSensitivityResult:
    """Level A: sensitivity to ψ parameter."""
    psi_grid: np.ndarray
    tau_estimates: np.ndarray
    ci_lower: np.ndarray
    ci_upper: np.ndarray
    
    # Critical thresholds
    psi_zero_crossing: Optional[float] = None  # ψ value where τ crosses 0
    sign_robust: bool = False                   # τ same sign across all ψ
    
    def summary(self) -> str:
        s = "ψ Sensitivity Analysis\n"
        s += "─" * 60 + "\n"
        s += f"  ψ grid: {self.psi_grid.tolist()}\n"
        s += f"  τ range: [{self.tau_estimates.min():+.4f}, {self.tau_estimates.max():+.4f}]\n"
        s += f"  Sign robust: {self.sign_robust}\n"
        if self.psi_zero_crossing is not None:
            s += f"  Zero crossing at ψ = {self.psi_zero_crossing:.3f}\n"
        return s


@dataclass
class ConfoundingSensitivityResult:
    """Level B: sensitivity to unobserved confounding."""
    gamma_grid: np.ndarray
    tau_lower: np.ndarray
    tau_upper: np.ndarray
    
    # Critical thresholds
    gamma_break_point: Optional[float] = None  # Γ at which CI includes 0
    qualitative_robust: bool = False           # Sign preserved for all reported Γ
    
    # Reference values
    tau_point: float = 0.0
    se_point: float = 0.0
    
    def summary(self) -> str:
        s = "Unobserved Confounding Sensitivity (Marginal Sensitivity Model)\n"
        s += "─" * 60 + "\n"
        s += f"  Point estimate: τ̂ = {self.tau_point:+.4f} (SE = {self.se_point:.4f})\n"
        s += "\n  Γ      τ_lower    τ_upper    Sign preserved?\n"
        for i, g in enumerate(self.gamma_grid):
            sign_pres = (np.sign(self.tau_lower[i]) == np.sign(self.tau_upper[i]) and 
                       self.tau_lower[i] != 0)
            s += f"  {g:.2f}  {self.tau_lower[i]:+.4f}    {self.tau_upper[i]:+.4f}    {'Yes' if sign_pres else 'No'}\n"
        if self.gamma_break_point is not None:
            s += f"\n  Break point: Γ ≈ {self.gamma_break_point:.2f}\n"
            s += f"  Interpretation: unobserved confounding must change\n"
            s += f"  odds ratio of A by factor {self.gamma_break_point:.2f}x to flip conclusion.\n"
        s += f"\n  Qualitatively robust: {self.qualitative_robust}\n"
        return s


@dataclass  
class DAGSensitivityResult:
    """Level C: sensitivity to DAG specification."""
    dag_names: List[str]
    tau_estimates: List[float]
    ci_lower: List[float]
    ci_upper: List[float]
    
    # Range diagnostics
    tau_min: float = 0.0
    tau_max: float = 0.0
    sign_consistent: bool = True
    
    def summary(self) -> str:
        s = "DAG Specification Sensitivity\n"
        s += "─" * 60 + "\n"
        for i, name in enumerate(self.dag_names):
            s += f"  {name:<30}  τ = {self.tau_estimates[i]:+.4f}  "
            s += f"CI = [{self.ci_lower[i]:+.4f}, {self.ci_upper[i]:+.4f}]\n"
        s += f"\n  Range: [{self.tau_min:+.4f}, {self.tau_max:+.4f}]\n"
        s += f"  Sign consistent: {self.sign_consistent}\n"
        return s


# =========================================================================
# LEVEL A: ψ SENSITIVITY
# =========================================================================

def psi_sensitivity_analysis(
    estimator,
    Y, A, M, X, S,
    psi_grid: Optional[np.ndarray] = None,
    path_to_vary: str = 'via_M',
    psi_fixed: Optional[Dict[str, float]] = None,
    verbose: bool = True,
) -> PsiSensitivityResult:
    """Trace τ_PJ-CF as ψ varies on grid.
    
    Parameters
    ----------
    estimator : HCDMLEstimator or HCDMLEstimatorEIF instance
    Y, A, M, X, S : arrays
    psi_grid : array of ψ values to evaluate. Default: [0, 0.25, 0.5, 0.75, 1.0]
    path_to_vary : str, which path's ψ to vary (default 'via_M')
    psi_fixed : dict, fixed ψ values for other paths (default: 0 for all)
    
    Returns
    -------
    PsiSensitivityResult
    """
    if psi_grid is None:
        psi_grid = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    
    if psi_fixed is None:
        psi_fixed = {p: 0.0 for p in estimator.paths}
    
    tau_estimates = np.zeros(len(psi_grid))
    ci_lower = np.zeros(len(psi_grid))
    ci_upper = np.zeros(len(psi_grid))
    
    if verbose:
        print(f"\n  ψ Sensitivity Analysis (varying {path_to_vary}):")
    
    for i, psi_val in enumerate(psi_grid):
        # Build psi dict for this iteration
        psi_now = dict(psi_fixed)
        psi_now[path_to_vary] = psi_val
        
        # Clone estimator with new psi
        params = estimator.get_params()
        params['psi'] = psi_now
        new_est = estimator.__class__(**params)
        
        try:
            r = new_est.fit(Y=Y, A=A, M=M, X=X, S=S)
            tau_estimates[i] = r.tau_pj_cf
            ci_lower[i] = r.ci_lower
            ci_upper[i] = r.ci_upper
            
            if verbose:
                print(f"    ψ_{path_to_vary} = {psi_val:.2f}: τ = {r.tau_pj_cf:+.4f}, "
                      f"CI = [{r.ci_lower:+.4f}, {r.ci_upper:+.4f}]")
        except Exception as e:
            warnings.warn(f"ψ={psi_val} failed: {e}")
            tau_estimates[i] = np.nan
            ci_lower[i] = np.nan
            ci_upper[i] = np.nan
    
    # Detect zero crossing
    psi_zero_crossing = None
    signs = np.sign(tau_estimates[~np.isnan(tau_estimates)])
    sign_robust = len(set(signs[signs != 0])) <= 1
    
    if not sign_robust:
        # Linear interpolate zero crossing
        for i in range(len(psi_grid) - 1):
            if (tau_estimates[i] * tau_estimates[i+1] < 0):
                # Found sign change between i and i+1
                t1, t2 = tau_estimates[i], tau_estimates[i+1]
                p1, p2 = psi_grid[i], psi_grid[i+1]
                psi_zero_crossing = p1 + (p2 - p1) * (-t1) / (t2 - t1)
                break
    
    return PsiSensitivityResult(
        psi_grid=psi_grid,
        tau_estimates=tau_estimates,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        psi_zero_crossing=psi_zero_crossing,
        sign_robust=sign_robust,
    )


# =========================================================================
# LEVEL B: UNOBSERVED CONFOUNDING SENSITIVITY (MARGINAL SENSITIVITY MODEL)
# =========================================================================

def _marginal_sensitivity_bounds_single(
    Y, A, M, X, S,
    mu_fn, e_fn, ratio_fn, mu_bar_fn,
    gamma: float,
    target: str = 'theta_10',
    n_mc: int = 30,
    rng=None,
) -> Tuple[float, float]:
    """Compute sharp bounds on θ under Γ-MSM.
    
    Under MSM with parameter Γ ≥ 1:
        1/Γ ≤ {P(A=1|X,U)/(1-P(A=1|X,U))} / {P(A=1|X)/(1-P(A=1|X))} ≤ Γ
    
    The true propensity weight is bounded between:
        w_L(X) = e(X) / (Γ + (1-Γ)·e(X))    [lower bound on adjusted weight]
        w_U(X) = Γ·e(X) / (1 + (Γ-1)·e(X))  [upper bound]
    
    For θ_10 = E[Y_{1, M_0}], bounds are obtained by:
        θ_lower = E[μ̄_1(X, 0, S)] - max effect of confounding
        θ_upper = E[μ̄_1(X, 0, S)] + max effect of confounding
    
    where max effect comes from worst-case re-weighting of Y residuals.
    
    Reference: Zhao, Small & Bhattacharya 2019 Theorem 1, adapted to PSE.
    
    Returns
    -------
    (lower, upper) : tuple of floats
    """
    if rng is None:
        rng = np.random.default_rng(42)
    
    n = len(Y)
    pi = np.clip(e_fn(X, S), 0.05, 0.95)
    
    if target == 'theta_00':
        # Standard ATE-like for A=0
        mu_at_A = mu_fn(X, np.zeros(n), M, S)
        mu_bar = mu_bar_fn(X, S, a_out=0, a_med=0)
        
        # Identify A=0 observations
        mask_A0 = (A == 0)
        
        # Residuals (Y - μ at observed Y for A=0)
        residuals = np.zeros(n)
        residuals[mask_A0] = Y[mask_A0] - mu_at_A[mask_A0]
        
        # Weight bounds under MSM
        # w_observed = I(A=0)/(1-e(X,S))
        w_obs = mask_A0.astype(float) / (1 - pi)
        
        # Bounded weights: w_L = I(A=0) / (1 - (Γ·(1-e) + e)/(Γ + 1)) ...
        # Simplified: w varies between e/(γ(1-e)+e) and γ·e/((1-e)+γ·e) under MSM
        # For A=0: bound is on (1-π') range
        
        # Lower/upper π' under MSM
        pi_lower = pi / (gamma + (1 - gamma) * pi)
        pi_upper = gamma * pi / (1 + (gamma - 1) * pi)
        pi_lower = np.clip(pi_lower, 1e-6, 1 - 1e-6)
        pi_upper = np.clip(pi_upper, 1e-6, 1 - 1e-6)
        
        # Weight bounds for A=0 obs
        w_for_A0_lower = mask_A0.astype(float) / (1 - pi_upper)  # Smallest (1-π')
        w_for_A0_upper = mask_A0.astype(float) / (1 - pi_lower)
        
        # Sort residuals: large positive residuals weighted more → larger θ
        # For upper bound: use w_upper for positive residuals, w_lower for negative
        sign_resid = np.sign(residuals)
        w_for_upper = np.where(sign_resid > 0, w_for_A0_upper, w_for_A0_lower)
        w_for_lower = np.where(sign_resid > 0, w_for_A0_lower, w_for_A0_upper)
        
        # Compute bounds
        upper = float(np.mean(w_for_upper * residuals + mu_bar))
        lower = float(np.mean(w_for_lower * residuals + mu_bar))
        
        return (lower, upper)
    
    elif target == 'theta_11':
        # Similar to theta_00 but for A=1
        mu_at_A = mu_fn(X, np.ones(n), M, S)
        mu_bar = mu_bar_fn(X, S, a_out=1, a_med=1)
        
        mask_A1 = (A == 1)
        residuals = np.zeros(n)
        residuals[mask_A1] = Y[mask_A1] - mu_at_A[mask_A1]
        
        pi_lower = pi / (gamma + (1 - gamma) * pi)
        pi_upper = gamma * pi / (1 + (gamma - 1) * pi)
        pi_lower = np.clip(pi_lower, 1e-6, 1 - 1e-6)
        pi_upper = np.clip(pi_upper, 1e-6, 1 - 1e-6)
        
        w_for_A1_lower = mask_A1.astype(float) / pi_upper  # Smallest π'
        w_for_A1_upper = mask_A1.astype(float) / pi_lower
        
        sign_resid = np.sign(residuals)
        w_for_upper = np.where(sign_resid > 0, w_for_A1_upper, w_for_A1_lower)
        w_for_lower = np.where(sign_resid > 0, w_for_A1_lower, w_for_A1_upper)
        
        upper = float(np.mean(w_for_upper * residuals + mu_bar))
        lower = float(np.mean(w_for_lower * residuals + mu_bar))
        
        return (lower, upper)
    
    elif target == 'theta_10':
        # Cross-world: E[Y_{1, M_0}]
        # MSM affects BOTH the A=1 weight (for outcome residual) AND
        # the density ratio (for cross-world adjustment)
        # We use conservative bound: vary both worst-case
        
        mu_at_A1 = mu_fn(X, np.ones(n), M, S)
        mu_bar = mu_bar_fn(X, S, a_out=1, a_med=0)  # E[μ(X,1,M,S) | M ~ A=0]
        
        mask_A1 = (A == 1)
        mask_A0 = (A == 0)
        
        # Cross-world ratio
        ratio = ratio_fn(M, X, np.zeros(n), np.ones(n), S)
        
        # Bounded propensities
        pi_lower = pi / (gamma + (1 - gamma) * pi)
        pi_upper = gamma * pi / (1 + (gamma - 1) * pi)
        pi_lower = np.clip(pi_lower, 1e-6, 1 - 1e-6)
        pi_upper = np.clip(pi_upper, 1e-6, 1 - 1e-6)
        
        # Term 1: I(A=1)/e · ratio · (Y - μ(X,1,M,S))
        residuals_A1 = np.zeros(n)
        residuals_A1[mask_A1] = (Y[mask_A1] - mu_at_A1[mask_A1]) * ratio[mask_A1]
        
        sign_t1 = np.sign(residuals_A1)
        w1_upper = mask_A1.astype(float) / pi_lower  # max weight for positive residuals
        w1_lower = mask_A1.astype(float) / pi_upper
        w1_for_upper = np.where(sign_t1 > 0, w1_upper, w1_lower)
        w1_for_lower = np.where(sign_t1 > 0, w1_lower, w1_upper)
        
        # Term 2: I(A=0)/(1-e) · (μ(X,1,M,S) - μ̄)
        residuals_A0 = np.zeros(n)
        residuals_A0[mask_A0] = mu_at_A1[mask_A0] - mu_bar[mask_A0]
        
        sign_t2 = np.sign(residuals_A0)
        w2_upper = mask_A0.astype(float) / (1 - pi_upper)
        w2_lower = mask_A0.astype(float) / (1 - pi_lower)
        w2_for_upper = np.where(sign_t2 > 0, w2_upper, w2_lower)
        w2_for_lower = np.where(sign_t2 > 0, w2_lower, w2_upper)
        
        # Compute bounds  
        upper = float(np.mean(w1_for_upper * residuals_A1 + w2_for_upper * residuals_A0 + mu_bar))
        lower = float(np.mean(w1_for_lower * residuals_A1 + w2_for_lower * residuals_A0 + mu_bar))
        
        return (lower, upper)
    
    else:
        raise ValueError(f"Unknown target: {target}")


def confounding_sensitivity_analysis(
    estimator,
    Y, A, M, X, S,
    gamma_grid: Optional[np.ndarray] = None,
    verbose: bool = True,
) -> ConfoundingSensitivityResult:
    """Marginal Sensitivity Model bounds for τ_PJ-CF under unobserved confounding.
    
    For each Γ in grid, computes worst-case lower/upper bounds on τ.
    
    Γ interpretation:
        Γ = 1: no unobserved confounding (point identification)
        Γ = 1.5: hidden confounder changes odds of A by up to 50%
        Γ = 2: hidden confounder changes odds of A by up to 2x
        Γ = 3: very strong confounding
    
    Parameters
    ----------
    estimator : fitted HCDMLEstimator or HCDMLEstimatorEIF
        Must have been fit() called first to estimate nuisances.
    Y, A, M, X, S : arrays
    gamma_grid : array of Γ values. Default: [1, 1.25, 1.5, 2, 3]
    
    Returns
    -------
    ConfoundingSensitivityResult
    """
    if gamma_grid is None:
        gamma_grid = np.array([1.0, 1.25, 1.5, 2.0, 3.0])
    
    # First fit estimator to get nuisances (full sample, no cross-fitting)
    if verbose:
        print(f"\n  Refitting nuisances on full sample for sensitivity...")
    
    # Re-fit nuisances on full sample
    n = len(Y)
    if M.ndim == 1:
        M = M.reshape(-1, 1)
    
    estimator._all_clusters = np.unique(S)
    mu_fn = estimator._fit_outcome(Y, X, A, M, S)
    e_fn = estimator._fit_propensity(A, X, S)
    density_fn, sample_fn, ratio_fn = estimator._fit_mediator_density(M, A, X, S)
    
    # Build mu_bar function (marginalized)
    rng = np.random.default_rng(42)
    n_mc = 30
    
    def mu_bar_fn(X_, S_, a_out, a_med):
        """Compute μ̄_{a_out}(X, a_med, S) via Monte Carlo."""
        n_x = len(X_)
        a_med_arr = np.full(n_x, a_med, dtype=float)
        a_out_arr = np.full(n_x, a_out, dtype=float)
        
        mu_accum = np.zeros(n_x)
        for _ in range(n_mc):
            M_prime = sample_fn(X_, a_med_arr, S_, rng)
            mu_accum += mu_fn(X_, a_out_arr, M_prime, S_)
        return mu_accum / n_mc
    
    # Get point estimate
    r_point = estimator.fit(Y=Y, A=A, M=M, X=X, S=S)
    tau_point = r_point.tau_pj_cf
    se_point = r_point.se
    
    if verbose:
        print(f"  Point estimate: τ̂ = {tau_point:+.4f} (SE = {se_point:.4f})")
        print(f"\n  Computing sensitivity bounds...")
    
    tau_lower_arr = np.zeros(len(gamma_grid))
    tau_upper_arr = np.zeros(len(gamma_grid))
    
    psi_d = estimator.psi.get('direct', 0.0)
    psi_m = estimator.psi.get('via_M', 0.0)
    
    for i, gamma in enumerate(gamma_grid):
        # Compute bounds on each θ
        if gamma == 1.0:
            # Point identified — use point estimate
            tau_lower_arr[i] = tau_point
            tau_upper_arr[i] = tau_point
            continue
        
        try:
            theta_00_l, theta_00_u = _marginal_sensitivity_bounds_single(
                Y, A, M, X, S, mu_fn, e_fn, ratio_fn, mu_bar_fn,
                gamma=gamma, target='theta_00'
            )
            theta_10_l, theta_10_u = _marginal_sensitivity_bounds_single(
                Y, A, M, X, S, mu_fn, e_fn, ratio_fn, mu_bar_fn,
                gamma=gamma, target='theta_10'
            )
            theta_11_l, theta_11_u = _marginal_sensitivity_bounds_single(
                Y, A, M, X, S, mu_fn, e_fn, ratio_fn, mu_bar_fn,
                gamma=gamma, target='theta_11'
            )
            
            # NDE = θ_10 - θ_00
            # NIE = θ_11 - θ_10
            # τ = (1-ψ_d)·NDE + (1-ψ_m)·NIE
            
            # Bounds on NDE
            NDE_lower = theta_10_l - theta_00_u
            NDE_upper = theta_10_u - theta_00_l
            
            # Bounds on NIE
            NIE_lower = theta_11_l - theta_10_u
            NIE_upper = theta_11_u - theta_10_l
            
            # Bounds on τ
            tau_lower_arr[i] = (1 - psi_d) * NDE_lower + (1 - psi_m) * NIE_lower
            tau_upper_arr[i] = (1 - psi_d) * NDE_upper + (1 - psi_m) * NIE_upper
            
            if verbose:
                print(f"  Γ = {gamma:.2f}: τ ∈ [{tau_lower_arr[i]:+.4f}, {tau_upper_arr[i]:+.4f}]")
        
        except Exception as e:
            warnings.warn(f"Γ={gamma} computation failed: {e}")
            tau_lower_arr[i] = np.nan
            tau_upper_arr[i] = np.nan
    
    # Find break point: smallest Γ where bounds cross 0 (sign flip possible)
    gamma_break = None
    for i in range(1, len(gamma_grid)):
        if not (np.isnan(tau_lower_arr[i]) or np.isnan(tau_upper_arr[i])):
            if tau_lower_arr[i] * tau_upper_arr[i] < 0:  # bounds cross zero
                # Interpolate
                if i > 0 and not (np.isnan(tau_lower_arr[i-1]) or np.isnan(tau_upper_arr[i-1])):
                    # Find Γ at which bounds first cross zero
                    if np.sign(tau_point) > 0:
                        # Track lower bound crossing zero
                        l_prev = tau_lower_arr[i-1]
                        l_cur = tau_lower_arr[i]
                        if l_prev > 0 and l_cur < 0:
                            gamma_break = gamma_grid[i-1] + (gamma_grid[i] - gamma_grid[i-1]) * l_prev / (l_prev - l_cur)
                    else:
                        u_prev = tau_upper_arr[i-1]
                        u_cur = tau_upper_arr[i]
                        if u_prev < 0 and u_cur > 0:
                            gamma_break = gamma_grid[i-1] + (gamma_grid[i] - gamma_grid[i-1]) * (-u_prev) / (u_cur - u_prev)
                else:
                    gamma_break = gamma_grid[i]
                break
    
    qualitative_robust = gamma_break is None or gamma_break > 2.0
    
    return ConfoundingSensitivityResult(
        gamma_grid=gamma_grid,
        tau_lower=tau_lower_arr,
        tau_upper=tau_upper_arr,
        gamma_break_point=gamma_break,
        qualitative_robust=qualitative_robust,
        tau_point=tau_point,
        se_point=se_point,
    )


# =========================================================================
# LEVEL C: DAG SPECIFICATION SENSITIVITY
# =========================================================================

def dag_sensitivity_analysis(
    estimator_class,
    estimator_params: Dict[str, Any],
    Y, A,
    dag_specs: List[Dict[str, Any]],
    verbose: bool = True,
) -> DAGSensitivityResult:
    """Sensitivity to different DAG specifications.
    
    Re-runs estimation across multiple defensible DAGs where the
    assignment of variables to X (covariates) vs M (mediators) varies.
    
    Parameters
    ----------
    estimator_class : class
        E.g., HCDMLEstimatorEIF
    estimator_params : dict
        Parameters for estimator constructor
    Y, A : arrays
    dag_specs : list of dict
        Each dict has keys: 'name', 'X', 'M', 'S' (the arrays)
    
    Returns
    -------
    DAGSensitivityResult
    """
    names = []
    tau_ests = []
    ci_lo = []
    ci_up = []
    
    if verbose:
        print(f"\n  DAG Sensitivity Analysis ({len(dag_specs)} specifications):")
    
    for spec in dag_specs:
        name = spec.get('name', 'unnamed')
        X_dag = spec['X']
        M_dag = spec['M']
        S_dag = spec['S']
        
        try:
            est = estimator_class(**estimator_params)
            r = est.fit(Y=Y, A=A, M=M_dag, X=X_dag, S=S_dag)
            names.append(name)
            tau_ests.append(r.tau_pj_cf)
            ci_lo.append(r.ci_lower)
            ci_up.append(r.ci_upper)
            
            if verbose:
                print(f"    {name}: τ = {r.tau_pj_cf:+.4f}")
        except Exception as e:
            warnings.warn(f"DAG '{name}' failed: {e}")
    
    tau_arr = np.array(tau_ests)
    sign_consistent = (np.sign(tau_arr) == np.sign(tau_arr[0])).all() if len(tau_arr) > 0 else True
    
    return DAGSensitivityResult(
        dag_names=names,
        tau_estimates=tau_ests,
        ci_lower=ci_lo,
        ci_upper=ci_up,
        tau_min=float(tau_arr.min()) if len(tau_arr) > 0 else 0.0,
        tau_max=float(tau_arr.max()) if len(tau_arr) > 0 else 0.0,
        sign_consistent=sign_consistent,
    )


__all__ = [
    'PsiSensitivityResult',
    'ConfoundingSensitivityResult',
    'DAGSensitivityResult',
    'psi_sensitivity_analysis',
    'confounding_sensitivity_analysis',
    'dag_sensitivity_analysis',
]