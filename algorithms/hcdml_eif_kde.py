"""
KDE (kernel density estimation) extension for HC-DML EIF estimator.

This module provides a kernel-based alternative to the default Gaussian conditional
density estimator used in HCDMLEstimatorEIF. The implementation uses residual KDE
under a per-dimension independence assumption (Naive Bayes factorization), which is
tractable for moderate-dimensional mediators (M dim 1-10) and large samples.

Mathematical formulation
------------------------
For each treatment level a in {0,1}, the conditional density g(M | X, A=a, S) is
modeled as:
    g(M | X, A=a, S) = prod_j h_{a,j}(M_j - mu_{M,j}^{(a)}(X, S))

where:
- mu_{M,j}^{(a)}(X, S) is a Ridge regression of M_j on (X, S) using A=a subset
- h_{a,j} is a univariate Gaussian KDE fit on the residuals from that regression

The density ratio g(M | 0, X, S) / g(M | 1, X, S) is computed in log-space
as a sum over dimensions of log-KDE differences, with clipping at the
configured maximum density ratio bound.

Computational cost
------------------
- Training: O(L * sum(n_a^2)) for KDE bandwidth selection per A-group
- Evaluation: O(n_eval * n_train) per (mediator dimension, A group) pair
- For OULAD (n~25K, M=4 dims, 2 A groups): ~30-60 seconds per cross-fitting fold

Limitations
-----------
1. Naive Bayes independence assumption: ignores within-mediator dependence
   conditional on (X, S, A). For mediators with strong inter-dependence beyond
   what is captured by X, S, this may introduce bias.
2. Residual KDE assumes location-shift model: g_a(M | X, S) = h_a(M - mu^{(a)}(X, S)).
   If the *spread* of M depends on X (heteroskedasticity beyond Ridge fit),
   the residual distribution is not invariant in (X, S).
3. Boundary issues for bounded mediators (e.g., probabilities in [0, 1]).
   Currently no boundary correction; users with bounded M should consider
   logit-transformation of M before applying this method.

Usage
-----
This module patches the parent HCDMLEstimatorEIF to support density_method='kernel'.
Import this module BEFORE instantiating estimator:

    from algorithms.hcdml_eif_kde import patch_kde_support
    patch_kde_support()
    
    from algorithms.hcdml_eif import HCDMLEstimatorEIF
    est = HCDMLEstimatorEIF(..., density_method='kernel')
    est.fit(...)
"""

import numpy as np
from scipy import stats as scipy_stats
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import warnings


def _fit_mediator_density_kde(self, M, A, X, S):
    """
    Fit conditional mediator density g(M | X, A, S) via residual KDE.

    Returns
    -------
    density_fn : callable
        density_fn(M_, X_, A_, S_) -> log density (for diagnostic use only;
        not directly used in EIF computation under the ratio interface).
    sample_fn : callable
        sample_fn(X_, A_, S_, rng) -> M sampled from estimated conditional.
    ratio_fn : callable
        ratio_fn(M_, X_, A_num, A_den, S_) -> g(M_|X_,A_num,S_) / g(M_|X_,A_den,S_).
    """
    n_mediators = M.shape[1]
    valid = ~np.any(np.isnan(M), axis=1)

    # Per-A storage
    models_per_a = {}     # models_per_a[a][j] = Ridge model for mediator j given (X, S) within A=a
    kdes_per_a = {}        # kdes_per_a[a][j] = scipy gaussian_kde on residuals
    scalers_per_a = {}     # scalers_per_a[a] = StandardScaler for (X, S) features in A=a
    resid_stats_per_a = {} # diagnostic: per-A, per-j (mean, std) of residuals

    for a_val in [0, 1]:
        a_mask = valid & (np.abs(A - a_val) < 1e-6)
        n_a = int(a_mask.sum())
        if n_a < 50:
            warnings.warn(
                f"KDE density: only {n_a} obs in A={a_val} group; falling back to Gaussian for this group"
            )
            models_per_a[a_val] = None
            kdes_per_a[a_val] = None
            scalers_per_a[a_val] = None
            continue

        X_a = X[a_mask]
        S_a = S[a_mask] if S is not None else np.zeros(n_a)
        M_a = M[a_mask]

        # Build feature matrix (X, S indicator dummies if S is cluster)
        feats_a = _make_features(X_a, S_a)
        scaler = StandardScaler().fit(feats_a)
        feats_a_scaled = scaler.transform(feats_a)

        models_j = []
        kdes_j = []
        resid_stats_j = []
        for j in range(n_mediators):
            model_j = Ridge(alpha=1.0).fit(feats_a_scaled, M_a[:, j])
            pred_j = model_j.predict(feats_a_scaled)
            resid_j = M_a[:, j] - pred_j

            try:
                kde_j = scipy_stats.gaussian_kde(resid_j, bw_method='scott')
            except (np.linalg.LinAlgError, ValueError) as e:
                warnings.warn(f"KDE fit failed for A={a_val}, j={j}: {e}; using Gaussian fallback")
                # Fallback Gaussian
                kde_j = None

            models_j.append(model_j)
            kdes_j.append(kde_j)
            resid_stats_j.append((float(resid_j.mean()), float(resid_j.std() + 1e-8)))

        models_per_a[a_val] = models_j
        kdes_per_a[a_val] = kdes_j
        scalers_per_a[a_val] = scaler
        resid_stats_per_a[a_val] = resid_stats_j

    # Capture self for clipping access
    clip_ratio = getattr(self, 'clip_density_ratio', 50.0)
    log_clip = np.log(clip_ratio)

    def _eval_log_density_per_dim(a_val, j, M_j_eval, X_eval, S_eval):
        """Return log g_j(M_j_eval | X_eval, A=a_val, S_eval) per observation."""
        if models_per_a.get(a_val) is None:
            # Fallback: Gaussian with overall mean/std
            mu_global = M[:, j].mean() if len(M) > 0 else 0.0
            sd_global = M[:, j].std() + 1e-6
            return scipy_stats.norm.logpdf(M_j_eval, mu_global, sd_global)

        feats_eval = _make_features(X_eval, S_eval)
        feats_eval_scaled = scalers_per_a[a_val].transform(feats_eval)
        pred_j = models_per_a[a_val][j].predict(feats_eval_scaled)
        resid_j = M_j_eval - pred_j

        kde_j = kdes_per_a[a_val][j]
        if kde_j is None:
            # Gaussian fallback for this (a, j)
            mu_r, sd_r = resid_stats_per_a[a_val][j]
            return scipy_stats.norm.logpdf(resid_j, 0.0, sd_r)

        # Vectorized KDE evaluation
        p_j = kde_j(resid_j)
        return np.log(np.maximum(p_j, 1e-30))

    def density(M_, X_, A_, S_):
        """Log density of M_ under estimated g(M | X, A, S)."""
        n = len(M_)
        log_p = np.zeros(n)
        # Vectorize by A group
        for a_val in [0, 1]:
            a_mask = np.abs(A_ - a_val) < 1e-6
            if a_mask.sum() == 0:
                continue
            for j in range(n_mediators):
                log_p[a_mask] += _eval_log_density_per_dim(
                    a_val, j, M_[a_mask, j], X_[a_mask], S_[a_mask] if S_ is not None else np.zeros(int(a_mask.sum()))
                )
        return log_p

    def sample(X_, A_, S_, rng):
        """Sample M from estimated conditional g(. | X_, A_, S_)."""
        n = len(X_)
        M_samples = np.zeros((n, n_mediators))
        for a_val in [0, 1]:
            a_mask = np.abs(A_ - a_val) < 1e-6
            n_a_eval = int(a_mask.sum())
            if n_a_eval == 0:
                continue

            if models_per_a.get(a_val) is None:
                # Fallback: use empirical M mean
                for j in range(n_mediators):
                    mu_g = M[:, j].mean()
                    sd_g = M[:, j].std() + 1e-6
                    M_samples[a_mask, j] = rng.normal(mu_g, sd_g, n_a_eval)
                continue

            feats_eval = _make_features(X_[a_mask], S_[a_mask] if S_ is not None else np.zeros(n_a_eval))
            feats_eval_scaled = scalers_per_a[a_val].transform(feats_eval)
            for j in range(n_mediators):
                pred_j = models_per_a[a_val][j].predict(feats_eval_scaled)
                kde_j = kdes_per_a[a_val][j]
                if kde_j is None:
                    _, sd_r = resid_stats_per_a[a_val][j]
                    resid_samp = rng.normal(0.0, sd_r, n_a_eval)
                else:
                    resid_samp = kde_j.resample(n_a_eval, seed=rng).ravel()
                M_samples[a_mask, j] = pred_j + resid_samp
        return M_samples

    def ratio(M_, X_, A_num, A_den, S_):
        """g(M_ | X_, A_num, S_) / g(M_ | X_, A_den, S_).

        Both A_num and A_den expected to be constant arrays (per existing call pattern).
        """
        n = len(M_)
        # Default safe value
        if n == 0:
            return np.ones(0)

        a_num_val = int(np.median(A_num)) if len(A_num) > 0 else 0
        a_den_val = int(np.median(A_den)) if len(A_den) > 0 else 1

        if models_per_a.get(a_num_val) is None or models_per_a.get(a_den_val) is None:
            return np.ones(n)

        log_ratio = np.zeros(n)
        for j in range(n_mediators):
            log_p_num = _eval_log_density_per_dim(a_num_val, j, M_[:, j], X_, S_)
            log_p_den = _eval_log_density_per_dim(a_den_val, j, M_[:, j], X_, S_)
            log_ratio += (log_p_num - log_p_den)

        log_ratio = np.clip(log_ratio, -log_clip, log_clip)
        return np.exp(log_ratio)

    return density, sample, ratio


def _make_features(X, S):
    """
    Build feature matrix for mediator regression: concatenate X and one-hot S.
    """
    X = np.atleast_2d(X)
    if X.shape[0] == 1 and X.shape[1] > 1:
        # Single-row case from view
        pass

    if S is None:
        return X

    S_arr = np.atleast_1d(S).astype(int)
    n = X.shape[0]
    if len(S_arr) != n:
        S_arr = np.broadcast_to(S_arr, (n,))

    # One-hot encode S, but skip if only one cluster value (e.g., test data)
    unique_s = np.unique(S_arr)
    if len(unique_s) <= 1:
        return X

    S_onehot = np.zeros((n, len(unique_s)))
    for k, s_val in enumerate(unique_s):
        S_onehot[S_arr == s_val, k] = 1.0
    return np.hstack([X, S_onehot])


def patch_kde_support():
    """
    Monkey-patch HCDMLEstimatorEIF to support density_method='kernel'.

    Call once before instantiating estimator:
        from algorithms.hcdml_eif_kde import patch_kde_support
        patch_kde_support()
    """
    try:
        from algorithms.hcdml_eif import HCDMLEstimatorEIF
    except ImportError as e:
        raise ImportError(
            "Cannot import HCDMLEstimatorEIF. Run this script from the project root or "
            "ensure algorithms/hcdml_eif.py is on PYTHONPATH."
        ) from e

    # Save original
    if not hasattr(HCDMLEstimatorEIF, '_fit_mediator_density_original'):
        HCDMLEstimatorEIF._fit_mediator_density_original = HCDMLEstimatorEIF._fit_mediator_density

    def patched_fit_mediator_density(self, M, A, X, S):
        if self.density_method == 'kernel':
            return _fit_mediator_density_kde(self, M, A, X, S)
        return self._fit_mediator_density_original(M, A, X, S)

    HCDMLEstimatorEIF._fit_mediator_density = patched_fit_mediator_density
    print("[hcdml_eif_kde] patch_kde_support applied: density_method='kernel' now supported")