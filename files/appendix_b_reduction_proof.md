# Appendix B: Reduction of Theorem 2 to the IID Case

## B.1 Purpose and Setup

This appendix provides a rigorous verification that the hierarchical efficient influence function (EIF) of Theorem 2 reduces, when $L = 1$ (a single cluster), to the IID semiparametric EIF for natural mediation parameters derived by Tchetgen Tchetgen and Shpitser (2014, Theorem 1, henceforth TS14). This reduction serves three purposes:

1. **Sanity check on derivation.** Any error in extending the IID EIF to clusters must manifest as a mismatch at $L = 1$; matching IID formulas is a necessary (though not sufficient) condition for correctness.
2. **Connection to established literature.** TS14 is the canonical IID semiparametric mediation reference, with established asymptotic properties. Reduction to TS14 inherits these properties as the limit case.
3. **Empirical verification target.** The numerical agreement between EIF and substitution estimators on Law School ($L = 1$, $n = 21{,}791$, Table 4) provides empirical confirmation of this reduction.

## B.2 Notation Translation

We first establish notation correspondence between this paper (LHS) and TS14 (RHS) for the natural mediation setting.

| This paper | TS14 | Quantity |
|------------|------|----------|
| $W = (Y, A, M, X, S)$ | $O = (Y, A, M, X)$ | Observed unit |
| $\theta_{aa'} = \mathbb{E}[Y_{a, M_{a'}}]$ | $\psi_{aa'}$ | Cross-world counterfactual mean |
| $\mu(X, a, M, S)$ | $E[Y \mid X, A=a, M]$ | Outcome regression |
| $e(X, S) = \mathbb{P}(A=1 \mid X, S)$ | $\pi(X) = \mathbb{P}(A=1 \mid X)$ | Propensity score |
| $g(M \mid X, a, S)$ | $f(M \mid a, X)$ | Mediator conditional density |
| $\bar{\mu}_a(X, a', S) = \int \mu(X, a, m, S) g(m \mid X, a', S) \, dm$ | $\eta_a^{a'}(X) = \int E[Y \mid X, A=a, m] f(m \mid a', X) \, dm$ | Marginalized counterfactual outcome |

The key observation for reduction is that when $L = 1$, the cluster indicator $S$ takes a single deterministic value (denote $s_0$) for all units, so conditioning on $S = s_0$ is informationally equivalent to no conditioning on $S$.

**Lemma B.1 (Vacuity of $S$-conditioning at $L = 1$).** Let $S \equiv s_0$ almost surely. Then for any random variable $V$ and any function $h$:

$$
\mathbb{E}[h(V) \mid X, S] = \mathbb{E}[h(V) \mid X] \quad \text{a.s.}
$$

*Proof.* Conditioning on a constant adds no information; the conditional expectation operator is unchanged. Formally, $\sigma(X, S) = \sigma(X)$ when $S$ is constant. $\square$

**Corollary B.1 (Nuisance reduction at $L = 1$).** Under Lemma B.1:

$$
e(X, S) = \pi(X), \quad g(M \mid X, a, S) = f(M \mid a, X), \quad \mu(X, a, M, S) = E[Y \mid X, A=a, M]
$$

$$
\bar{\mu}_a(X, a', S) = \eta_a^{a'}(X)
$$

## B.3 Reduction of $\phi_{10}$ to TS14

### B.3.1 The TS14 efficient influence function for $\psi_{aa'}$

TS14 (Theorem 1, equation 3.4 in the journal version) establishes that under sequential ignorability, the efficient influence function for $\psi_{aa'} = \mathbb{E}[Y_{a, M_{a'}}]$ in the IID setting is:

$$
\begin{aligned}
\phi^{\text{TS}}_{aa'}(O; \eta, \psi_{aa'}) =\,& \frac{\mathbb{1}\{A = a\}}{\pi_a(X)} \cdot \frac{f(M \mid a', X)}{f(M \mid a, X)} \cdot \big(Y - E[Y \mid X, A=a, M]\big) \\
&+ \frac{\mathbb{1}\{A = a'\}}{\pi_{a'}(X)} \cdot \big(E[Y \mid X, A=a, M] - \eta_a^{a'}(X)\big) \\
&+ \eta_a^{a'}(X) - \psi_{aa'}
\end{aligned}
\tag{B.1}
$$

where $\pi_a(X) = \mathbb{P}(A = a \mid X)$, so $\pi_1(X) = \pi(X)$ and $\pi_0(X) = 1 - \pi(X)$.

### B.3.2 Specialization to $(a, a') = (1, 0)$

Setting $a = 1, a' = 0$ in (B.1):

$$
\begin{aligned}
\phi^{\text{TS}}_{10}(O; \eta, \psi_{10}) =\,& \frac{\mathbb{1}\{A = 1\}}{\pi(X)} \cdot \frac{f(M \mid 0, X)}{f(M \mid 1, X)} \cdot \big(Y - E[Y \mid X, A=1, M]\big) \\
&+ \frac{\mathbb{1}\{A = 0\}}{1 - \pi(X)} \cdot \big(E[Y \mid X, A=1, M] - \eta_1^{0}(X)\big) \\
&+ \eta_1^{0}(X) - \psi_{10}
\end{aligned}
\tag{B.2}
$$

### B.3.3 Reduction of the hierarchical EIF $\phi_{10}$ at $L = 1$

Theorem 2 of the main text states the hierarchical EIF as:

$$
\begin{aligned}
\phi_{10}(W; \eta, \theta_{10}) =\,& \frac{\mathbb{1}\{A = 1\}}{e(X, S)} \cdot \frac{g(M \mid X, 0, S)}{g(M \mid X, 1, S)} \cdot \big(Y - \mu(X, 1, M, S)\big) \\
&+ \frac{\mathbb{1}\{A = 0\}}{1 - e(X, S)} \cdot \big(\mu(X, 1, M, S) - \bar{\mu}_1(X, 0, S)\big) \\
&+ \bar{\mu}_1(X, 0, S) - \theta_{10}
\end{aligned}
\tag{B.3}
$$

Applying Corollary B.1 termwise (suppressing the constant $S = s_0$):

**Term 1.** $\dfrac{\mathbb{1}\{A = 1\}}{e(X, S)} \cdot \dfrac{g(M \mid X, 0, S)}{g(M \mid X, 1, S)} \cdot \big(Y - \mu(X, 1, M, S)\big)$
$= \dfrac{\mathbb{1}\{A = 1\}}{\pi(X)} \cdot \dfrac{f(M \mid 0, X)}{f(M \mid 1, X)} \cdot \big(Y - E[Y \mid X, A=1, M]\big)$

**Term 2.** $\dfrac{\mathbb{1}\{A = 0\}}{1 - e(X, S)} \cdot \big(\mu(X, 1, M, S) - \bar{\mu}_1(X, 0, S)\big)$
$= \dfrac{\mathbb{1}\{A = 0\}}{1 - \pi(X)} \cdot \big(E[Y \mid X, A=1, M] - \eta_1^0(X)\big)$

**Term 3.** $\bar{\mu}_1(X, 0, S) - \theta_{10}$
$= \eta_1^0(X) - \psi_{10}$ (since $\theta_{10} = \psi_{10}$).

Adding terms, the right-hand side equals (B.2). Therefore:

$$
\phi_{10}(W; \eta, \theta_{10}) \big|_{L=1} = \phi^{\text{TS}}_{10}(O; \eta, \psi_{10})
\qquad \square
$$

## B.4 Reduction of $\phi_{00}$ and $\phi_{11}$

The reductions for $\phi_{00}$ and $\phi_{11}$ follow by the same procedure with $(a, a') = (0, 0)$ and $(1, 1)$ respectively.

### B.4.1 Reduction of $\phi_{00}$

Setting $(a, a') = (0, 0)$ in (B.1), the density ratio $f(M \mid 0, X) / f(M \mid 0, X) = 1$, yielding the simplified TS14 form:

$$
\phi^{\text{TS}}_{00}(O) = \frac{\mathbb{1}\{A = 0\}}{1 - \pi(X)} \big(Y - E[Y \mid X, A=0, M]\big) + \frac{\mathbb{1}\{A = 0\}}{1 - \pi(X)} \big(E[Y \mid X, A=0, M] - \eta_0^0(X)\big) + \eta_0^0(X) - \psi_{00}
\tag{B.4}
$$

The hierarchical $\phi_{00}$ from Theorem 2 is:

$$
\begin{aligned}
\phi_{00}(W) =\,& \frac{\mathbb{1}\{A = 0\}}{1 - e(X, S)} \big(Y - \mu(X, 0, M, S)\big) \\
&+ \frac{\mathbb{1}\{A = 0\}}{1 - e(X, S)} \big(\mu(X, 0, M, S) - \bar{\mu}_0(X, 0, S)\big) \\
&+ \bar{\mu}_0(X, 0, S) - \theta_{00}
\end{aligned}
\tag{B.5}
$$

Applying Corollary B.1 to each term in (B.5) yields (B.4). Note that the two IPW terms in (B.4) telescope:

$$
\phi^{\text{TS}}_{00}(O) = \frac{\mathbb{1}\{A = 0\}}{1 - \pi(X)} \big(Y - \eta_0^0(X)\big) + \eta_0^0(X) - \psi_{00}
$$

This is the standard ATE-style EIF for $\mathbb{E}[Y(A=0)]$ when applied via the marginalized regression $\eta_0^0$. The Theorem 2 form preserves the un-telescoped structure for Neyman orthogonality in finite samples (Chernozhukov et al., 2018).

### B.4.2 Reduction of $\phi_{11}$

Setting $(a, a') = (1, 1)$ in (B.1), symmetric to $\phi_{00}$:

$$
\phi^{\text{TS}}_{11}(O) = \frac{\mathbb{1}\{A = 1\}}{\pi(X)} \big(Y - E[Y \mid X, A=1, M]\big) + \frac{\mathbb{1}\{A = 1\}}{\pi(X)} \big(E[Y \mid X, A=1, M] - \eta_1^1(X)\big) + \eta_1^1(X) - \psi_{11}
\tag{B.6}
$$

Applying Corollary B.1 to the hierarchical $\phi_{11}$ yields (B.6).

## B.5 Reduction of the Path-Specific EIFs

The natural direct and natural indirect effect EIFs are linear combinations:

$$
\phi_{\text{NDE}}(W) = \phi_{10}(W) - \phi_{00}(W), \qquad \phi_{\text{NIE}}(W) = \phi_{11}(W) - \phi_{10}(W)
$$

By linearity and the componentwise reductions of Sections B.3–B.4:

$$
\phi_{\text{NDE}}(W) \big|_{L=1} = \phi^{\text{TS}}_{10}(O) - \phi^{\text{TS}}_{00}(O), \qquad \phi_{\text{NIE}}(W) \big|_{L=1} = \phi^{\text{TS}}_{11}(O) - \phi^{\text{TS}}_{10}(O)
$$

The right-hand sides are the TS14 efficient influence functions for the natural direct and indirect effects respectively (TS14, equations 3.5–3.6).

The PJ-CF estimand EIF reduces analogously:

$$
\phi_{\text{PJ-CF}}(W; \psi) \big|_{L=1} = (1 - \psi_{\text{direct}}) \phi^{\text{TS}}_{\text{NDE}}(O) + (1 - \psi_{\text{via\_M}}) \phi^{\text{TS}}_{\text{NIE}}(O)
$$

## B.6 Consequences for Asymptotic Theory

The reduction in Section B.3–B.5 has two immediate consequences:

**Consequence B.1 (Inherited efficiency bound).** At $L = 1$, the semiparametric efficiency bound for $\hat{\tau}_{\text{PJ-CF}}$ equals that of the corresponding TS14 estimator. From TS14 Theorem 1:

$$
V^*_{\text{IID}} = \mathbb{E}\big[\phi^{\text{TS}}_{\text{PJ-CF}}(O)^2\big]
$$

By Lemma B.1 and the reduction, $V^*_{L=1} = V^*_{\text{IID}}$.

**Consequence B.2 (Reduction validates implementation).** The HC-DML implementation with `n_cluster_folds = 1` and a single cluster ($L = 1$) should produce numerically identical point estimates to a TS14-conformant IID implementation, modulo Monte Carlo error in the marginalization step. This is verified empirically on Law School (Table 4, Section 5.2): the EIF estimator's $\hat{\tau} = +0.714$ agrees with the substitution estimator's $\hat{\tau} = +0.721$ to within $0.01$, consistent with Pattern 1 of method convergence at large $n$ under correctly specified nuisances.

## B.7 Limitations of This Reduction

Three caveats merit explicit acknowledgment:

1. **Reduction is at the population level.** Equality of EIFs at $L = 1$ does not imply identical finite-sample behavior between the hierarchical and IID implementations. The hierarchical implementation includes cluster-aware cross-fitting machinery that is vacuous when $L = 1$ but adds computational overhead; the substitution estimator does not include this machinery. Section 3.10.1 documents the practical performance difference.

2. **TS14 nuisance estimation differs from ours.** TS14 establishes the EIF without prescribing nuisance estimators. Our use of Ridge regression and conditional Gaussian densities differs from many TS14-conformant implementations. Equality of EIFs ensures consistency under either estimator, but rate conditions for $\sqrt{n}$-convergence (Theorem 4 condition (i)) depend on the specific estimators chosen.

3. **The cross-world independence assumption is unaltered by reduction.** Both the hierarchical and IID identification rely on the cross-world counterfactual independence assumption (Robins, 2003; Assumption 5 in Section 3.2.1). The reduction does not address its plausibility, which remains an empirically untestable identification assumption.

## B.8 Empirical Verification on Law School

The Law School dataset ($L = 1$, $n = 21{,}791$) provides a direct empirical verification of the reduction. Table 4 reports:

- Naive estimator: $\hat{\tau} = +0.721$
- Substitution estimator: $\hat{\tau} = +0.721$
- EIF estimator: $\hat{\tau} = +0.714$

The maximum pairwise difference is $0.007$ (less than $1\%$ of the estimate). This is the expected behavior under correct reduction: at $L = 1$ with sufficiently large $n$, all three estimators target the same population estimand. Disagreement greater than would be expected from Monte Carlo error in $\hat{\bar{\mu}}_a$ would indicate either implementation error or violation of the regularity conditions for $\sqrt{n}$-convergence.

---

**End of Appendix B.**

## References cited in this appendix

- Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., and Robins, J. (2018). Double/debiased machine learning for treatment and structural parameters. *The Econometrics Journal*, 21(1), C1–C68.
- Robins, J. M. (2003). Semantics of causal DAG models and the identification of direct and indirect effects. In *Highly Structured Stochastic Systems*, 70–81.
- Tchetgen Tchetgen, E. J., and Shpitser, I. (2014). Semiparametric theory for causal mediation analysis: efficiency bounds, multiple robustness, and sensitivity analysis. *Annals of Statistics*, 40(3), 1816–1845.
