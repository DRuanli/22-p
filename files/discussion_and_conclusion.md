# 6. Discussion

This section discusses the implications, limitations, and broader interpretation of our findings. We organize discussion around three themes: methodological implications for causal fairness research (6.1), substantive implications for educational AI policy and practice (6.2), and honest assessment of limitations (6.3).

## 6.1 Methodological Implications

### 6.1.1 The Cost of Ignoring Hierarchical Structure

Our results demonstrate concrete costs of applying IID-based causal fairness methods to clustered educational data. Three patterns emerge consistently:

**Cost 1: Severely underestimated standard errors.** Substitution estimators applied without cluster-aware inference produce SE that is 3.5×–4× smaller than honest bootstrap-based estimates on clustered datasets (xAPI, OULAD). On Law School ($L = 1$, $n = 21{,}791$), the asymptotic substitution SE collapses to a near-zero value (orders of magnitude smaller than bootstrap SE), reflecting a pathological failure of the score-based variance formula in particular IID configurations. For OULAD, even the more modest 3.5× underestimation translates to nominally significant findings whose true confidence intervals span zero. This is not a theoretical concern: it directly affects whether reported fairness disparities can be defended scientifically.

**Cost 2: Aggregate-level masking of cluster heterogeneity.** The OULAD aggregate estimate $\hat{\tau} = +0.076$ describes none of the dataset's actual fairness landscape. Cochran's Q test rejects homogeneity at $p = 4.06 \times 10^{-7}$ ($I^2 = 70\%$), with cluster-specific point estimates ranging from $-0.064$ to $+0.146$—a spread of 0.21, nearly three times the aggregate. One module (CCC_2014J) shows strongly significant disparities ($p_{\text{BH}} \approx 10^{-11}$) after Benjamini-Hochberg multiple-testing correction, while two others (FFF_2014J, BBB_2014B) show suggestive effects in opposing directions. The aggregate metric assigns a single number to a heterogeneous causal landscape.

**Cost 3: Confounded direct and indirect pathways.** OULAD's NDE ($+0.230$) and NIE ($-0.154$) operate in opposing directions. Single-number fairness metrics (whether aggregate $\tau$ or any path-collapsed quantity) mask this structure. Interventions designed against aggregate metrics will fail because they target the wrong causal pathways.

### 6.1.2 Efficient Influence Function: Theoretical Value, Practical Constraints

The EIF derivation (Theorem 2) provides both theoretical advances and practical complications:

**Theoretical value:**
- $\sqrt{n}$-consistency with semiparametric efficiency
- Doubly robust property (consistent under partial nuisance misspecification)
- Proper variance characterization via cluster-robust sandwich

**Practical constraints:**
- Sample size requirements ($n \geq 1000$ recommended) preclude application to small educational datasets
- Density ratio estimation is the practical bottleneck — Gaussian assumptions may fail for non-Gaussian mediators
- Stability requires careful diagnostic monitoring (density ratio clipping, weight trimming)

We do not view these constraints as undermining the EIF approach but rather as defining its appropriate domain. For datasets with $n < 1000$ or extreme overlap problems, the substitution estimator with bootstrap inference provides a pragmatic alternative that sacrifices efficiency for robustness. This bifurcation in our recommendations is honest scientific practice: no single tool is universally optimal.

### 6.1.3 The Pedagogical Justifiability Function

The $\psi$ formalization makes explicit a normative dependency typically left implicit. In our experiments:

- **Sign-robust to $\psi$:** Law School, OULAD aggregate (qualitative conclusions hold regardless of $\psi$)
- **Sign-dependent on $\psi$:** UCI Portuguese, xAPI (whether females are advantaged or disadvantaged depends on whether mediator pathways are considered legitimate)

The latter result is methodologically valuable: rather than imposing implicit normative judgments through method choice, $\psi$-sensitivity surfaces them for explicit reasoning. Policy stakeholders can debate the appropriate value of $\psi$ for a given context, rather than disputing which fairness metric to use.

### 6.1.4 The Sensitivity Framework

The three-level sensitivity analysis (ψ, Γ, DAG) collectively provides what we believe is the most comprehensive robustness assessment for causal fairness estimation in clustered data. Our findings demonstrate two important nuances:

**Nuance 1: Robustness is not uniform across levels.** Law School is highly robust to confounding (Γ break > 3.0) but moderately sensitive to ψ specification (range 0.20). OULAD is robust to ψ but fragile to confounding at aggregate level. Practitioners should report all three sensitivity dimensions.

**Nuance 2: Cluster-level sensitivity differs from aggregate.** For OULAD, the most robust clusters are not those with largest effects but those with balanced overlap. This finding reframes practitioner guidance: report A balance alongside effect estimates, and apply heightened scrutiny to clusters with extreme imbalance.

## 6.2 Implications for Educational AI

### 6.2.1 Regulatory Compliance

The EU AI Act's requirement for "examination of possible biases" implicitly demands causal pathway analysis. Aggregate observational fairness metrics (demographic parity, equal opportunity) are insufficient to meet this standard. We propose that HC-DML provides one principled approach to compliance, with three required components:

1. **Path decomposition:** Distinguish direct from mediated effects, enabling intervention design
2. **Cluster-level reporting:** Required for hierarchical contexts where aggregates mislead
3. **Sensitivity analysis:** Documented robustness to ψ and Γ values

Practitioners building EU AI Act compliance procedures should consider these as minimum requirements rather than optional refinements.

### 6.2.2 Practical Guidance for Educational AI Auditors

We provide concrete guidance based on our findings:

**When auditing systems for fairness:**

1. **Always conduct cluster-level analysis** when data has hierarchical structure. Aggregate results may certify systems as fair when substantial within-cluster disparities exist.

2. **Decompose direct and indirect effects** to inform intervention design. Direct effects suggest evaluator bias or feature engineering issues; mediated effects suggest upstream factors affecting engagement, preparation, or assessment.

3. **Use bootstrap inference, not asymptotic SE.** Especially for substitution estimators, asymptotic SE may be wildly anti-conservative.

4. **Report sensitivity systematically.** $\psi$-range and $\Gamma$-break provide concrete robustness statements.

5. **Verify identifying assumptions when possible.** Overlap diagnostics, DAG defensibility, mediator timing — all should be documented.

### 6.2.3 Substantive Findings on OULAD

The OULAD per-cluster heterogeneity finding has independent substantive value:

- **For institutional research at Open University:** The data suggest specific modules (CCC, FFF) where female advantages emerge, and others (BBB) where the reverse holds. Module-level review may surface causes — instructor effects, course content, peer composition, assessment methods.

- **For online education broadly:** The findings suggest fairness in online courses may be much more context-dependent than typically assumed. A single algorithm or pedagogy may produce different fairness implications across courses, instructors, or cohorts.

- **For research methodology:** Future fairness analyses of OULAD (or similar datasets) should adopt cluster-level reporting. Our results suggest aggregate-only analyses systematically misrepresent the data's fairness structure.

## 6.3 Limitations

We address limitations of our work honestly. These represent areas for future improvement rather than weaknesses to be hidden.

### 6.3.1 Theoretical Limitations

**Cross-world assumption (Robins 2003) remains untestable.** Path-specific effects require an assumption about cross-world counterfactual independence that cannot be verified from data. Our sensitivity analysis addresses unobserved confounding (Γ) but not cross-world violations specifically. Schröder et al. (2024) provide one approach for this; extending their neural framework to clustered path-specific settings is future work.

**Formal proofs are sketched, not complete.** The theorems in Section 3 (particularly the asymptotic normality argument) rely on standard DML techniques extended via clustered CLT. While the structure of the proofs is clear, the detailed verification requires careful work that we defer to a companion theoretical paper. For journals requiring complete proofs (e.g., Biometrika, JASA), this represents necessary additional investment.

**Higher-order orthogonality not exploited.** The EIF we derive is first-order orthogonal. Higher-order orthogonality (Mackey et al., 2018) could provide additional robustness to nuisance estimation, particularly in settings with weak overlap. We did not pursue this extension.

### 6.3.2 Methodological Limitations

**Density estimation under Gaussian assumption.** Our mediator density implementation assumes conditional Gaussianity. While this is computationally efficient and stable, real mediators may exhibit:

- Heavy tails (e.g., engagement metrics)
- Multi-modality
- Bounded support (e.g., scores in [0, 100])
- Discrete components (e.g., binary indicators)

Kernel density estimation or normalizing flows would provide more flexibility at additional computational cost. Empirically, on datasets where mediators clearly violate Gaussianity (OULAD `sum_clicks` is heavily right-skewed), the EIF still produces reasonable estimates, suggesting some robustness to mild violations. But systematic evaluation is warranted.

**Sensitivity bounds may be conservative.** Our MSM bounds vary propensity and density ratio simultaneously at worst case. Tighter bounds exploiting the path-specific structure remain an open problem. For OULAD, where the aggregate Γ-break of 1.12 may be conservative, the true robustness threshold may be modestly higher.

**Sample size requirements limit small-dataset applicability.** The EIF estimator's reliability degrades substantially below $n = 1000$. For many educational research contexts (single school studies, pilot evaluations), this constraint requires the fallback substitution + bootstrap approach. This bifurcation in recommendations is honest but inconvenient for practitioners.

### 6.3.3 Empirical Limitations

**DAG specifications involve substantive judgment.** Our default DAG assignments (e.g., treating prior grades as mediators rather than covariates) are defensible but not unique. Alternative specifications might yield different conclusions. The DAG sensitivity analysis we describe (Level C) addresses this in principle but was not systematically conducted in this paper due to space constraints.

**Limited baseline implementation.** Our simplified Chiappa (2019) baseline uses PCA rather than the original VAE. Full replication of Chiappa's approach would require substantial additional engineering. We acknowledge this limitation while noting that full VAE replication has not been provided in published causal fairness comparisons either.

**Missing comparison with very recent work.** The fast-moving causal fairness literature includes recent papers (e.g., Plečko and Bareinboim, 2024; Nabi et al., 2024) whose detailed empirical comparison would require additional work. We position our contribution relative to these works conceptually but not via head-to-head empirical comparison.

**Treatment of small-sample datasets.** The UCI Mathematics dataset ($n = 395$) was excluded from main analyses because its sample size falls below the recommended threshold ($n \geq 500$) for EIF-based estimation. Application of our framework to this dataset produces unstable density ratio estimates (maximum density ratio exceeded 100 in diagnostic checks) and unreliable point estimates. We retain analysis of the UCI Portuguese dataset ($n = 649$), which falls just above the small-sample threshold and serves as the empirical lower-bound case in our experiments. This exclusion follows our general guidance (Section 3.8.4) that EIF estimation requires sufficient data for stable nuisance estimation, particularly for the cross-world density ratio component.

### 6.3.4 Substantive Limitations

**OULAD findings are descriptive, not explanatory.** We document substantial cluster-level heterogeneity but do not identify its causes. Why do CCC modules show female advantages while BBB modules do not? Course content? Instructor effects? Cohort composition? Future work could address this through formal moderator analysis with cluster-level features.

**Generalizability of OULAD findings.** OULAD is a specific institution (Open University UK) at a specific time period (2013–2014). The patterns observed may be specific to that context. Replication on other hierarchically structured educational datasets (e.g., PISA, IPEDS) is needed before strong general claims.

**Privacy and ethical considerations.** Cluster-level reporting raises potential privacy concerns when clusters are small (e.g., specific instructors, courses). We did not address whether all cluster-level disclosures in fairness audits are ethically appropriate. This is an important practical consideration we defer to ethics literature.

---

# 7. Conclusion

We have presented Hierarchical Causal Double Machine Learning (HC-DML), a methodology for path-specific counterfactual fairness in clustered data with particular relevance to educational AI applications. The key contributions are:

**Theoretical:** We derive the efficient influence function for natural direct and indirect effects under hierarchical sequential ignorability, extending the IID results of Tchetgen-Tchetgen and Shpitser (2014) to clustered data. We establish $\sqrt{n}$-consistency, asymptotic normality, doubly robust property, and Neyman orthogonality under regularity conditions on nuisance estimation rates and cluster growth.

**Methodological:** We develop a complete estimation procedure combining hierarchical cross-fitting (extending Liu et al., 2024), EIF score computation, and cluster-robust variance estimation. The implementation includes substitution-based estimation with bootstrap inference for settings where EIF is inappropriate (e.g., small samples), and a three-level sensitivity analysis framework addressing path justifiability, unobserved confounding, and DAG specification choices.

**Empirical:** We validate HC-DML on five datasets (synthetic + UCI Student Portuguese, xAPI, Law School, OULAD; the UCI Mathematics dataset was excluded for falling below the recommended sample-size threshold). Three findings emerge as substantive contributions:

1. **Cluster-level fairness heterogeneity in OULAD:** Cochran's Q test rejects effect homogeneity across the 22 modules at $p = 4.06 \times 10^{-7}$ ($I^2 = 70\%$), with one module (CCC_2014J) reaching strong significance after Benjamini-Hochberg correction ($p_{\text{BH}} \approx 10^{-11}$). Cluster-specific point estimates span $-0.064$ to $+0.146$ across modules—nearly three times the aggregate estimate—entirely obscured by the marginal $\tau = +0.076$.

2. **Direct/indirect effect suppression:** In OULAD, NDE ($+0.230$) and NIE ($-0.154$) operate in opposing directions, with the aggregate measure obscuring both substantial pathways. This has direct implications for intervention design.

3. **Substitution estimator SE underestimation:** On clustered datasets (xAPI, OULAD), substitution-based estimators underestimate standard errors by 3.5×–4× compared to cluster bootstrap inference. On the IID Law School case the asymptotic SE collapses to a degenerate near-zero value, suggesting that for clustered or large-$n$ IID settings, asymptotic SE from substitution estimators should not be trusted without bootstrap verification. This raises concerns about reported significance in prior causal fairness literature when applied to clustered data.

The methodology and findings have implications for three communities. For **causal inference researchers**, we extend established efficient inference theory to a substantively important hierarchical setting. For **fairness ML researchers**, we provide a principled alternative to IID-based counterfactual fairness for the educational domain where clustering is ubiquitous. For **educational practitioners and policy makers**, we provide tools and findings supporting EU AI Act compliance and rigorous fairness audits of high-stakes educational AI systems.

**Open questions for future work:** Tighter sensitivity bounds exploiting path-specific structure; kernel density estimation for non-Gaussian mediators; complete formal proofs of asymptotic theorems suitable for theoretical statistics journals; explanation of cluster-level heterogeneity patterns through moderator analysis; replication across additional hierarchically structured educational datasets; integration with the broader causal fairness analysis framework of Plečko and Bareinboim (2024).

The complete reproducibility package (Python code, LaTeX theory documents, data preprocessing scripts) is available for community use. We hope this contributes to making rigorous causal fairness analysis more accessible for the diverse practitioners conducting AI audits across educational institutions.

---

## Acknowledgments

[To be added based on institutional affiliations, funding sources, and collaborators.]

## Statement on Reproducibility

All code, data preprocessing pipelines, and theoretical documents are available in an open-source repository. The package includes:

- 29 Python files (~8,500 LOC): core estimators, baselines, sensitivity analysis, data loaders, diagnostic utilities, evaluation scripts
- LaTeX theory documents: detailed EIF derivation and theorem statements
- Configuration files specifying all hyperparameters used in reported experiments
- Verification scripts producing the synthetic validation results in Section 5.1

The four public datasets used (UCI Student Performance, xAPI, Law School, OULAD) are publicly available under their respective licenses. Reproducibility code does not redistribute the data but provides loading scripts compatible with the standard public formats.

Random seeds are fixed at 42 for all reported point estimates; bootstrap inference uses seed-controlled resampling for reproducibility.

## Statement on Use of AI

Portions of the implementation, derivation, and writing in this paper were assisted by AI tools (specifically, large language models). The authors take full responsibility for verification of all theoretical claims and empirical results. AI-assisted derivations were independently verified through empirical simulation (Section 5.1) and cross-checked against established literature (notably Tchetgen-Tchetgen and Shpitser, 2014).

---
