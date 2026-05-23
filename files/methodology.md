# 3. Methodology

## 3.1 Problem Formulation

### 3.1.1 Setup and Notation

Consider a study population partitioned into $L$ clusters indexed by $s \in \{1, \dots, L\}$ (e.g., course modules, schools, or cohorts), with $n_s$ individuals per cluster and total sample size $n = \sum_{s=1}^{L} n_s$. For each individual $i$ in cluster $s$, we observe the random vector $W_i = (Y_i, A_i, M_i, X_i, S_i)$, where:

- $Y_i \in \mathcal{Y} \subseteq \mathbb{R}$ is the outcome of interest (e.g., final grade, pass/fail indicator, predicted probability of success)
- $A_i \in \{0, 1\}$ is a binary protected attribute (e.g., gender, race, socioeconomic status)
- $M_i \in \mathcal{M} \subseteq \mathbb{R}^p$ is a $p$-dimensional vector of mediators (post-treatment variables on causal pathway from $A$ to $Y$, e.g., engagement metrics, prior assessment scores)
- $X_i \in \mathcal{X} \subseteq \mathbb{R}^q$ is a $q$-dimensional vector of pre-treatment covariates (variables determined before $A$, e.g., demographics, socioeconomic background)
- $S_i \in \{1, \dots, L\}$ is the cluster membership indicator

We assume observations are independent across clusters but dependent within clusters due to shared cluster-level effects. This hierarchical structure characterizes virtually all educational datasets, where students are nested within courses, courses within institutions, and cohorts within time periods.

### 3.1.2 Causal Model

We posit the following structural causal model with cluster random effects $U_s$:

$$
\begin{aligned}
X_i &= f_X(\epsilon^X_i, U_{S_i}) \\
A_i &= f_A(X_i, \epsilon^A_i, U_{S_i}) \\
M_i &= f_M(X_i, A_i, \epsilon^M_i, U_{S_i}) \\
Y_i &= f_Y(X_i, A_i, M_i, \epsilon^Y_i, U_{S_i})
\end{aligned}
$$

where $\epsilon^V_i$ denote individual-level idiosyncratic noise components and $U_{S_i}$ represents cluster-level unobserved heterogeneity. The cluster random effects $U_s$ induce within-cluster correlation absent in standard counterfactual fairness literature.

### 3.1.3 Path-Specific Counterfactual Quantities

Following Avin, Shpitser, and Pearl (2005), we define path-specific potential outcomes. For binary treatment values $a, a' \in \{0, 1\}$:

- $M_a$: the counterfactual mediator value when $A$ is set to $a$
- $Y_{a, M_{a'}}$: the counterfactual outcome when $A$ is set to $a$ for the direct effect path, while $M$ is set to its natural value under $A = a'$ for the indirect path

The two-path decomposition yields:

$$
\text{NDE} = \mathbb{E}[Y_{1, M_0} - Y_{0, M_0}] \quad \text{(Natural Direct Effect)}
$$

$$
\text{NIE} = \mathbb{E}[Y_{1, M_1} - Y_{1, M_0}] \quad \text{(Natural Indirect Effect)}
$$

The total effect decomposes as $\text{TE} = \text{NDE} + \text{NIE}$.

### 3.1.4 Path-Justified Counterfactual Fairness (PJ-CF) Estimand

Standard counterfactual fairness (Kusner et al., 2017) operates on total effects, conflating discriminatory and legitimate pathways. We introduce the **Pedagogical Justifiability Function** $\psi: \Pi \to [0, 1]$, where $\Pi = \{\text{direct}, \text{via\_M}\}$ denotes the set of causal paths:

- $\psi(\pi) = 0$: path $\pi$ is fully unjustified (contributes entirely to bias)
- $\psi(\pi) = 1$: path $\pi$ is fully justified (excluded from bias measure)
- $\psi(\pi) \in (0, 1)$: partially justified path

The target estimand is the **Path-Justified Counterfactual Fairness measure**:

$$
\tau_{\text{PJ-CF}}(\psi) = (1 - \psi_{\text{direct}}) \cdot \text{NDE} + (1 - \psi_{\text{via\_M}}) \cdot \text{NIE}
$$

Sensitivity analysis over $\psi$ values reveals robustness of fairness conclusions to alternative justifiability assumptions. When $\psi \equiv 0$, $\tau_{\text{PJ-CF}}$ reduces to the total counterfactual fairness measure of Kusner et al. (2017).

---

## 3.2 Identification Theory

### 3.2.1 Identification Assumptions

For identification of NDE and NIE in clustered data, we require the following assumptions:

**Assumption 1 (Hierarchical Sequential Ignorability).** For all $a, a' \in \{0, 1\}$:

$$
\{Y_{a, M_{a'}}, M_a\} \perp\!\!\!\perp A \mid X, S
$$

$$
Y_{a, M_{a'}} \perp\!\!\!\perp M_a \mid X, A = a, S
$$

This extends the standard sequential ignorability (Imai et al., 2010) by conditioning on cluster membership $S$, thereby absorbing cluster-level confounding $U_s$ that would otherwise violate the IID-based identification.

**Assumption 2 (Positivity within Clusters).** There exists $\eta > 0$ such that for all $a \in \{0, 1\}$, $x \in \text{supp}(X)$, $s \in \{1, \dots, L\}$:

$$
\mathbb{P}(A = a \mid X = x, S = s) \in (\eta, 1 - \eta)
$$

with analogous overlap conditions for mediator distributions $g(m \mid x, a, s)$.

**Assumption 3 (Cluster-Conditional Independence).** Conditional on cluster effects $U_s$, observations within a cluster are independent:

$$
W_i \perp\!\!\!\perp W_j \mid U_{S_i} \quad \text{for } i \neq j, \, S_i = S_j
$$

**Assumption 4 (No Cross-Cluster Interference).** Potential outcomes for individual $i$ do not depend on treatment assignments of individuals in different clusters $j$ with $S_i \neq S_j$.

**Assumption 5 (Cross-World Independence).** Following Robins (2003), we assume the cross-world counterfactual independence necessary for path-specific identification.

### 3.2.2 Identification Result

**Theorem 1 (Hierarchical PSE Identification).** Under Assumptions 1–5, the natural direct and indirect effects are identified from the observed distribution as:

$$
\text{NDE} = \mathbb{E}_{X, S}\left[\int \{\mu(X, 1, m, S) - \mu(X, 0, m, S)\} \, g(m \mid X, A=0, S) \, dm\right]
$$

$$
\text{NIE} = \mathbb{E}_{X, S}\left[\int \mu(X, 1, m, S) \{g(m \mid X, 1, S) - g(m \mid X, 0, S)\} \, dm\right]
$$

where $\mu(x, a, m, s) = \mathbb{E}[Y \mid X=x, A=a, M=m, S=s]$ denotes the outcome regression function and $g(m \mid x, a, s)$ denotes the conditional mediator density.

This extends the Pearl (2001) mediation formula to the hierarchical setting. The key novelty lies in conditioning on cluster $S$ throughout the nuisance functions, which prevents the bias that would arise from ignoring cluster-level confounding.

**Corollary 1 (IID Reduction).** When $L = 1$ (single cluster), Theorem 1 reduces to the standard Tchetgen-Shpitser (2014) identification with $S$ dropped from conditioning sets.

---

## 3.3 The HC-DML Estimator

### 3.3.1 Nuisance Parameters

The PJ-CF estimand depends on the following nuisance parameters $\eta = (\mu, e, g)$:

- **Outcome regression**: $\mu(x, a, m, s) = \mathbb{E}[Y \mid X=x, A=a, M=m, S=s]$
- **Propensity score**: $e(x, s) = \mathbb{P}(A = 1 \mid X=x, S=s)$
- **Mediator density**: $g(m \mid x, a, s) = $ conditional density of $M$ given $(X, A, S)$

Additionally, we require the **marginalized counterfactual outcome**:

$$
\bar{\mu}_a(x, a', s) = \int \mu(x, a, m, s) \, g(m \mid x, a', s) \, dm
$$

which represents the expected outcome under treatment $a$ when mediator $M$ is drawn from its distribution under treatment $a'$.

### 3.3.2 Efficient Influence Function

We derive the efficient influence function (EIF) for each component of the target via pathwise derivatives on parametric submodels (Bickel et al., 1993; van der Laan and Robins, 2003).

**Theorem 2 (EIF for Hierarchical PSE).** Under Assumptions 1–5, the efficient influence function for $\theta_{10} = \mathbb{E}[Y_{1, M_0}]$ is:

$$
\begin{aligned}
\phi_{10}(W; \eta, \theta_{10}) &= \frac{\mathbb{1}\{A = 1\}}{e(X, S)} \cdot \frac{g(M \mid X, 0, S)}{g(M \mid X, 1, S)} \cdot \{Y - \mu(X, 1, M, S)\} \\
&\quad + \frac{\mathbb{1}\{A = 0\}}{1 - e(X, S)} \cdot \{\mu(X, 1, M, S) - \bar{\mu}_1(X, 0, S)\} \\
&\quad + \bar{\mu}_1(X, 0, S) - \theta_{10}
\end{aligned}
$$

The EIF for $\theta_{00} = \mathbb{E}[Y_{0, M_0}]$ is:

$$
\begin{aligned}
\phi_{00}(W; \eta, \theta_{00}) &= \frac{\mathbb{1}\{A = 0\}}{1 - e(X, S)} \cdot \{Y - \mu(X, 0, M, S)\} \\
&\quad + \frac{\mathbb{1}\{A = 0\}}{1 - e(X, S)} \cdot \{\mu(X, 0, M, S) - \bar{\mu}_0(X, 0, S)\} \\
&\quad + \bar{\mu}_0(X, 0, S) - \theta_{00}
\end{aligned}
$$

and analogously $\phi_{11}$ for $\theta_{11} = \mathbb{E}[Y_{1, M_1}]$. The path-specific effect EIFs are:

$$
\phi_{\text{NDE}}(W) = \phi_{10}(W) - \phi_{00}(W)
$$

$$
\phi_{\text{NIE}}(W) = \phi_{11}(W) - \phi_{10}(W)
$$

The EIF for the PJ-CF estimand is:

$$
\phi_{\text{PJ-CF}}(W; \eta, \psi) = (1 - \psi_{\text{direct}}) \cdot \phi_{\text{NDE}}(W) + (1 - \psi_{\text{via\_M}}) \cdot \phi_{\text{NIE}}(W)
$$

**Critical implementation note.** The plug-in terms must use the marginalized outcome $\bar{\mu}_a(X, a', S)$, NOT the conditional version $\mu(X, a, M_{\text{obs}}, S)$. The latter introduces systematic bias when applied to observations with $A \neq a'$, as $M_{\text{obs}}$ is then drawn from the wrong distribution. This was confirmed empirically: substituting $\mu(X, 0, M, S)$ for $\bar{\mu}_0(X, 0, S)$ in $\phi_{00}$ produces bias of approximately $0.5(\theta_{10} - \theta_{00})$.

### 3.3.3 Neyman Orthogonality

**Theorem 3 (Neyman Orthogonality).** The EIF in Theorem 2 satisfies the Neyman orthogonality condition:

$$
\frac{\partial}{\partial r} \mathbb{E}[\phi_{\text{PJ-CF}}(W; \eta_0 + r(\tilde{\eta} - \eta_0), \tau_0)] \bigg|_{r=0} = 0
$$

for all admissible perturbations $\tilde{\eta}$ of the nuisance parameter $\eta = (\mu, e, g)$.

This property is critical: it implies that first-order errors in nuisance estimation do not contaminate the estimator. This enables the use of flexible machine learning methods for $\hat{\eta}$ while preserving valid statistical inference.

### 3.3.4 Hierarchical Cross-Fitting

To avoid overfitting bias in nuisance estimation, we employ K-fold cross-fitting (Chernozhukov et al., 2018) adapted to the clustered setting following Liu, Liu, and Sasaki (2024). The procedure consists of:

**Step 1 (Cluster-aware fold creation).** Partition the $L$ clusters into $K$ disjoint sets $\mathcal{C}_1, \dots, \mathcal{C}_K$ of approximately equal cluster count. Define training fold $\mathcal{D}_k^{\text{train}}$ as observations from clusters not in $\mathcal{C}_k$, and evaluation fold $\mathcal{D}_k^{\text{eval}}$ as observations from clusters in $\mathcal{C}_k$.

**Step 2 (Nuisance estimation on training folds).** For each fold $k$:
- Estimate outcome regression: $\hat{\mu}^{(-k)}$ from $\mathcal{D}_k^{\text{train}}$
- Estimate propensity score: $\hat{e}^{(-k)}$ from $\mathcal{D}_k^{\text{train}}$
- Estimate mediator density: $\hat{g}^{(-k)}$ from $\mathcal{D}_k^{\text{train}}$
- Compute marginalized outcomes $\hat{\bar{\mu}}_a^{(-k)}$ via Monte Carlo sampling from $\hat{g}^{(-k)}$

**Step 3 (Score computation on evaluation folds).** For each observation $i \in \mathcal{D}_k^{\text{eval}}$:

$$
\hat{\phi}_i = \phi_{\text{PJ-CF}}(W_i; \hat{\eta}^{(-k(i))}, \psi)
$$

**Step 4 (Estimator).** The HC-DML estimator solves $\sum_i \hat{\phi}_i^* = 0$ for $\hat{\tau}_n$, where $\hat{\phi}_i^*$ denotes the score with the $-\tau$ term removed:

$$
\hat{\tau}_n = \frac{1}{n} \sum_{i=1}^{n} \hat{\phi}_i^*
$$

### 3.3.5 Cluster-Robust Variance Estimation

To account for within-cluster correlation, we estimate the variance using a multi-way clustered sandwich estimator:

$$
\hat{V}_n = \frac{1}{n} \sum_{s=1}^{L} \left( \sum_{i: S_i = s} \hat{\phi}_i \right)^2 \cdot \frac{L}{L-1}
$$

The final 95% confidence interval is:

$$
\text{CI}_{95\%} = \hat{\tau}_n \pm 1.96 \cdot \sqrt{\hat{V}_n / n}
$$

For settings with few clusters ($L < 30$), we recommend cluster bootstrap (Section 3.5) for more reliable inference.

---

## 3.4 Asymptotic Properties

### 3.4.1 Consistency and Asymptotic Normality

**Theorem 4 ($\sqrt{n}$-Asymptotic Normality).** Suppose Assumptions 1–5 hold, and:

(i) **Nuisance convergence rates:**
$$
\|\hat{\mu} - \mu_0\|_{L_2} \cdot \|\hat{g} - g_0\|_{L_2} = o_p(n^{-1/2})
$$
with analogous product rates for $(\hat{\mu}, \hat{e})$ and $(\hat{g}, \hat{e})$.

(ii) **Bounded second moments:** $\mathbb{E}[\phi^2(W; \eta_0, \tau_0)] < \infty$.

(iii) **Cluster growth condition:** $L \to \infty$ as $n \to \infty$, with $\max_s n_s / n \to 0$.

Then the cross-fitted HC-DML estimator $\hat{\tau}_n$ satisfies:

$$
\sqrt{n}(\hat{\tau}_n - \tau_0) \xrightarrow{d} \mathcal{N}(0, V^*)
$$

where $V^* = \mathbb{E}[\phi^2(W; \eta_0, \tau_0)]$ is the semiparametric efficiency bound for hierarchical i.i.d. data.

The proof combines the DML asymptotic framework of Chernozhukov et al. (2018) with the cluster CLT of Liu, Liu, and Sasaki (2024, Theorem 4.1). The key modifications from the IID case are: (1) replacement of single-fold cross-fitting with cluster-aware cross-fitting, and (2) replacement of standard CLT with cluster CLT requiring $L \to \infty$.

### 3.4.2 Doubly Robust Property

**Theorem 5 (Doubly Robust).** The HC-DML estimator satisfies $\hat{\tau}_n \xrightarrow{p} \tau_0$ if EITHER:

(a) $\hat{\mu}$ is consistently estimated, regardless of $(\hat{e}, \hat{g})$, OR

(b) $(\hat{e}, \hat{g})$ are consistently estimated, regardless of $\hat{\mu}$.

This property follows from the structure of the EIF: the score can be rewritten so that the bias term cancels under either consistency condition. The doubly robust property provides practical robustness to one form of model misspecification, which is particularly valuable in applications where the correct functional forms of nuisance functions are unknown.

---

## 3.5 Bootstrap Inference

The substitution-based estimator (Section 3.7) systematically underestimates standard errors due to the absence of doubly robust correction terms. To provide honest inference for both estimators and to address finite-sample concerns when $L < 30$, we implement cluster bootstrap inference.

### 3.5.1 Cluster Bootstrap Procedure

For $B$ bootstrap replications $b = 1, \dots, B$:

**Step 1 (Cluster resampling).** Sample $L$ clusters with replacement from the $L$ original clusters.

**Step 2 (Data assembly).** Construct the bootstrap sample by taking all observations from the sampled clusters.

**Step 3 (Re-estimation).** Re-run the HC-DML algorithm on the bootstrap sample with a new random state for cross-fitting, yielding $\hat{\tau}_n^{(b)}$.

**Step 4 (Statistical summaries).** Compute:

- Bootstrap mean: $\bar{\tau}^* = B^{-1} \sum_b \hat{\tau}_n^{(b)}$
- Bootstrap standard error: $\hat{\text{SE}}_{\text{boot}} = \sqrt{(B-1)^{-1} \sum_b (\hat{\tau}_n^{(b)} - \bar{\tau}^*)^2}$
- Percentile 95% CI: $[\hat{q}_{0.025}, \hat{q}_{0.975}]$ where $\hat{q}_\alpha$ is the $\alpha$-quantile of bootstrap estimates

### 3.5.2 Bias-Corrected Accelerated (BCa) Intervals

For improved coverage properties, we optionally compute BCa intervals (Efron, 1987) using:

- Bias correction: $\hat{z}_0 = \Phi^{-1}\left(B^{-1} \sum_b \mathbb{1}\{\hat{\tau}_n^{(b)} < \hat{\tau}_n\}\right)$
- Acceleration: $\hat{a}$ via leave-one-cluster-out jackknife when $L \leq 30$, or bootstrap skewness when $L > 30$

The BCa interval is:

$$
\text{CI}_{\text{BCa}} = [\hat{q}_{\alpha_1}, \hat{q}_{\alpha_2}]
$$

where $\alpha_1, \alpha_2$ are adjusted quantile levels accounting for bias and acceleration.

We recommend $B \geq 200$ for paper-quality inference; $B \geq 500$ for BCa intervals.

---

## 3.6 Sensitivity Analysis Framework

A critical limitation of any causal inference procedure is its dependence on untestable assumptions. We provide a three-level sensitivity analysis framework addressing the most relevant violations.

### 3.6.1 Level A: Sensitivity to Path Justifiability ($\psi$)

The PJ-CF estimand depends on user-specified justifiability weights $\psi$, which encode normative judgments about which causal pathways are considered discriminatory. To assess robustness of fairness conclusions, we vary $\psi$ over a grid:

$$
\psi_{\text{via\_M}} \in \{0, 0.25, 0.5, 0.75, 1.0\}
$$

while typically holding $\psi_{\text{direct}} = 0$ (direct effects are universally considered unjustified). For each grid point, we re-estimate $\hat{\tau}_n(\psi)$ and report:

1. **Range of estimates:** $[\min_\psi \hat{\tau}_n(\psi), \max_\psi \hat{\tau}_n(\psi)]$
2. **Sign robustness:** whether all estimates share the same sign
3. **Zero-crossing point:** $\psi^*$ such that $\hat{\tau}_n(\psi^*) = 0$, if it exists

Sign robustness implies the qualitative fairness conclusion does not depend on the specific justifiability assumption.

### 3.6.2 Level B: Sensitivity to Unobserved Confounding (Marginal Sensitivity Model)

Assumption 1 (Hierarchical Sequential Ignorability) requires no unobserved confounders, which is generally untestable. Following Tan (2006) and Zhao, Small, and Bhattacharya (2019), we extend the Marginal Sensitivity Model to path-specific effects in clustered data.

**Sensitivity parameter $\Gamma$.** For $\Gamma \geq 1$, the Marginal Sensitivity Model bounds the odds ratio between the observed propensity $e(X, S)$ and the true propensity that would obtain under unobserved confounding $e^*(X, S, U)$:

$$
\frac{1}{\Gamma} \leq \frac{e^*(X, S, U) / (1 - e^*(X, S, U))}{e(X, S) / (1 - e(X, S))} \leq \Gamma
$$

This implies bounded "true" propensities:

$$
e_L(X, S; \Gamma) = \frac{e(X, S)}{\Gamma + (1 - \Gamma) e(X, S)} \leq e^*(X, S, U) \leq \frac{\Gamma \cdot e(X, S)}{1 + (\Gamma - 1) e(X, S)} = e_U(X, S; \Gamma)
$$

**Path-specific bounds.** For each target $\theta_{aa'}$ (with $a, a' \in \{0, 1\}$), the sensitivity bounds are obtained by worst-case re-weighting of residuals:

$$
\theta_{aa'}^{\text{upper}}(\Gamma) = \mathbb{E}\left[w^{\text{adv}}_{aa'}(W; \Gamma) \cdot \text{residual}_{aa'}(W) + \bar{\mu}_{aa'}(X, S)\right]
$$

$$
\theta_{aa'}^{\text{lower}}(\Gamma) = \mathbb{E}\left[w^{\text{ben}}_{aa'}(W; \Gamma) \cdot \text{residual}_{aa'}(W) + \bar{\mu}_{aa'}(X, S)\right]
$$

where $w^{\text{adv}}, w^{\text{ben}}$ denote adverse and beneficial weights respectively, constructed from $e_L$ and $e_U$ depending on the sign of residuals. Bounds on PJ-CF are then propagated:

$$
\tau^{\text{lower}}_{\text{PJ-CF}}(\Gamma) = (1 - \psi_d)(\theta_{10}^{\text{lower}} - \theta_{00}^{\text{upper}}) + (1 - \psi_m)(\theta_{11}^{\text{lower}} - \theta_{10}^{\text{upper}})
$$

$$
\tau^{\text{upper}}_{\text{PJ-CF}}(\Gamma) = (1 - \psi_d)(\theta_{10}^{\text{upper}} - \theta_{00}^{\text{lower}}) + (1 - \psi_m)(\theta_{11}^{\text{upper}} - \theta_{10}^{\text{lower}})
$$

**Break point.** We define $\Gamma_{\text{break}}$ as the smallest $\Gamma$ for which the bounds cross zero (i.e., the sign of $\tau$ can no longer be determined). $\Gamma_{\text{break}}$ provides an interpretable measure of robustness:

- $\Gamma_{\text{break}} > 2.0$: qualitatively robust (unobserved confounding must change odds of treatment by 2x to flip conclusion)
- $1.5 \leq \Gamma_{\text{break}} \leq 2.0$: moderately robust
- $\Gamma_{\text{break}} < 1.5$: fragile to unobserved confounding

**Caveat on bound tightness.** The bounds derived here may be conservative as they vary both propensity and density ratio at worst case simultaneously. Tighter bounds exploiting the path-specific structure remain an open question.

### 3.6.3 Level C: Sensitivity to DAG Specification

The causal DAG determining which variables are pre-treatment covariates $X$ versus mediators $M$ involves substantive domain knowledge that may be contested. We evaluate sensitivity by re-running estimation across alternative defensible specifications:

For each alternative DAG specification $\mathcal{G}^{(j)}$ defining $(X^{(j)}, M^{(j)})$, we estimate $\hat{\tau}_n^{(j)}$ and report:

1. **Range across DAGs:** $[\min_j \hat{\tau}_n^{(j)}, \max_j \hat{\tau}_n^{(j)}]$
2. **Sign consistency:** proportion of DAGs yielding same-sign estimates

DAG sensitivity is particularly important in education applications where the distinction between "pre-existing" covariates and "treatment-induced" mediators may be ambiguous.

---

## 3.7 Baseline Comparators

We compare HC-DML against three baselines representing different modeling traditions:

### 3.7.1 Naive Plug-in Estimator

The simplest baseline computes a linear regression of $Y$ on $(X, A, M)$ and reports the coefficient on $A$:

$$
\hat{\tau}_{\text{Naive}} = \hat{\beta}_A \text{ from OLS: } Y = \alpha + \beta_X^\top X + \beta_A A + \beta_M^\top M + \epsilon
$$

This estimator ignores both cluster structure and path-specific decomposition. It serves to quantify the bias introduced by these simplifications.

### 3.7.2 Single-Level DML

The Chernozhukov et al. (2018) double machine learning estimator without cluster awareness:

$$
\hat{\tau}_{\text{DML}} = \frac{1}{n} \sum_i \phi^{\text{IID}}(W_i; \hat{\eta}^{(-k(i))})
$$

where $\phi^{\text{IID}}$ is the IID-equivalent of our hierarchical EIF (i.e., dropping $S$ from conditioning sets), and cross-fitting uses standard random folds. Compares HC-DML against a benchmark that addresses one limitation (overfitting) but not the other (clustering).

### 3.7.3 Path-Specific Counterfactual Fairness (Simplified)

A simplified implementation inspired by Chiappa (2019), using principal component analysis for latent representation rather than a full variational autoencoder. We use this as comparator while acknowledging it differs from the original VAE+MMD approach; the simplification is for computational tractability.

### 3.7.4 Substitution-Based HC-DML (Ablation)

To isolate the contribution of the EIF, we implement a substitution-based version of HC-DML using only the plug-in component:

$$
\hat{\tau}_{\text{sub}} = \frac{1}{n} \sum_i \left[\hat{\mu}(X_i, 1, \hat{M}_0^{(i)}, S_i) - \hat{\mu}(X_i, 0, \hat{M}_0^{(i)}, S_i)\right] \cdot (1 - \psi_d) + \ldots
$$

where $\hat{M}_0^{(i)}$ are sampled from $\hat{g}(\cdot \mid X_i, 0, S_i)$. This estimator is consistent under correct nuisance specification but lacks doubly robust property and produces severely underestimated standard errors.

---

## 3.8 Nuisance Estimation Specifics

### 3.8.1 Default Learners

The HC-DML framework is agnostic to the choice of machine learning algorithms for nuisance estimation, subject to convergence rate conditions (Theorem 4). We provide flexible specification:

- **Outcome regression $\hat{\mu}$:** Default Ridge regression (continuous $Y$) or LogisticRegression (binary $Y$, auto-detected); also supports Gradient Boosting and other sklearn-compatible regressors
- **Propensity score $\hat{e}$:** Default LogisticRegression; supports any classifier with `predict_proba`
- **Mediator density $\hat{g}$:** Gaussian conditional with cluster-aware feature inclusion; ratio computed analytically

For binary outcomes, the outcome model is fit using logistic regression to ensure predictions in $[0, 1]$; predictions for continuous outcomes are clipped to a margin around the observed $Y$ range to prevent extreme extrapolation.

### 3.8.2 Density Ratio Stability

The cross-world density ratio $g(M \mid X, 0, S) / g(M \mid X, 1, S)$ can become numerically unstable when mediator distributions differ substantially between treatment groups. We apply:

1. **Log-ratio clipping:** $\log \left[g(M \mid X, 0, S) / g(M \mid X, 1, S)\right] \in [-\log \Gamma_{\max}, \log \Gamma_{\max}]$ with default $\Gamma_{\max} = 5$
2. **Propensity clipping:** $\hat{e}(X, S) \in [0.05, 0.95]$
3. **MAD-based outlier trimming:** Observations with EIF scores deviating from median by more than $10 \times \text{MAD}$ are excluded (typically < 1% of observations); trim automatically disabled if > 10% of observations flagged

### 3.8.3 Diagnostic Tracking

The implementation tracks diagnostic quantities reported alongside estimates:

- **Maximum unclipped density ratio:** indicates extent of overlap violations
- **Number of clipped observations:** flags potential instability
- **Number of trimmed observations:** indicates outlier prevalence
- **EIF score centered means:** should be approximately zero for consistent estimation

These diagnostics enable practitioners to assess whether EIF results should be trusted or whether alternative methods (substitution + bootstrap) are preferable.

### 3.8.4 Sample Size Considerations

The EIF estimator requires sufficient sample size for both nuisance estimation rates and stable density ratio computation. Based on extensive simulation and empirical experience, we recommend:

- $n \geq 1000$: EIF estimator generally reliable
- $500 \leq n < 1000$: EIF feasible but bootstrap inference strongly recommended
- $n < 500$: substitution estimator with bootstrap inference preferred over EIF

The implementation issues warnings when $n < 1000$, alerting users to potential instabilities.

---

## 3.9 Implementation Summary

The complete HC-DML pipeline integrates the following components:

```
Algorithm: HC-DML with EIF
─────────────────────────────────────────
Input:    Data {(Y_i, A_i, M_i, X_i, S_i)}_{i=1}^n
          Justifiability ψ: Π → [0,1]
          Number of folds K
          Nuisance learners (μ̂, ê, ĝ)

Output:   Estimate τ̂, SE, 95% CI, diagnostic warnings

1. Validate inputs and detect binary outcomes
2. If n < min_n_threshold, issue sample size warning
3. Create K cluster-aware folds based on S
4. For k = 1, ..., K:
   a. Fit nuisance models on D \ D_k
   b. Compute marginalized outcomes via Monte Carlo
   c. Compute EIF scores φ̂_i on D_k
   d. Track diagnostic quantities
5. Optionally trim catastrophic outliers via MAD criterion
6. Compute:
   τ̂ = n⁻¹ Σ_i φ̂_i*
   V̂ = cluster-robust sandwich estimator
   CI = τ̂ ± 1.96·√(V̂/n)
7. (Optional) Bootstrap inference: refit B times,
   compute percentile / BCa intervals
8. (Optional) Sensitivity analyses (Levels A, B, C)
9. Return results with diagnostic reporting
```

### 3.9.1 Software Availability

The complete implementation is released as open-source Python code, structured for reproducibility:

- **Core estimators**: `hcdml.py` (substitution), `hcdml_eif.py` (efficient)
- **Inference**: `bootstrap_inference.py` (cluster + iid + wild cluster)
- **Sensitivity**: `sensitivity.py` (ψ, confounding, DAG levels)
- **Baselines**: `baselines.py` (Naive, SingleLevelDML, simplified Chiappa)
- **Data loaders**: pre-built loaders for UCI Student, xAPI, Law School (LSAC), OULAD, with auto-detection of variable encodings
- **Diagnostic utilities**: `diagnostics.py` for DGP validation

All estimators conform to a unified interface (scikit-learn compatible), enabling drop-in replacement and consistent diagnostic reporting.

---

## 3.10 Computational Considerations

### 3.10.1 Scalability

The dominant computational cost is nuisance estimation, with complexity $O(K \cdot n \cdot \text{cost}(\text{learner}))$ for cross-fitting. Monte Carlo marginalization of $\bar{\mu}$ adds $O(K \cdot n \cdot M)$ cost, where $M$ is the number of MC samples (default 50). On a standard workstation:

- UCI Student datasets (n ≈ 500): < 1 second per fit
- xAPI dataset (n = 480, L = 12 clusters): < 1 second per fit
- Law School (n = 21,791): 0.5–1 second per fit
- OULAD (n = 25,820, L = 22 clusters): 5–15 seconds per fit

Bootstrap inference scales linearly with $B$ replications. For $B = 200$ on OULAD, expect 15–45 minutes total computation. Sensitivity analysis (Level B) requires only one nuisance fit followed by closed-form bound computation, adding negligible overhead.

### 3.10.2 Memory Considerations

The framework stores all $n$ EIF scores plus the original data, requiring $O(n)$ memory beyond the underlying learner requirements. For datasets exceeding available memory (e.g., OULAD with full VLE click logs), we provide chunked loading utilities that aggregate auxiliary tables in pieces.

---

## 3.11 Methodological Innovations Summary

The HC-DML framework combines and extends several existing methodological streams:

1. **Path-specific effects** (Avin et al., 2005; Imai et al., 2010): we adopt the natural direct/indirect decomposition and extend to clustered data.

2. **Counterfactual fairness** (Kusner et al., 2017): we generalize the total-effect approach via the pedagogical justifiability function $\psi$.

3. **Path-specific counterfactual fairness** (Chiappa, 2019): we provide a non-parametric alternative to VAE-based approaches with formal asymptotic guarantees.

4. **Double machine learning** (Chernozhukov et al., 2018): we adapt the DML framework to incorporate cluster structure and path-specific scores.

5. **Multi-way clustered DML** (Liu et al., 2024): we extend their methodology from CATE to path-specific fairness estimation.

6. **Sensitivity for causal mediation** (Tchetgen-Tchetgen and Shpitser, 2014; Schröder et al., 2024): we adapt the Marginal Sensitivity Model to the path-specific clustered setting.

The novelty lies in the integration: the efficient influence function for path-specific effects in hierarchical data (Theorem 2) has not previously appeared in the literature, nor has the complete framework for sensitivity-aware fairness estimation in clustered educational settings.
