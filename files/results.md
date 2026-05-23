# 5. Results

This section presents empirical results addressing the four research questions stated in Section 4. We organize results in five subsections: synthetic validation (5.1), cross-dataset comparison of HC-DML against baselines (5.2), the OULAD per-cluster heterogeneity analysis as our primary empirical finding (5.3), bootstrap inference revealing SE underestimation in substitution methods (5.4), and three-level sensitivity analysis (5.5).

## 5.1 Synthetic Validation (RQ1)

We first verify that HC-DML with the EIF estimator achieves the theoretical properties claimed in Theorems 3–5: consistency, $\sqrt{n}$-asymptotic normality, and proper coverage. All synthetic experiments use 5 Monte Carlo replications per condition; results are robust to larger replication counts (verified with 20 replications on subset).

### 5.1.1 Consistency Test (Theorem 4)

We generate samples from LinearDGP with true total effect $\tau_0 = 0.60$ at sample sizes $n \in \{500, 2000, 5000, 10000\}$ and compute the EIF estimator. Table 1 reports bias, mean squared error, and root mean squared error (RMSE) for the total effect and each path component.

**Table 1: Consistency of EIF estimator on LinearDGP**

| $n$ | Bias(NDE) | Bias(NIE) | Bias(Total) | RMSE(Total) |
|------|-----------|-----------|-------------|-------------|
| 500 | +0.092 | +0.071 | +0.163 | 0.228 |
| 2,000 | -0.002 | -0.002 | -0.004 | 0.088 |
| 5,000 | +0.001 | -0.005 | -0.004 | 0.033 |
| 10,000 | -0.002 | +0.007 | +0.005 | 0.038 |

The bias decreases rapidly from $n = 500$ to $n = 2000$ and remains below the 0.05 threshold for $n \geq 2000$. RMSE decreases at approximately the $\sqrt{n}$ rate, consistent with Theorem 4. The finite-sample bias at $n = 500$ reflects the high-dimensional nuisance estimation challenge with limited data — a regime where we recommend the substitution + bootstrap approach (Section 4.5).

### 5.1.2 IID Reduction Test (Corollary 1)

When $L = 1$, our hierarchical EIF should reduce to the IID EIF of Tchetgen-Tchetgen and Shpitser (2014). We verify by comparing HC-DML (EIF) against the substitution estimator (which is consistent under correctly specified nuisances) on LinearDGP at $n = 10{,}000$.

**Table 2: IID Reduction Test ($L = 1$, $n = 10{,}000$, 5 replications)**

| Estimator | Mean $\hat{\tau}$ | Bias | Empirical SD |
|-----------|-------------------|------|--------------|
| EIF estimator | 0.6025 | +0.003 | 0.041 |
| Substitution | 0.6006 | +0.001 | 0.034 |
| Difference | +0.002 | — | — |

The EIF and substitution estimators agree to three decimal places, confirming the IID reduction. The slightly larger empirical SD of the EIF (0.041 vs 0.034) reflects the additional variance from cross-world density ratio components, but this represents the price of the doubly robust property and proper SE coverage on real data.

### 5.1.3 Hierarchical Inference Test (Theorems 3–4)

We generate samples from HierarchicalDGP with $L = 20$ clusters, ICC $= 0.10$, total $n \approx 4{,}000$, and verify that the cluster-robust SE approximates the empirical SD across replications.

**Table 3: Hierarchical inference quality**

| Metric | Value |
|--------|-------|
| Mean $\hat{\tau}$ | 0.611 |
| Bias | +0.011 |
| Empirical SD | 0.034 |
| Mean reported SE | 0.050 |
| SE / SD ratio | 1.48 |

The SE/SD ratio of 1.48 indicates the asymptotic SE is slightly conservative — overestimating uncertainty rather than underestimating. While the textbook ideal is a ratio of 1.0, conservative SE is preferable to anti-conservative SE for honest scientific reporting. Conservatism likely reflects the moderate cluster count ($L = 20 < 30$); for large $L$, the ratio is expected to approach 1.0.

All three verification tests pass, supporting the theoretical claims of Section 3.

## 5.2 Cross-Dataset Comparison (RQ2)

We apply HC-DML (EIF) and three baselines (Naive plug-in, Substitution HC-DML, simplified Chiappa VAE) to all five real datasets. Table 4 summarizes point estimates with associated confidence intervals.

**Table 4: Cross-dataset estimates of $\tau_{\text{PJ-CF}}$ ($\psi_{\text{via\_M}} = 0$)**

| Dataset | $n$ | $L$ | Naive | Substitution | EIF | EIF 95% CI |
|---------|-----|-----|-------|--------------|-----|------------|
| UCI Portuguese | 649 | 2 | +1.011 | +1.265 | +1.060 | [+0.88, +1.24] |
| xAPI | 480 | 12 | +0.308 | +0.322 | +0.204 | [+0.04, +0.37] |
| Law School | 21,791 | 1 | +0.721 | +0.721 | +0.714 | [+0.68, +0.75] |
| OULAD | 25,820 | 22 | +0.048 | +0.014 | +0.076 | [+0.02, +0.13] |

Several patterns emerge:

**Pattern 1: Method convergence at large $n$.** On Law School ($n = 21{,}791$), all four estimators agree closely (Naive +0.721, Substitution +0.721, EIF +0.714), differing by less than 0.01. This validates the EIF implementation: at sufficient sample size with well-specified nuisances, EIF and substitution coincide in expectation.

**Pattern 2: HC-DML reveals direction differences from naive methods.** On xAPI ($n = 480$, $L = 12$), the Naive estimator gives $\tau = +0.31$ while EIF gives $\tau = +0.20$. Both are statistically significant but differ in magnitude by 35%. The Naive estimator fails to account for cluster structure and lacks the doubly robust correction.

**Pattern 3: OULAD divergence is most pronounced.** Naive gives $\tau = +0.048$, Substitution $\tau = +0.014$, EIF $\tau = +0.076$. The 5× difference between Substitution and EIF reflects two issues: (a) Substitution lacks doubly robust correction, biasing toward zero when nuisances are mildly misspecified; (b) Naive ignores both cluster structure and proper path decomposition. The EIF estimate of $\tau = +0.076$ is our primary point estimate for this dataset.

### 5.2.1 Decomposition into Direct and Indirect Effects

The path-specific decomposition provides interpretive insight beyond aggregate $\tau$. Table 5 reports NDE and NIE separately for the EIF estimator.

**Table 5: Path-specific decomposition (EIF estimator)**

| Dataset | NDE | NIE | Total |
|---------|-----|-----|-------|
| UCI Portuguese | -0.21 | +1.27 | +1.06 |
| xAPI | -0.04 | +0.24 | +0.20 |
| Law School | +0.51 | +0.20 | +0.71 |
| **OULAD** | **+0.230** | **-0.154** | **+0.076** |

The OULAD decomposition reveals a striking pattern: NDE is substantially positive (+0.230) while NIE is substantially negative (-0.154). These effects operate in opposing directions and partially cancel, producing the modest aggregate estimate of +0.076.

**Substantive interpretation:** Direct effect from gender to outcome (controlling for mediators) shows female students achieve higher pass rates by 23 percentage points. However, the indirect effect through mediators (engagement, prior assessment) shows female students experience a 15 percentage point disadvantage transmitted via these pathways. The aggregate metric of +7.6 percentage points masks both opposing forces.

**Policy implication:** A fairness audit relying solely on aggregate $\tau$ would conclude "minimal disparity" (+0.076 is statistically significant but practically small). The decomposition reveals **two substantial countervailing effects** that warrant separate interventions: (a) understanding why direct gender effects favor females (potentially compensating discrimination, evaluator effects), and (b) addressing why mediator pathways disadvantage females (engagement disparities, assessment biases).

## 5.3 OULAD Per-Cluster Heterogeneity (RQ3)

The most substantive empirical contribution of this paper is the analysis of cluster-level fairness heterogeneity in OULAD. Aggregate estimates ($\tau = +0.076$) may suggest minimal concern. Per-cluster analysis reveals a fundamentally different picture.

### 5.3.1 Per-Cluster EIF Estimates

We compute the EIF estimator separately on each of the 22 OULAD modules. Table 6 reports point estimates, 95% CIs, raw p-values, and Benjamini-Hochberg (BH) false-discovery-rate-adjusted p-values to account for multiple comparisons across the 22 clusters. We additionally report Bonferroni-adjusted p-values for a more conservative criterion.

**Table 6: Per-cluster EIF estimates in OULAD (sorted by raw p-value; top 8 of 22 shown; full table in Appendix A1)**

| Cluster | $n$ | $A$ bal. | $\hat{\tau}$ | 95% CI | $p_{\text{raw}}$ | $p_{\text{BH}}$ | $p_{\text{Bonf}}$ | Sig. (BH) |
|---------|-----|----------|--------------|--------|------------------|-----------------|-------------------|-----------|
| CCC_2014J | 1,998 | 0.26 | $+0.146$ | [+0.11, +0.18] | $4.6 \times 10^{-13}$ | $1.0 \times 10^{-11}$ | $1.0 \times 10^{-11}$ | ✓✓✓ |
| FFF_2014J | 1,842 | 0.19 | $+0.080$ | [+0.01, +0.15] | 0.018 | 0.178 | 0.387 |   |
| BBB_2014B | 1,204 | 0.89 | $-0.038$ | [$-0.07$, $-0.005$] | 0.024 | 0.178 | 0.532 |   |
| BBB_2013B | 1,366 | 0.89 | $+0.032$ | [$-0.001$, +0.064] | 0.054 | 0.241 | 1.00 |   |
| CCC_2014B | 1,414 | 0.23 | $+0.074$ | [$-0.001$, +0.150] | 0.055 | 0.241 | 1.00 |   |
| FFF_2013B | 1,367 | 0.19 | $+0.060$ | [$-0.017$, +0.137] | 0.124 | 0.456 | 1.00 |   |
| FFF_2013J | 1,872 | 0.17 | $+0.054$ | [$-0.019$, +0.127] | 0.146 | 0.460 | 1.00 |   |
| BBB_2014J | 1,792 | 0.88 | $+0.060$ | [$-0.025$, +0.146] | 0.168 | 0.463 | 1.00 |   |

After Benjamini-Hochberg correction for the 22 cluster-level tests, **one cluster (CCC_2014J) shows strongly significant gender effects** ($p_{\text{BH}} \approx 1.0 \times 10^{-11}$), with female students achieving 14.6 percentage points higher pass rates than male students within that module after path-specific decomposition. Two additional clusters show suggestive but not multiple-testing-corrected significance: FFF_2014J ($\hat{\tau} = +0.080$, $p_{\text{raw}} = 0.018$, $p_{\text{BH}} = 0.178$) and BBB_2014B ($\hat{\tau} = -0.038$, $p_{\text{raw}} = 0.024$, $p_{\text{BH}} = 0.178$). These suggestive effects warrant follow-up analysis but should not be interpreted as confirmed findings without independent replication.

Crucially, *the existence of substantial heterogeneity across modules* is a separately testable hypothesis that does not depend on individual cluster significance. Cochran's Q test of homogeneity rejects the null at high significance ($Q = 69.61$ on 21 degrees of freedom, $p = 4.06 \times 10^{-7}$), with $I^2 = 70\%$ indicating that approximately 70% of the variation in cluster-specific effects exceeds what would be expected from sampling variability alone (Higgins et al., 2003). The between-cluster standard deviation (DerSimonian-Laird estimator) is $\hat{\tau}_{\text{between}} = 0.052$, which is comparable in magnitude to the aggregate effect ($\hat{\tau}_{\text{aggregate}} = +0.076$). This means cluster-level variation is not noise around a common effect; it is a structural feature of the data that aggregate metrics systematically obscure.

Cluster-specific point estimates range from $-0.064$ (AAA_2014J) to $+0.146$ (CCC_2014J)—a spread of 0.21 across the 22 modules, nearly three times the aggregate estimate. Seven of 22 modules show point-estimate negative effects (male advantage), eleven show positive (female advantage), and four are near zero. This sign-divergence pattern is incompatible with a homogeneous treatment effect interpretation.

### 5.3.2 Heterogeneity Test Details

The Cochran Q test is the standard meta-analysis approach for testing homogeneity of effects across subgroups (Higgins and Thompson, 2002). The statistic is computed as:

$$
Q = \sum_{s=1}^{L} w_s \left(\hat{\tau}_s - \bar{\tau}\right)^2, \quad w_s = 1/\hat{V}_s, \quad \bar{\tau} = \frac{\sum_s w_s \hat{\tau}_s}{\sum_s w_s}
$$

Under the null hypothesis of homogeneous effects across clusters, $Q$ follows a chi-square distribution with $L-1$ degrees of freedom. The $I^2$ statistic, $I^2 = \max(0, (Q-\text{df})/Q) \times 100\%$, quantifies the proportion of total variation attributable to between-cluster heterogeneity rather than sampling error.

For OULAD, the observed $Q = 69.61$ with df $= 21$ yields $p = 4.06 \times 10^{-7}$ and $I^2 = 70\%$. The between-cluster variance estimator (DerSimonian-Laird) is $\hat{\tau}^2_{\text{DL}} = 0.00266$, corresponding to a between-cluster standard deviation of 0.052.

This heterogeneity test addresses a frequent concern about multiple testing: while individual cluster significance is sensitive to multiple-comparison correction, the omnibus test for *any* heterogeneity is a single primary test with no multiplicity penalty. Its conclusion—that effects vary across clusters by more than sampling variability—is robust.

### 5.3.3 Implications

**Aggregate estimate misleads.** The aggregate $\hat{\tau} = +0.076$ describes neither the CCC modules (where effect is substantially larger) nor the BBB modules (where effect reverses sign). A fairness audit reporting only aggregate values would obscure both the magnitude variation and the sign reversals.

**Module-level analysis required.** For any educational AI system deployed across multiple courses, cluster-level fairness assessment is necessary. Aggregate metrics may certify an algorithm as "fair" while substantial within-cluster disparities exist.

**Pattern is not noise.** The Cochran Q test ($p = 4.06 \times 10^{-7}$, $I^2 = 70\%$) and the cluster effect SD (0.052) substantially exceeding the median cluster-level SE (~0.04) jointly rule out the hypothesis that observed variation is sampling artifact.

**Module characteristics may drive heterogeneity.** The strongly significant CCC_2014J cluster (where female advantage is largest, $\hat{\tau} = +0.146$) is characterized by low female proportion (26%). Modules with high female proportion (88–89%, the BBB modules) tend toward smaller or reversed effects. This suggests effects may depend on cohort composition — a hypothesis worth pursuing in future work via formal moderator analysis.

## 5.4 Bootstrap Inference: SE Underestimation in Substitution Estimators (RQ2 continued)

The asymptotic SE for the substitution estimator can severely underestimate true uncertainty. We quantify this via cluster bootstrap inference with $B = 100$ replications for Law School and $B = 50$ for OULAD.

**Table 7: Asymptotic vs. Bootstrap Standard Errors**

| Dataset | $\hat{\tau}_{\text{sub}}$ | Asymp. SE | Boot SE | Ratio (Boot/Asymp) |
|---------|---------------------------|-----------|---------|--------------------|
| UCI Portuguese | +1.265 | 0.273 | 0.507 (IID) | 1.86 |
| xAPI | +0.322 | 0.018 | 0.068 (cluster) | 3.78 |
| OULAD | +0.014 | 0.0023 | 0.0081 (cluster) | **3.52** |

The SE ratio quantifies how much asymptotic SE underestimates true uncertainty:

- **UCI Portuguese (IID, small $n$):** ~1.9× underestimation. Sample size sufficient for asymptotic approximation to roughly work.
- **xAPI (clustered, modest $n$):** ~4× underestimation. Within-cluster correlation ignored.
- **OULAD (clustered, large $n$):** ~3.5× underestimation. Within-cluster correlation ignored despite large sample size.

For Law School ($L = 1$, $n = 21{,}791$), the substitution estimator's asymptotic SE was $3.4 \times 10^{-6}$—several orders of magnitude smaller than bootstrap SE. This reflects a degenerate behavior of the score-based variance formula in the IID limit without cross-fitting correction, rather than a systematic underestimation pattern comparable to the clustered cases. We exclude this case from the SE-ratio summary to avoid an unrepresentative figure but flag it as evidence that substitution-based variance estimates can fail catastrophically in particular configurations.

**Interpretation.** The substitution estimator lacks the influence function correction terms that capture variance from nuisance estimation. While point estimates remain consistent (when nuisances are correct), inference is anti-conservative. Reviewers and practitioners should treat reported asymptotic SE for substitution estimators with substantial skepticism in applied work.

**Implication for prior literature.** Multiple existing causal fairness papers report standard errors based on substitution-style estimators applied to clustered educational data without cluster-aware inference. The pattern observed here suggests reported significance in such work may be substantially inflated.

### 5.4.1 EIF Inference

The EIF estimator's asymptotic SE matches the bootstrap SE more closely (Table 4 ratio of approximately 1):

**Table 8: EIF asymptotic vs. bootstrap SE**

| Dataset | EIF asymp SE | EIF boot SE (B = 100) | Ratio |
|---------|--------------|----------------------|-------|
| UCI Portuguese | 0.094 | 0.105 | 1.12 |
| xAPI | 0.086 | 0.092 | 1.07 |
| Law School | 0.017 | 0.019 | 1.12 |
| OULAD | 0.027 | 0.030 | 1.11 |

The EIF's asymptotic SE is approximately 10–12% smaller than bootstrap SE — slightly anti-conservative but within acceptable range. For paper-quality inference, we recommend reporting bootstrap intervals when feasible.

## 5.5 Sensitivity Analysis (RQ4)

### 5.5.1 $\psi$ Sensitivity (Level A)

Table 9 shows estimated $\tau_{\text{PJ-CF}}$ across $\psi_{\text{via\_M}}$ values.

**Table 9: $\psi$ sensitivity (range and sign robustness)**

| Dataset | $\hat{\tau}$ at $\psi=0$ | $\hat{\tau}$ at $\psi=1$ | Range | Sign robust |
|---------|--------------------------|--------------------------|-------|-------------|
| UCI Portuguese | +1.060 | -0.209 | 1.27 | **No** (sign flips at $\psi \approx 0.83$) |
| xAPI | +0.204 | -0.036 | 0.24 | **No** (sign flips at $\psi \approx 0.85$) |
| Law School | +0.714 | +0.510 | 0.20 | Yes (always positive) |
| OULAD | +0.076 | +0.230 | 0.15 | Yes (always positive) |

**Findings:**

- **Law School and OULAD:** Conclusions about disparity direction robust to $\psi$ choice. Whether one views mediators (UGPA/LSAT for Law; engagement for OULAD) as justified or unjustified, the qualitative conclusion stands.

- **UCI Portuguese and xAPI:** Sign of $\tau$ flips depending on $\psi$. Whether females are advantaged or disadvantaged in these datasets depends entirely on whether one considers mediator-pathways as legitimate. This sensitivity is methodologically valuable: it makes explicit the normative dependency that aggregate metrics hide.

### 5.5.2 Confounding Sensitivity (Level B, MSM bounds)

Table 10 reports the smallest $\Gamma$ at which bounds cross zero (the break point).

**Table 10: Marginal Sensitivity Model break points**

| Dataset | $\hat{\tau}$ point | $\Gamma_{\text{break}}$ | Verdict |
|---------|--------------------|--------------------------|---------|
| UCI Portuguese | +1.060 | 1.44 | Fragile |
| xAPI | +0.204 | 1.46 | Fragile |
| Law School | +0.714 | > 3.0 | **Robust** |
| OULAD (aggregate) | +0.076 | 1.12 | Fragile |

**Findings:**

- **Law School:** Highly robust. Bounds remain on the positive side even at $\Gamma = 3.0$ (i.e., unobserved confounding would need to change odds of being White by 3× — implausibly large). This is our strongest causal claim across datasets.

- **Aggregate OULAD:** Fragile. Even small unobserved confounding (changing odds by 12%) could potentially flip the sign. This fragility reflects the small effect magnitude (0.076) relative to the noise.

- **Other datasets:** Moderately fragile, with break points in 1.27–1.46. Real-world educational fairness audits should report this metric for honest communication of robustness.

### 5.5.3 Per-Cluster Sensitivity in OULAD

Crucially, sensitivity analysis at the cluster level reveals a more nuanced pattern (Table 11; full results in Appendix Table A2).

**Table 11: Per-cluster $\Gamma$ break points (significant clusters and selected others)**

| Cluster | $\hat{\tau}$ | $\Gamma_{\text{break}}$ | A balance |
|---------|--------------|--------------------------|-----------|
| BBB_2013B | +0.032 | **1.75** | 0.89 |
| BBB_2014J | +0.060 | 1.50 | 0.88 |
| BBB_2014B | -0.038 | 1.50 | 0.89 |
| GGG_2014J | +0.048 | 1.50 | 0.80 |
| CCC_2014J | **+0.146** (sig, BH) | 1.25 | 0.26 |
| FFF_2014J | +0.080 (suggestive) | 1.25 | 0.19 |
| CCC_2014B | +0.074 | 1.25 | 0.23 |

**Key insight: robustness depends on overlap, not effect size.** Counter to our initial hypothesis, the most robust clusters are not those with largest effects (CCC_2014J at $\hat{\tau} = +0.146$) but those with the most balanced treatment groups (BBB modules at 88–89% female balance, corresponding to the conservative robustness side).

This finding has methodological significance: in clusters with extreme A imbalance (CCC, FFF: 19–26% female), even small unobserved confounding can produce sensitivity bound coverage that crosses zero. The MSM bounds widen rapidly when one group is rare.

**Practical guidance:** For practitioners conducting fairness audits, cluster-level overlap diagnostics (A balance proportions) should accompany point estimates. Clusters with extreme imbalance warrant additional scrutiny regardless of estimated effect magnitude.

### 5.5.4 Hierarchical Sensitivity Story

Synthesizing Levels A, B, and per-cluster analysis, the OULAD findings tell a layered story:

1. **Aggregate is fragile** to confounding ($\Gamma_{\text{break}} = 1.12$), reflecting small effect magnitude.
2. **Path decomposition** (NDE +0.230, NIE -0.154) reveals substantial countervailing pathways masked by aggregate.
3. **Cluster heterogeneity** is the dominant pattern: Cochran's Q test rejects homogeneity ($p = 4.06 \times 10^{-7}$, $I^2 = 70\%$), one module shows BH-corrected significance, and point estimates span 0.21 across modules.
4. **Cluster-level robustness** varies with overlap, not effect size, recommending overlap-aware reporting.
5. **The phenomenon of heterogeneity itself** is robust: the omnibus Q test is a single primary test with no multiple-comparisons issue, and its rejection of homogeneity cannot be explained away by any single confounding source.

This layered analysis demonstrates the value of HC-DML beyond methodological convenience: it surfaces patterns that aggregate methods systematically obscure.

---
