# 4. Experimental Setup

This section describes the empirical evaluation of HC-DML. We design experiments to address four research questions:

- **RQ1:** Does HC-DML achieve consistent estimation and valid inference under the conditions of Theorem 4?
- **RQ2:** How does HC-DML compare to baseline estimators (Naive, SingleLevelDML, simplified Chiappa) across diverse real-world educational datasets?
- **RQ3:** Does HC-DML reveal substantive fairness heterogeneity that aggregate methods miss?
- **RQ4:** How robust are estimated fairness effects to violations of identification assumptions (path justifiability, unobserved confounding)?

## 4.1 Synthetic Data Generating Processes

To assess theoretical properties under controlled conditions, we develop six data generating processes (DGPs) of increasing complexity. All synthetic experiments use ground truth values of $\tau_{\text{PJ-CF}}$ computed analytically from DGP parameters.

### 4.1.1 LinearDGP

The base DGP follows a linear structural causal model:

$$
\begin{aligned}
X &\sim \mathcal{N}(0, I_q) \\
A &\mid X \sim \text{Bernoulli}(\sigma(\alpha_X^\top X)) \\
M \mid X, A &\sim \mathcal{N}(\gamma_X^\top X + \gamma_A A, \sigma_M^2 I_p) \\
Y \mid X, A, M &\sim \mathcal{N}(\beta_X^\top X + \beta_A A + \beta_M^\top M, \sigma_Y^2)
\end{aligned}
$$

Default parameters yield true values $\text{NDE} = 0.30$, $\text{NIE} = 0.30$, $\text{Total} = 0.60$ with $q = 5$ covariates and $p = 3$ mediators. This DGP satisfies all identification assumptions exactly.

### 4.1.2 HierarchicalDGP

Extends LinearDGP with cluster random effects:

$$
\begin{aligned}
U_s &\sim \mathcal{N}(0, \tau_U^2 I), \quad s = 1, \dots, L \\
X_i &\mid U_{S_i} \sim \mathcal{N}(U_{S_i}, I_q) \\
A_i \mid X_i, U_{S_i} &\sim \text{Bernoulli}(\sigma(\alpha_X^\top X_i + \alpha_U^\top U_{S_i})) \\
M_i \mid X_i, A_i, U_{S_i} &\sim \mathcal{N}(\gamma_X^\top X_i + \gamma_A A_i + \gamma_U^\top U_{S_i}, \sigma_M^2 I_p) \\
Y_i \mid X_i, A_i, M_i, U_{S_i} &\sim \mathcal{N}(\beta_X^\top X_i + \beta_A A_i + \beta_M^\top M_i + \beta_U^\top U_{S_i}, \sigma_Y^2)
\end{aligned}
$$

The intraclass correlation coefficient (ICC) is calibrated to typical educational data values (default ICC $= 0.10$, range $[0.05, 0.20]$). Default specification uses $L = 20$ clusters with cluster sizes uniformly distributed in $[100, 300]$.

### 4.1.3 NonlinearDGP

Replaces linear structural equations with non-monotonic transformations:

$$
\begin{aligned}
M \mid X, A &\sim \mathcal{N}(\gamma_X^\top X + \gamma_A A + \delta_{XA}^\top (X \odot A) + \text{relu}(X), \sigma_M^2 I_p) \\
Y \mid X, A, M &\sim \mathcal{N}(\beta_X^\top X + \beta_A A + \beta_M^\top M + \theta_{AM}^\top (A \cdot M), \sigma_Y^2)
\end{aligned}
$$

Tests whether HC-DML with flexible nuisance learners (gradient boosting) can recover true effects under model misspecification of simpler learners.

### 4.1.4 ConfoundedDGP

Introduces a controlled unobserved confounder $U_{\text{conf}}$ affecting both $A$ and $Y$ but not included in observed $X$. Used to validate the Marginal Sensitivity Model bounds: at fixed levels of confounding, we verify that true $\tau$ lies within computed sensitivity bounds.

### 4.1.5 MissingPADGP

Simulates missingness in the protected attribute $A$ at rates of 5–20%. Tests robustness of estimation when $A$ is partially missing under missing-at-random (MAR) conditions.

### 4.1.6 FullComplexDGP

Combines hierarchical structure, non-linearity, partial unobserved confounding, and partial $A$ missingness. Approximates the complexity of real-world educational data.

## 4.2 Real-World Datasets

We evaluate HC-DML on five publicly available educational datasets representing diverse domains, sample sizes, and structural properties.

### 4.2.1 UCI Student Performance

The UCI Student Performance dataset (Cortez and Silva, 2008) contains academic records from two Portuguese secondary schools. We use the **Portuguese language** subject ($n = 649$), which provides sufficient sample size for stable nuisance estimation. The Mathematics subject ($n = 395$) was excluded from main analyses because $n < 500$ falls below the recommended threshold for EIF-based estimation (Section 3.8.4); applying our framework to this dataset produces unstable density ratio estimates and unreliable point estimates, illustrating the small-sample regime limitations discussed in Section 6.3.3. Variables for the Portuguese subject include:

- **Outcome (Y):** Final grade G3 on 0–20 scale
- **Protected (A):** Sex (binary, encoded as Female = 1)
- **Mediators (M):** Study time, absences, failures, prior grades G1 and G2 (engagement and intermediate performance indicators)
- **Covariates (X):** Age, school, address (urban/rural), family size, parental education, parental occupation, travel time, family support, paid extra classes, internet access at home
- **Clusters (S):** School (2 levels: GP, MS) — limited hierarchical structure

Despite modest sample size, this dataset serves as a benchmark replication for prior fairness work in education and illustrates lower-bound behavior of EIF-based estimators within the recommended operating regime.

### 4.2.2 xAPI Educational Mining

The xAPI Educational Mining dataset (Amrieh et al., 2016) contains learning behavior data from 480 students collected via Experience API. Variables include:

- **Outcome (Y):** Class level (Low/Medium/High, encoded as ordinal)
- **Protected (A):** Gender (binary, encoded as Female = 1)
- **Mediators (M):** Raised hands count, visited resources, viewed announcements, discussion participation
- **Covariates (X):** Nationality, place of birth, stage, grade, section, semester, relation, parent satisfaction
- **Clusters (S):** Topic (12 subjects: Math, Science, Arabic, etc.)

Provides meaningful cluster structure ($L = 12$) at modest sample size.

### 4.2.3 Law School Admissions (LSAC)

The Law School Admissions Council dataset (Wightman, 1998), preserved through replication packages of Kusner et al. (2017) and subsequent work, contains records of 21,791 law school applicants. Variables include:

- **Outcome (Y):** Binary indicator of passing the bar exam on first attempt (`first_pf`); $\bar{Y} = 0.888$
- **Protected (A):** Race (multi-class collapsed to White vs. non-White; $\bar{A} = 0.839$)
- **Mediators (M):** Undergraduate GPA (UGPA), LSAT score
- **Covariates (X):** Sex, region of first law school, ZFYA (Z-score first-year average), Sander index
- **Clusters (S):** None (single national pool, $L = 1$)

Serves as the canonical benchmark for counterfactual fairness with substantial sample size and well-documented findings. The IID setting ($L = 1$) provides validation of EIF behavior under conditions matching Tchetgen-Tchetgen and Shpitser (2014).

**Outcome verification.** Because the column `first_pf` is not self-documenting, we verified the outcome encoding through three diagnostics before analysis. First, the marginal pass rate (0.888) closely matches LSAC documentation's reported overall first-attempt pass rate (~86.7%). Second, the race-conditional pass rates show the expected pattern (White: 0.920, Asian: 0.815, Black: 0.618), consistent with historical literature documenting an approximately 20-percentage-point Black-White gap in bar passage; the White-vs-Non-White gap in our data is $+0.198$. Third, mediators LSAT and UGPA show the expected positive associations with `first_pf` and exhibit race-conditional means consistent with LSAC documentation (White mean LSAT = 37.5, Black = 29.4 on the 11–48 raw scale; White UGPA = 3.26, Black = 2.89 on the 0–4 scale). All diagnostics confirm `first_pf = 1` represents passing the bar exam on first attempt. We recommend analogous verification for all future fairness work on binary outcomes whose encoding is not self-evident. The verification procedure is implemented in `scripts/verify_law_school.py` and is fully reproducible.

### 4.2.4 Open University Learning Analytics Dataset (OULAD)

The OULAD dataset (Kuzilek et al., 2017) is the canonical hierarchical educational dataset, containing records from the UK's Open University spanning 7 modules across multiple presentations (2013B, 2013J, 2014B, 2014J). After filtering students with at least one assessment:

- **Outcome (Y):** Pass or Distinction in final result (binary; $\bar{Y} = 0.596$)
- **Protected (A):** Gender (binary, encoded as Female = 1; $\bar{A} = 0.450$)
- **Mediators (M):** Cumulative VLE click count, first assessment score, average assessment score, days late registration
- **Covariates (X):** Age band, region, IMD band (socioeconomic deprivation), highest education, disability, number of previous attempts, studied credits
- **Clusters (S):** Module × presentation (22 unique combinations)

Sample sizes per cluster range from 340 to 1,998. Total $n = 25{,}820$ after filtering. Cluster module codes are AAA, BBB, CCC, DDD, EEE, FFF, GGG (anonymized in original release).

### 4.2.5 Dataset Summary

| Dataset | $n$ | $L$ | $\bar{A}$ | $\bar{Y}$ | $Y$ type | Domain |
|---------|-----|-----|-----------|-----------|----------|--------|
| Synthetic (LinearDGP) | varies | varies | 0.50 | 0.00 | Continuous | — |
| UCI Portuguese | 649 | 2 | 0.59 | 11.91 | Continuous (grade) | Secondary education |
| xAPI | 480 | 12 | 0.40 | 2.00 (avg) | Ordinal | Online K–12 |
| Law School | 21,791 | 1 | 0.84 | 0.89 | Binary | Professional licensure |
| OULAD | 25,820 | 22 | 0.45 | 0.60 | Binary | Distance higher education |

## 4.3 Causal DAG Specifications

For each real-world dataset, we specify a default causal DAG based on substantive considerations, with alternative specifications evaluated as DAG sensitivity (Section 3.6.3).

### 4.3.1 Default DAG Structure

Across all datasets, we adopt the canonical structure:

```
X → A → M → Y
↓   ↓   ↓
└───→───→ Y (direct effects)
```

with cluster effects $U_s$ affecting all observed variables. This corresponds to:

- Protected attribute $A$ may depend on pre-treatment covariates $X$
- Mediators $M$ are post-treatment, capturing pathways through which $A$ affects $Y$
- Direct effects $A \to Y$ capture pathways not mediated through observed $M$
- Cluster effects $U_s$ are absorbed by conditioning on $S$

### 4.3.2 Variable Assignment Decisions

The distinction between pre-treatment covariates $X$ and post-treatment mediators $M$ requires substantive judgment. Our default assignments are:

- **UCI Student (Portuguese):** Demographics (age, address, family) as $X$; study behaviors (study time, failures) and prior grades (G1, G2) as $M$
- **xAPI:** Background variables (nationality, stage) as $X$; behavioral metrics (clicks, discussions) as $M$
- **Law School:** Sex, region, ZFYA as $X$; academic preparation indicators (UGPA, LSAT) as $M$
- **OULAD:** Demographics (age, region, IMD, education, disability) as $X$; engagement and intermediate performance as $M$

Alternative specifications (e.g., treating studied_credits as $M$ in OULAD rather than $X$, on grounds that course load is partially treatment-induced) are evaluated as DAG sensitivity.

### 4.3.3 Pedagogical Justifiability ($\psi$) Choices

For path-specific decomposition, we adopt the convention:

- $\psi_{\text{direct}} = 0$: direct effects from protected attribute to outcome are uniformly unjustified
- $\psi_{\text{via\_M}}$: varied over $\{0, 0.25, 0.5, 0.75, 1.0\}$ for sensitivity

The motivation for varying $\psi_{\text{via\_M}}$ reflects ongoing debate: some scholars argue that effects mediated through prior academic performance reflect legitimate differences in preparation (justifying $\psi \approx 1$), while others argue these prior outcomes themselves reflect upstream discrimination ($\psi \approx 0$). By presenting sensitivity to this choice, we make the normative dependence transparent.

## 4.4 Baseline Comparators

We compare HC-DML against four baselines representing distinct methodological traditions, as detailed in Section 3.7. We summarize their characteristics here:

| Method | Cluster-aware | Path-specific | Doubly robust | Asymptotic guarantees |
|--------|---------------|---------------|---------------|----------------------|
| Naive plug-in | No | Implicit | No | Under correct linear specification |
| SingleLevelDML | No | Yes (partial) | Yes | IID only |
| Simplified Chiappa | No | Yes | No | None |
| Substitution HC-DML | Yes | Yes | No | Under correct nuisance specification |
| **HC-DML (EIF)** | **Yes** | **Yes** | **Yes** | **√n under Assumptions** |

## 4.5 Implementation Details

### 4.5.1 Nuisance Learner Configurations

Default learner specifications used throughout experiments:

- **Outcome regression $\hat{\mu}$:** Ridge regression with $\alpha = 1.0$ for continuous outcomes; Logistic regression (max_iter = 2000) for binary outcomes (auto-detected)
- **Propensity score $\hat{e}$:** Logistic regression (max_iter = 1000)
- **Mediator density $\hat{g}$:** Gaussian conditional via Ridge regression for means; residual variance estimated empirically
- **Marginalization $\bar{\mu}$:** Monte Carlo with 50 samples per observation

Alternative learner specifications (Gradient Boosting Regressor, Random Forest) were also evaluated; results are similar in qualitative pattern though more computationally expensive.

### 4.5.2 Cross-Fitting Configurations

- **Number of folds (K):** 3 for all real datasets to balance computational cost against bias reduction
- **Cluster folds:** $\min(3, L)$ for datasets with $L \geq 5$; standard stratified folds for $L < 5$
- **Random seed:** Fixed at 42 for reproducibility across reported point estimates

### 4.5.3 Stability Parameters

- **Propensity clipping:** $\hat{e}(X, S) \in [0.05, 0.95]$
- **Density ratio clipping:** $\hat{g}(M \mid X, 0, S) / \hat{g}(M \mid X, 1, S) \in [0.2, 5.0]$ (i.e., $\log$-ratio in $[-\log 5, \log 5]$)
- **Score trimming:** MAD-based; threshold = $10 \times \text{MAD}$ around median (catches catastrophic outliers only)
- **Auto-disable trim:** If $> 10\%$ of observations flagged for trimming, trimming disabled with warning

### 4.5.4 Bootstrap Parameters

For Section 5.4 (bootstrap inference):

- **Number of replications (B):** 200 for paper-quality inference; 50 for preliminary diagnostics; 100 for Law School (sufficient given large $n$)
- **Bootstrap method:** Cluster bootstrap for $L > 1$; IID bootstrap for Law School and synthetic IID experiments
- **Failure handling:** If $> 25\%$ of bootstrap replications fail, computation terminated with warning

### 4.5.5 Sensitivity Analysis Parameters

For Section 5.5 (sensitivity analysis):

- **$\psi$ grid:** $\{0.0, 0.25, 0.5, 0.75, 1.0\}$ for $\psi_{\text{via\_M}}$, with $\psi_{\text{direct}} = 0$ fixed
- **$\Gamma$ grid:** $\{1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0\}$ for confounding sensitivity
- **MC samples for marginalization in sensitivity:** 30 (reduced from 50 for speed; bounds are insensitive)

### 4.5.6 Verification Protocol

To verify EIF correctness, we conduct three independent tests (detailed in Section 5.1):

1. **Consistency:** Bias of $\hat{\tau}$ should decrease as $n$ increases, with $|\hat{\tau} - \tau_0| < 0.05$ at $n = 10{,}000$
2. **IID reduction:** When $L = 1$, EIF should match substitution estimator and Tchetgen-Tchetgen and Shpitser (2014) formulas
3. **Hierarchical inference:** With proper $L$ and ICC, asymptotic SE should approximately match empirical SD across replications

All three tests pass on synthetic data (Section 5.1).

## 4.6 Evaluation Metrics

### 4.6.1 Point Estimation Quality

For synthetic experiments with known truth:

- **Bias:** $\hat{\tau} - \tau_0$
- **Root mean squared error (RMSE):** $\sqrt{(B^*)^{-1} \sum_{b=1}^{B^*} (\hat{\tau}^{(b)} - \tau_0)^2}$ where $B^*$ denotes Monte Carlo replications (distinct from bootstrap)
- **Empirical standard deviation:** Across $B^*$ replications

### 4.6.2 Inference Quality

- **Standard error:** Asymptotic SE from cluster-robust sandwich vs. bootstrap SE
- **Coverage:** Proportion of nominally 95% CIs containing true $\tau_0$ (synthetic only)
- **SE ratio:** $\hat{\text{SE}}_{\text{boot}} / \hat{\text{SE}}_{\text{asymp}}$, quantifying SE underestimation

### 4.6.3 Heterogeneity Diagnostics

For OULAD per-cluster analysis:

- **Effect range:** $[\min_s \hat{\tau}_s, \max_s \hat{\tau}_s]$
- **Sign disagreement:** Proportion of clusters with sign opposite to aggregate
- **Significance count:** Number of clusters with 95% CI not containing zero
- **Cluster effect SD:** $\sqrt{\sum_s (\hat{\tau}_s - \bar{\tau})^2 / (L-1)}$

### 4.6.4 Sensitivity Diagnostics

- **$\psi$ sensitivity range:** $[\min_\psi \hat{\tau}(\psi), \max_\psi \hat{\tau}(\psi)]$
- **$\psi$ sign robustness:** Whether $\text{sign}(\hat{\tau}(\psi))$ is constant across grid
- **$\Gamma$ break point:** Smallest $\Gamma$ for which sensitivity bounds cross zero
- **Robustness verdict:** $\Gamma_{\text{break}} > 2.0$ "qualitatively robust"; $1.5 < \Gamma_{\text{break}} \leq 2.0$ "moderately robust"; $\Gamma_{\text{break}} \leq 1.5$ "fragile"

## 4.7 Reproducibility

All experiments are fully reproducible. The implementation is released as open-source Python code with:

- **Random seed control:** All stochastic operations use fixed seeds
- **Configuration documentation:** All hyperparameters explicitly stated
- **Data loading pipelines:** Standardized loaders with version-controlled preprocessing
- **Diagnostic logging:** All runs produce diagnostic outputs alongside point estimates

The complete reproducibility package includes 29 Python files totaling approximately 8,500 lines of code, organized into modules for estimators, data loaders, scripts, and theory documentation.

---
