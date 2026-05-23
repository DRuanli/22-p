# 1. Introduction

## 1.1 Motivation

Artificial intelligence systems are increasingly deployed in high-stakes educational decisions: predicting student dropout risk, automating grading, allocating scholarships, recommending personalized learning paths, and supporting admissions decisions. These systems impact millions of learners across primary, secondary, and tertiary education globally. The U.S. Department of Education reported in 2023 that over 60% of higher education institutions use AI-based decision support for at least one student-facing process, while the European Commission's 2024 Digital Education Action Plan identifies AI-driven personalization as a strategic priority.

This widespread adoption raises fundamental concerns about algorithmic fairness. Empirical audits have repeatedly documented bias in educational AI systems: predictive analytics tools systematically under-predict performance for underrepresented minority students (Yu et al., 2020); automated essay scoring exhibits gender bias (Loukina et al., 2019); facial recognition for online proctoring fails disproportionately for darker skin tones (Buolamwini and Gebru, 2018, with subsequent education-specific replications). The consequences of unaddressed bias are not merely technical inconveniences but materially impact educational opportunities, lifetime earnings, and social mobility.

Regulatory frameworks have responded to these concerns. The European Union's AI Act, with provisions on high-risk educational AI taking full effect in August 2026, mandates fairness audits with documented causal pathways of bias. Article 10 of the EU AI Act specifically requires "examination of possible biases that are likely to affect the health and safety of natural persons or lead to discrimination," with particular emphasis on understanding the causal mechanisms through which such biases arise. Similar regulatory developments are emerging in the United States (Department of Education guidance, 2024), the United Kingdom (Office for Students AI principles, 2024), and several Asian jurisdictions.

Despite this regulatory urgency, the technical methodology for conducting rigorous fairness audits of educational AI faces two critical limitations that this paper addresses.

## 1.2 Two Critical Gaps in Existing Methodology

### 1.2.1 Gap 1: Aggregate Fairness Metrics Conflate Discriminatory and Legitimate Pathways

Counterfactual fairness (Kusner et al., 2017), one of the most influential causal fairness frameworks, evaluates whether predictions would differ if an individual's protected attribute were counterfactually changed while holding their "true" characteristics fixed. While conceptually appealing, this approach treats fairness as a single number, conflating two fundamentally different sources of disparity:

- **Direct discrimination**: causal pathways from protected attributes to outcomes that operate through unjustified mechanisms (e.g., evaluator bias)
- **Mediated effects through legitimate factors**: pathways operating through variables that society may consider acceptable bases for differential treatment (e.g., prior academic performance reflecting genuine differences in preparation)

Consider a concrete example. A university's admissions algorithm may show higher acceptance rates for one gender group. Total counterfactual fairness would aggregate all causal mechanisms into a single estimate. However, policy implications differ dramatically depending on whether the disparity operates through:

- **Path 1 (direct):** Algorithm's reviewer-mimicking component embeds historical bias against the group → action required: bias mitigation
- **Path 2 (via mediator):** Group differences in prior coursework participation due to upstream factors → action required: addressing upstream educational access

Path-specific counterfactual fairness, formalized by Chiappa (2019), provides a framework to decompose fairness along the causal graph. However, existing implementations rely on variational autoencoders (VAEs) that lack formal asymptotic guarantees and assume independent observations.

### 1.2.2 Gap 2: Hierarchical Data Structure is Pervasive but Methodologically Ignored

Educational data are inherently hierarchical: students are nested within classrooms, classrooms within schools, schools within districts, and cohorts within time periods. The Open University Learning Analytics Dataset (OULAD), one of the canonical benchmarks for educational data mining, contains 32,593 students across 22 module-presentation combinations. The IPEDS database, the U.S. Department of Education's primary higher education repository, includes 7,000+ institutions with millions of student records nested within. The PISA international assessment includes 81 countries with hundreds of schools per country.

This hierarchical structure has profound statistical implications:

1. **Within-cluster correlation:** Students in the same course share unobserved factors (instructor effects, course difficulty, peer composition), violating independence assumptions
2. **Effect heterogeneity:** Fairness effects may differ substantially across clusters; the same protected attribute may have different impacts in STEM versus social science courses
3. **Cluster-level confounding:** Unobserved cluster characteristics may confound individual-level relationships, requiring cluster-aware identification strategies

Critically, the dominant methodological literature on counterfactual fairness assumes IID data. Applying these methods to clustered educational data produces:

- **Biased point estimates** when cluster-level confounding is non-trivial
- **Severely underestimated standard errors** because within-cluster correlation is ignored (we observe SE underestimation by factors of approximately 3.5× to 4× on clustered datasets, with degenerate near-zero asymptotic SE in particular IID configurations)
- **Misleading aggregate conclusions** that mask substantively important heterogeneity

Recent work in causal inference has developed double machine learning (DML) approaches for clustered data (Liu, Liu, and Sasaki, 2024), but these focus on conditional average treatment effects rather than path-specific fairness estimation. The intersection of (a) hierarchical structure, (b) path-specific effects, and (c) practical fairness inference has not been formalized.

## 1.3 Contributions

This paper proposes **Hierarchical Causal Double Machine Learning (HC-DML)** for path-specific counterfactual fairness in clustered educational data. Our contributions are:

**Theoretical contributions:**

1. **Hierarchical identification of path-specific effects** (Theorem 1): We extend the Pearl mediation formula to hierarchical data with cluster-level random effects, providing identification conditions under sequential ignorability with cluster conditioning.

2. **Efficient Influence Function for hierarchical PSE** (Theorem 2): We derive the efficient influence function for natural direct and indirect effects under hierarchical sequential ignorability. This extends the IID results of Tchetgen-Tchetgen and Shpitser (2014) to clustered data with cross-world counterfactual independence.

3. **Asymptotic theory** (Theorems 3–5): We establish $\sqrt{n}$-consistency, asymptotic normality, doubly robust property, and Neyman orthogonality of the resulting estimator, providing principled inference under regularity conditions on nuisance estimation rates.

**Methodological contributions:**

4. **HC-DML algorithm**: A complete estimation procedure combining hierarchical cross-fitting (extending Liu et al. 2024), efficient influence function score computation, and cluster-robust variance estimation. The estimator is doubly robust and achieves the semiparametric efficiency bound.

5. **Pedagogical Justifiability Function ($\psi$)**: A formalization of partial path justifiability that generalizes the binary discriminatory/non-discriminatory dichotomy in prior work, enabling sensitivity analysis over normative assumptions.

6. **Three-level sensitivity analysis framework**: Comprehensive sensitivity to (a) path justifiability assumptions, (b) unobserved confounding via Marginal Sensitivity Model bounds, and (c) DAG specification choices.

7. **Practical implementation guidance**: Diagnostic tools and empirical recommendations for when EIF estimation is appropriate versus when substitution-based estimation with bootstrap inference should be preferred. Specifically, sample size requirements ($n \geq 1000$), density ratio diagnostics, and overlap assessment.

**Empirical contributions:**

8. **Comprehensive validation across five datasets**: Synthetic data generating processes (with known ground truth), UCI Student Performance (Portuguese language), xAPI Educational Mining, Law School Admissions (LSAC), and OULAD. (The UCI Mathematics dataset, $n = 395$, was excluded from main analyses because it falls below the recommended sample-size threshold for EIF-based estimation; see Section 6.3.3.)

9. **Heterogeneity of fairness effects across OULAD modules**: We document substantial and statistically significant cluster-level heterogeneity in gender effects across 22 OULAD modules. Cochran's Q test rejects effect homogeneity at $p = 4.06 \times 10^{-7}$ (I² = 70%), with one module (CCC_2014J, $\hat{\tau} = +0.146$) reaching strong significance after Benjamini-Hochberg multiple-testing correction ($p_{\text{BH}} \approx 10^{-11}$). Cluster-specific point estimates span $-0.064$ to $+0.146$ across the 22 modules, with the aggregate marginal estimate ($\tau = +0.076$) entirely masking this heterogeneity. This finding has not previously been documented in the educational fairness literature with rigorous causal inference.

10. **Direct/indirect effect suppression**: We demonstrate that in OULAD, the natural direct effect (NDE = +0.230) and natural indirect effect (NIE = -0.154) operate in opposing directions and partially cancel in the aggregate measure. This has important policy implications: interventions must address each pathway separately rather than relying on aggregate metrics.

11. **Empirical evidence on substitution estimator SE underestimation**: We document that substitution-based estimators underestimate standard errors by factors of approximately 3.5×–4× on clustered datasets (xAPI, OULAD) and exhibit degenerate near-zero asymptotic SE in particular IID configurations, raising concerns about reported significance in prior literature applying these estimators to clustered or pathological-overlap settings.

## 1.4 Practical and Policy Implications

Our findings have implications beyond the immediate methodological contribution:

**For practitioners conducting fairness audits:**

- Aggregate fairness metrics may produce misleading conclusions when applied to hierarchically structured data. Cluster-level analysis should be standard practice for educational AI audits.
- Standard errors reported in causal fairness literature may be substantially underestimated. Bootstrap inference or proper EIF-based variance estimation is essential for honest uncertainty quantification.
- Path-specific decomposition reveals operational structure of bias that informs intervention design.

**For policy and regulation:**

- The EU AI Act's requirement for "examination of possible biases" implicitly demands causal pathway analysis. HC-DML provides one principled approach to meet this requirement.
- Aggregate fairness scores may certify systems as fair when significant cluster-level disparities exist. Regulatory frameworks should consider mandating cluster-level reporting.
- Sensitivity analysis to unobserved confounding provides interpretable robustness measures (the $\Gamma$ break point) that translate to policy-relevant statements: "this conclusion holds unless hidden confounding shifts treatment odds by more than $X$-fold."

**For the AIED, learning analytics, and fairness ML communities:**

- The OULAD heterogeneity finding suggests that existing single-number fairness audits may be insufficient for clustered educational data.
- The methodological pipeline (open-source Python implementation) lowers the barrier for rigorous causal fairness analysis in education.
- The pedagogical justifiability function provides a vocabulary for engaging domain experts in normative discussions about which causal paths constitute discrimination.

## 1.5 Paper Organization

The remainder of this paper is organized as follows. Section 2 reviews related work in causal fairness, hierarchical causal inference, and double machine learning, positioning our contribution against prior literature. Section 3 develops the methodology, including identification (Theorem 1), the efficient influence function derivation (Theorem 2), the HC-DML algorithm, asymptotic theory (Theorems 3–5), bootstrap inference, and the three-level sensitivity analysis framework. Section 4 describes the experimental setup including data generating processes, real-world datasets, baseline comparators, and evaluation metrics. Section 5 presents results: synthetic validation establishing consistency and efficient inference; cross-dataset comparisons revealing systematic patterns in substitution versus EIF estimation; the per-module OULAD heterogeneity analysis as our primary empirical finding; sensitivity analysis demonstrating robustness patterns. Section 6 discusses limitations including small-sample regimes, density ratio estimation challenges, and the cross-world identification assumption that remains untestable. Section 7 concludes with implications for fairness audits, regulatory compliance, and future research directions.

---

# 2. Related Work

This section reviews three streams of literature that converge in our contribution: (i) counterfactual fairness and path-specific approaches, (ii) hierarchical and clustered causal inference, and (iii) double machine learning. We then position our work and articulate distinctions from the most closely related papers.

## 2.1 Counterfactual Fairness and Path-Specific Approaches

### 2.1.1 Foundations: Counterfactual Fairness

Kusner et al. (2017) introduced counterfactual fairness as the requirement that a predictor's outcome for an individual should not change under a counterfactual change in their protected attribute, holding other "non-descendants" of the protected attribute fixed. Formally, a predictor $\hat{Y}$ is counterfactually fair if:

$$
\mathbb{P}(\hat{Y}_{A=a}(U) = y \mid X = x, A = a) = \mathbb{P}(\hat{Y}_{A=a'}(U) = y \mid X = x, A = a)
$$

for all $y, x, a, a'$. This framework grounds fairness in Pearl's structural causal models (Pearl, 2009), providing a principled alternative to observational fairness criteria such as demographic parity and equal opportunity (Hardt et al., 2016).

The conceptual elegance of counterfactual fairness has driven substantial follow-up work. Russell et al. (2017) propose multi-world counterfactual fairness allowing for multiple causal models. Wu et al. (2019) extend the framework to address measurement error in protected attributes. Garg et al. (2019) consider counterfactual fairness in text classification contexts.

However, the original Kusner et al. (2017) framework operates on total effects, which conflates multiple causal pathways. This limitation motivated path-specific extensions.

### 2.1.2 Path-Specific Counterfactual Fairness

Path-specific effects (Avin, Shpitser, and Pearl, 2005) provide the foundation for fine-grained causal analysis. The natural direct effect (NDE) captures the effect of treatment that does not operate through specified mediators, while the natural indirect effect (NIE) captures the effect through mediators.

Chiappa (2019) extends counterfactual fairness to a path-specific framework, distinguishing fair paths (along which differential treatment is acceptable) from unfair paths. The implementation uses variational autoencoders (VAEs) to learn latent representations capturing legitimate variation, combined with maximum mean discrepancy (MMD) constraints to enforce fairness along unfair paths. While conceptually rigorous, this approach has limitations:

1. **No formal asymptotic guarantees:** VAE-based estimation lacks $\sqrt{n}$-consistency results applicable to fairness audits
2. **IID assumption:** Method does not address hierarchical data structure
3. **Implementation complexity:** Practitioners require deep learning expertise; replication is non-trivial
4. **Sensitivity analysis absent:** No principled framework for assessing robustness to assumptions

Nabi et al. (2024) develop fair risk minimization with path-specific effects, focusing on training fair predictors rather than auditing existing systems. Their approach also assumes IID data.

Schröder, Frauen, and Feuerriegel (2024) provide sensitivity analysis for counterfactual fairness under unobserved confounding, using a neural sensitivity model. Their framework addresses total effects in IID settings; we extend their conceptual approach to path-specific effects in hierarchical settings.

### 2.1.3 Causal Fairness Frameworks

Plečko and Bareinboim (2024) develop a comprehensive causal fairness analysis framework integrating identification, estimation, and bias decomposition. Their decomposition formulas distinguish direct, indirect, and spurious effects, providing a vocabulary for discussing fairness violations. Our work complements this framework by providing efficient inference theory and explicit handling of hierarchical data.

Nilforoshan et al. (2022) demonstrate fundamental tensions between causal fairness criteria, showing that no single criterion can simultaneously satisfy all desirable properties. This motivates the user-specified justifiability function $\psi$ in our framework, which makes normative choices transparent rather than imposing them implicitly.

### 2.1.4 Fairness in Education Specifically

Several recent papers address fairness in educational AI specifically. Anderson et al. (2019) audit dropout prediction models for racial bias. Kizilcec and Lee (2022) provide a fairness assessment framework for MOOCs. Yu et al. (2020) document predictive performance disparities in postsecondary success prediction. Loukina et al. (2019) examine bias in automated essay scoring.

Most existing educational fairness audits use observational metrics (demographic parity, equal opportunity) rather than causal frameworks. The few causal analyses (e.g., Pang et al., 2023) apply IID counterfactual fairness directly, without addressing hierarchical structure. Our work extends rigorous causal fairness specifically to the clustered educational setting.

## 2.2 Hierarchical and Clustered Causal Inference

### 2.2.1 Classical Multilevel Models

Hierarchical data analysis has a long tradition in education, with multilevel/hierarchical linear models being a methodological mainstay (Raudenbush and Bryk, 2002; Snijders and Bosker, 2012). These models account for within-cluster correlation through random effects but operate within a parametric framework, requiring strong functional form assumptions and offering limited robustness.

For causal effect estimation specifically, Hong and Raudenbush (2006) consider treatment effects in multilevel settings using propensity score methods. Steiner et al. (2015) develop matching estimators for clustered data. These approaches address total causal effects but not path-specific decomposition.

### 2.2.2 Modern Cluster-Robust Inference

Cameron, Gelbach, and Miller (2008, 2011) provide foundational work on cluster-robust standard errors. The cluster sandwich estimator $\hat{V} = (X'X)^{-1} (\sum_s X_s' e_s e_s' X_s)(X'X)^{-1}$ accounts for within-cluster correlation in regression-style inference. For small numbers of clusters ($L < 30$), they recommend wild cluster bootstrap, which we incorporate as an optional procedure.

The cluster CLT establishes that under appropriate conditions ($L \to \infty$, $\max_s n_s / n \to 0$), cluster-robust inference is valid. This theoretical foundation underlies our cluster-robust variance estimator (Section 3.3.5).

### 2.2.3 Hierarchical Causal Mediation

The literature on causal mediation in hierarchical settings is sparse. Bauer et al. (2006) discuss multilevel mediation models in psychology. Talloen et al. (2024) provide a recent review of multilevel mediation analysis. However, these papers operate within parametric multilevel frameworks rather than the semiparametric/machine-learning paradigm we adopt.

Liu, Liu, and Sasaki (2024) develop multi-way clustered double machine learning for conditional average treatment effects (CATE). They establish $\sqrt{n}$-consistency and provide cross-fitting procedures accounting for cluster structure. Our work directly extends their multi-way clustered cross-fitting approach from CATE to path-specific fairness estimation. The key technical novelty in our paper is the EIF derivation for path-specific effects in this clustered setting.

## 2.3 Double Machine Learning

### 2.3.1 Foundations

Chernozhukov et al. (2018) develop the double/debiased machine learning (DML) framework for estimating treatment effects with high-dimensional or non-parametric nuisance functions. The framework's key ideas are:

1. **Neyman orthogonality**: Score functions are designed such that first-order errors in nuisance estimation do not contaminate the target estimate
2. **Cross-fitting**: Sample splitting prevents own-observation bias from flexible nuisance estimation
3. **Doubly robust property**: Estimators remain consistent if either outcome or treatment nuisance models are correctly specified

DML has been extended in numerous directions, including local effects (Foster and Syrgkanis, 2019), instrumental variables (Singh and Sun, 2019), and continuous treatments (Colangelo and Lee, 2020).

### 2.3.2 DML for Causal Mediation

Farbmacher et al. (2022) develop DML estimators for natural direct and indirect effects in IID settings. Their approach uses cross-fitting with three nuisance functions (outcome regression, propensity score, mediator density) but does not address clustered data. Hines, Vansteelandt, and Diaz-Ordaz (2022) provide similar IID DML mediation results with extensions to time-varying mediators.

Our work extends DML mediation estimation to the hierarchical setting with proper cluster-level conditioning and cluster-robust inference. The EIF in our Theorem 2 reduces to the IID mediation EIF of Tchetgen-Tchetgen and Shpitser (2014) when $L = 1$.

### 2.3.3 DML for Fairness

Recent work applies DML to fairness estimation. Bia et al. (2023) use DML for total effect decomposition in fairness contexts. Plečko and Bareinboim (2024) employ DML estimators in their causal fairness pipeline. However, these works assume IID observations.

## 2.4 Sensitivity Analysis for Causal Inference

### 2.4.1 Marginal Sensitivity Model

Tan (2006) introduces the Marginal Sensitivity Model (MSM) for evaluating robustness of causal estimates to unobserved confounding. The model bounds the odds ratio between observed and true (latent) propensity scores by a sensitivity parameter $\Gamma$. Zhao, Small, and Bhattacharya (2019) develop sharp bounds for IPW estimators under MSM.

Yadlowsky et al. (2022) extend MSM to outcome regression settings. Dorn and Guo (2023) provide alternative formulations using the Rosenbaum (1987) framework. Recent work by Schröder et al. (2024) employs neural networks for sensitivity analysis of total counterfactual fairness.

### 2.4.2 Sensitivity for Mediation

Tchetgen-Tchetgen and Shpitser (2014, Section 5) discuss sensitivity analysis for IID mediation effects, focusing on violations of the cross-world independence assumption. VanderWeele (2010) provides sensitivity bounds for mediation under unmeasured mediator-outcome confounding.

Our work extends the MSM to path-specific effects in clustered data (Section 3.6.2). The bounds we derive are obtained by simultaneously worst-casing propensity and density ratio components, which may be conservative. Deriving tighter bounds exploiting the path-specific structure remains an open question for future work.

## 2.5 Positioning and Distinctions

We summarize the relationship between this paper and the most closely related work:

| Reference | Path-specific | Hierarchical | Efficient IF | Sensitivity | Educational application |
|-----------|--------------|--------------|--------------|-------------|------------------------|
| Kusner et al. (2017) | No (total) | No | No | No | General |
| Chiappa (2019) | Yes | No | No | No | General |
| Liu et al. (2024) | No (CATE) | Yes | Yes | No | General |
| Farbmacher et al. (2022) | Yes | No | Yes | Limited | General |
| Plečko & Bareinboim (2024) | Yes | No | Yes | No | General |
| Schröder et al. (2024) | No (total) | No | Yes | Yes (neural) | General |
| **This paper** | **Yes** | **Yes** | **Yes** | **Yes (MSM)** | **Yes (5 datasets)** |

Three key distinctions:

**Distinction 1 (vs. Chiappa 2019).** We provide formal asymptotic theory (√n-consistency, efficiency bounds, doubly robust property) and handle clustered data. Our approach is also computationally more tractable than VAE-based methods.

**Distinction 2 (vs. Liu et al. 2024).** While we adopt their multi-way clustered cross-fitting approach, we extend from conditional average treatment effects (a single target) to path-specific effects (requiring decomposition across three counterfactual quantities $\theta_{00}, \theta_{10}, \theta_{11}$ with cross-world identification). The EIF derivation for path-specific effects in clustered data (Theorem 2) is novel.

**Distinction 3 (vs. Schröder et al. 2024).** They provide neural sensitivity analysis for total counterfactual fairness in IID settings. We provide closed-form MSM bounds for path-specific effects in clustered settings, applicable directly to standard DML output without additional neural network training. This is significantly simpler to implement and interpret.

**Empirical novelty.** To our knowledge, this is the first paper to document statistically significant fairness heterogeneity across course modules in OULAD with rigorous causal inference. While prior work has analyzed OULAD for fairness (e.g., Riazy et al., 2020, using observational metrics), the cluster-level path-specific analysis with confidence intervals and sensitivity bounds is unique to our contribution.

---
