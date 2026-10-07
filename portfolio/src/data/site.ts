// All copy comes from docs/content.md (filled from the CV). Do not add facts that are not there.

export const person = {
  name: "Dang Nguyen Le",
  publishedAs: "Nguyen Le",
  location: "Ho Chi Minh City, Vietnam",
  email: "elio.ruanli@gmail.com",
  scholar: "https://scholar.google.com/citations?user=AeLm94oAAAAJ",
  orcid: "https://orcid.org/0009-0009-5517-9996",
  orcidId: "0009-0009-5517-9996",
};

export type PlateKind = "lattice" | "utility" | "cohort" | "danube";

export type Route = {
  id: string;
  name: string; // list label
  title: string; // detail page headline
  length: string; // "18 months"
  months: number;
  plate: PlateKind;
  teaser: string; // right-column text on the home page
  overview: string;
  stats: { label: string; value: string }[];
  steps: { when: string; where: string; title: string; body: string }[];
  cta: { label: string; href: string };
  figures?: { src: string; caption: string; credit: string }[]; // reusable figures from the paper
};

export const routes: Route[] = [
  {
    id: "tufci",
    name: "TUFCI",
    title: "Top-k closed itemsets in uncertain data",
    length: "18 months",
    months: 18,
    plate: "lattice",
    teaser:
      "My first research route. Depth-first miners meet strong patterns late, so their pruning threshold rises slowly. TUFCI explores candidates in descending probabilistic support instead: it finds strong patterns first, stops early, and needs about 60% fewer closure checks on Chess. Published in PLOS ONE.",
    overview:
      "In an uncertain database every item appears only with some probability, and computing an itemset's probabilistic support costs a quadratic convolution. Most top-k closed miners walk the search space depth-first, in item order, so high-support patterns surface late and the pruning threshold rises slowly. TUFCI replaces the stack with a priority queue ordered by probabilistic support: strong patterns arrive first, the threshold climbs fast, search can terminate safely, and closure checks start with the supersets most likely to fail.",
    stats: [
      { label: "Duration", value: "18 months" },
      { label: "Period", value: "09/2024 – 02/2026" },
      { label: "Advisor", value: "Dr. Chi-Thien Nguyen" },
      { label: "Outcome", value: "PLOS ONE, Q1" },
    ],
    steps: [
      { when: "09/2024", where: "Design and Analysis of Algorithms", title: "Departure", body: "The project starts inside the course (grade 10.0), with one question: does search order matter when support is expensive?" },
      { when: "Problem", where: "Uncertain databases", title: "Late strong patterns", body: "Depth-first search explores in enumeration order, so high-support patterns are found late, pruning stays weak and closure checks pile up." },
      { when: "Idea", where: "Priority queue", title: "Best-first search", body: "Candidates are expanded in descending probabilistic support, so the top-k threshold rises quickly and search can stop early." },
      { when: "Proof", where: "Seven pruning strategies", title: "Safe pruning", body: "P1–P7, in four groups, are proven never to remove a true top-k closed frequent itemset, including safe early termination." },
      { when: "Tests", where: "Chess · Mushroom · Retail · Liquor", title: "Dense and sparse data", body: "Against TopKPFIM and ITUFP, plus ablations that separate search order from pruning; differences significant at p < 0.01." },
      { when: "17/06/2026", where: "PLOS ONE 21(6)", title: "Arrival", body: "Published as e0351951. Le, N., Vo, H., & Nguyen, T. Code and data on GitHub." },
    ],
    cta: { label: "Read in PLOS ONE", href: "https://doi.org/10.1371/journal.pone.0351951" },
    figures: [
      { src: "media/papers/tufci-fig2.webp", caption: "Fig 2. Traversal order. Depth-first search wastes work on low-support nodes before it reaches the strong one; best-first search visits it first, raises the threshold and prunes the rest.", credit: "Le, Vo & Nguyen (2026), PLOS ONE 21(6): e0351951, CC BY 4.0" },
      { src: "media/papers/tufci-fig3.webp", caption: "Fig 3. Runtime against the external baselines TopKPFIM and ITUFP on Chess, Liquor, Mushrooms and Retail: 2–3× faster on dense data.", credit: "Le, Vo & Nguyen (2026), PLOS ONE 21(6): e0351951, CC BY 4.0" },
      { src: "media/papers/tufci-fig5.webp", caption: "Fig 5. Closure checks with identical pruning: best-first search needs about 60% fewer than depth-first search.", credit: "Le, Vo & Nguyen (2026), PLOS ONE 21(6): e0351951, CC BY 4.0" },
    ],
  },
  {
    id: "ptk-huim",
    name: "PTK-HUIM",
    title: "Profits, losses and uncertain data",
    length: "13 months",
    months: 13,
    plate: "utility",
    teaser:
      "My thesis route: the k most profitable item combinations in uncertain data where items can bring profit or loss. A counterexample shows the classical bound fails here; two new bounds make an exact algorithm correct, and UTKU-PSO is the first heuristic for the problem.",
    overview:
      "Top-k high-utility mining finds the k most profitable itemsets without a hand-tuned threshold, but existing algorithms assume certain data and positive profits. Real data has neither: sensor readings are noisy, and promotions or loss leaders carry negative profit. I showed by counterexample that the classical transaction-weighted utility bound is unsafe in this setting even after probability weighting, derived two bounds that are safe (PTWU and PUB), and built an exact algorithm and a heuristic on top of them.",
    stats: [
      { label: "Duration", value: "13 months" },
      { label: "Period", value: "06/2025 – 06/2026" },
      { label: "Thesis grade", value: "9.1 / 10" },
      { label: "Outcome", value: "JKSU – CIS, Q1, in press" },
    ],
    steps: [
      { when: "06/2025", where: "Undergraduate thesis", title: "Departure", body: "Advisor Dr. Chi-Thien Nguyen. No algorithm covered top-k utility mining on uncertain data with both positive and negative profits." },
      { when: "Step 01", where: "A counterexample", title: "The broken bound", body: "The classical transaction-weighted utility bound can prune true answers once negative utilities appear, even with probabilities applied." },
      { when: "Step 02", where: "PTWU · PUB", title: "Two safe bounds", body: "Positive Transaction-Weighted Utility and Positive Upper Bound: required for correctness, not just speed." },
      { when: "Step 03", where: "UPU-List", title: "PTK-HUIM, exact", body: "Prefix growth on a Utility-Probability-Utility List; depth-first, breadth-first and best-first orders proven to return the same top-k." },
      { when: "Step 04", where: "UTKU-PSO", title: "First heuristic", body: "Particle swarm with probability-aware fitness, PTWU-based bit clearing and a shifted roulette wheel for negative utilities." },
      { when: "Step 05", where: "Six benchmarks", title: "Honest trade-offs", body: "Chess, Mushroom, Accidents, Pumsb, Retail, Kosarak, and three further probability models, one breaking independence." },
      { when: "08/2026", where: "JKSU – CIS", title: "Arrival", body: "Thesis graded 9.1/10; the article was accepted in August 2026." },
    ],
    cta: { label: "Ask about this work", href: "mailto:elio.ruanli@gmail.com?subject=PTK-HUIM" },
  },
  {
    id: "ic-fs",
    name: "IC-FS",
    title: "Early warning without the leak",
    length: "10 months",
    months: 10,
    plate: "cohort",
    teaser:
      "A route through real school data. Early-warning models often rely on student behaviour that does not exist yet when they must predict. In a course-start test, five standard selectors chose ten features each and not one was available; IC-FS certifies that cannot happen. Published in Expert Systems with Applications.",
    overview:
      "An early-warning system is only useful if it can act when the course begins. Yet feature selectors routinely pick engagement signals, like clicks in the learning platform, that do not exist yet at that moment. The paper names this Behavioural Leakage and its extreme case, the Illusion of Actionability, gives a machine-checkable no-leakage certificate, an evaluation that retrains on horizon-available features only, and IC-FS, a selector that satisfies the certificate by construction.",
    stats: [
      { label: "Duration", value: "10 months" },
      { label: "Period", value: "08/2025 – 05/2026" },
      { label: "Data", value: "OULAD · UCI · 675-student cohort" },
      { label: "Outcome", value: "ESWA, Q1" },
    ],
    steps: [
      { when: "08/2025", where: "Lower-secondary school", title: "Departure", body: "With M.Sc. Huu-Phuoc Duong and a lower-secondary school in southern Vietnam that provided an anonymised cohort." },
      { when: "Step 01", where: "Two failure modes", title: "Naming the leak", body: "Behavioural Leakage: actionable behaviour not observable at the horizon. Illusion of Actionability: its limit, τ = 1." },
      { when: "Step 02", where: "BL(S, h)", title: "A certificate", body: "A binary no-leakage check for any selection, kept separate from the intervention-utility score IUS_deploy." },
      { when: "Step 03", where: "Two protocols", title: "Deployment-honest", body: "Retrain on horizon-available features for the estimate; audit an already-deployed model under missing late features (DRE)." },
      { when: "Step 04", where: "OULAD · UCI · Vietnam", title: "Evidence", body: "Group-aware 5-fold CV with bootstrap intervals, a fairness audit across sensitive attributes, and a 675-student case study." },
      { when: "06/09/2026", where: "Expert Systems with Applications", title: "Arrival", body: "Published online, volume 333, article 134262. Le, N., Lam, T., & Duong, H.-P." },
    ],
    cta: { label: "Read in ESWA", href: "https://doi.org/10.1016/j.eswa.2026.134262" },
  },
  {
    id: "regensburg",
    name: "Regensburg",
    title: "A semester on the Danube",
    length: "6 months",
    months: 6,
    plate: "danube",
    teaser:
      "From the Mekong to the Danube. Six months at OTH Regensburg on a TL-Stiftung scholarship: five courses, a data-science project built from scratch in three weeks, a study group of four nations working in Mandarin, and weekends from Pisa to Vienna.",
    overview:
      "I found the TL-Stiftung scholarship two days before its deadline, renewed an expired passport in Can Tho after the award, and landed in Munich at 1 °C in March 2024. At OTH Regensburg, a partner university of Ton Duc Thang, I took five courses, among them Applied Python for Data Science, Natural Language Processing and German, and learned what self-directed study means: no attendance lists, lecturers who talk with students as peers, and classmates who live in the library.",
    stats: [
      { label: "Duration", value: "6 months" },
      { label: "Period", value: "03/2024 – 09/2024" },
      { label: "Funding", value: "TL-Stiftung scholarship" },
      { label: "Courses", value: "5, plus audited classes" },
    ],
    steps: [
      { when: "10/2023", where: "TL-Stiftung", title: "The award", body: "Found the scholarship two days before the deadline, applied with help from TDTU's INCRETI institute, interviewed, and was selected at the end of October." },
      { when: "11/2023", where: "Can Tho", title: "Paperwork", body: "An expired passport, renewed in three to four weeks; then the learning agreement and the visa." },
      { when: "03/2024", where: "Munich → Regensburg", title: "Arrival at 1 °C", body: "An OTH buddy, an hour on the train, and a Deutschlandticket that opened almost all public transport in Germany." },
      { when: "Spring", where: "Old Town Hall", title: "Welcome", body: "International students were received by the city in Regensburg's historic Town Hall." },
      { when: "Semester", where: "OTH Regensburg", title: "Five courses", body: "Applied Python for Data Science, a project built from scratch in three weeks; Natural Language Processing; German; and classes audited alongside." },
      { when: "Semester", where: "Study group", title: "Four nations, one language", body: "Five students from Vietnam, Britain, Ireland and China, working together in Mandarin." },
      { when: "04/2024", where: "Ice rink", title: "First time on ice", body: "A university ice-skating evening: several falls, then confidence." },
      { when: "05/2024", where: "Pisa", title: "First trip abroad", body: "A night in Memmingen before a 6 a.m. flight, the Leaning Tower, and a beach triathlon straight out of Luca." },
      { when: "End 05/2024", where: "Côte d'Azur", title: "Six cities", body: "Nice, Antibes, Cannes, Èze, Monaco on Formula 1 weekend, and Marseille." },
      { when: "06/2024", where: "Salzburg · Vienna", title: "A favourite country", body: "Two visits to Austria: Salzburg, and Vienna in June." },
      { when: "09/2024", where: "Ho Chi Minh City", title: "Return", body: "Back home, and straight into the first research project." },
    ],
    cta: { label: "Write to me", href: "mailto:elio.ruanli@gmail.com" },
  },
];

export const milestones = [
  { when: "2019", where: "Can Tho", title: "Upper-secondary school", body: "Nguyen Viet Hong Upper-Secondary School, until 2022. Chinese begins here." },
  { when: "09/2022", where: "Ho Chi Minh City", title: "B.Sc. Computer Science", body: "Ton Duc Thang University; Academic Merit Scholarship in several semesters." },
  { when: "03/2024", where: "Regensburg", title: "Exchange semester", body: "OTH Regensburg on a merit-based TL-Stiftung scholarship." },
  { when: "09/2024", where: "Ton Duc Thang University", title: "First research project", body: "Begins in Design and Analysis of Algorithms; becomes TUFCI." },
  { when: "08/2025", where: "FPT Information System", title: "Internship", body: "Deploying an information system for a provincial Civil Judgment Enforcement Department. Graded 9.5/10." },
  { when: "04/2026", where: "Ho Chi Minh City", title: "Valedictorian", body: "1st of the cohort, GPA 8.98/10, one semester ahead of schedule." },
  { when: "06/2026", where: "PLOS ONE", title: "First article", body: "Top-k closed frequent itemsets from uncertain databases." },
  { when: "09/2026", where: "Ton Duc Thang University", title: "Researcher", body: "Faculty of IT, working with Assoc. Prof. Anh-Cuong Le. ESWA article online." },
];

export const profileStats = [
  { label: "Degree", value: "B.Sc. Computer Science" },
  { label: "GPA", value: "8.98 / 10" },
  { label: "Rank", value: "1st of cohort" },
  { label: "Articles", value: "3 × Q1, first author" },
];

export const facts = [
  { label: "Now", value: "Researcher, Faculty of IT, Ton Duc Thang University" },
  { label: "2026", value: "Valedictorian, B.Sc. Computer Science" },
  { label: "2025", value: "Intern, FPT Information System" },
  { label: "2024", value: "Exchange semester, OTH Regensburg" },
];

export type Figure = { value: string; label: string };
export type ChartRow = { label: string; value: number; display: string; emphasis?: boolean; note?: string };

export type Paper = {
  venue: string;
  year: string;
  date: string;
  title: string;
  authors: string;
  details: string;
  quartile: string;
  href?: string;
  route: string; // id in routes[]
  citation: string; // APA, as on the CV
  summary: string; // what the paper does, in plain words
  contributions: string[];
  figures: Figure[]; // headline numbers, all from the paper
  chart: { title: string; caption: string; max: number; rows: ChartRow[] };
  data: string[];
  keywords: string[];
};

// Every number below is quoted from the published papers (see docs/content.md).
export const papers: Paper[] = [
  {
    venue: "Expert Systems with Applications",
    year: "2026",
    date: "Online 6 Sep 2026",
    title: "Behavioural leakage and the illusion of actionability: a deployment-honest evaluation framework for educational early warning systems",
    authors: "Le, N., Lam, T., & Duong, H.-P.",
    details: "Vol. 333, 134262 (2027 volume)",
    quartile: "Q1",
    href: "https://doi.org/10.1016/j.eswa.2026.134262",
    route: "ic-fs",
    citation: "Le, N., Lam, T., & Duong, H.-P. (2026). Behavioural leakage and the illusion of actionability: a deployment-honest evaluation framework for educational early warning systems. Expert Systems with Applications, 333, 134262. https://doi.org/10.1016/j.eswa.2026.134262",
    summary:
      "Early warning systems are judged on retrospective accuracy, but they have to act at the start of a course. The paper formalises two deployment failure modes, Behavioural Leakage and the Illusion of Actionability, and builds an evaluation that measures what a school could actually use at the prediction horizon.",
    contributions: [
      "Formal definitions of Behavioural Leakage and the Illusion of Actionability, with an actionability-dilution coefficient τ whose limit τ = 1 is the Illusion.",
      "A machine-checkable no-leakage certificate BL(S, h), deliberately separate from the intervention-utility score IUS_deploy.",
      "A two-protocol evaluation: retrain on horizon-available features for the deployment estimate, and audit an already-deployed model under missing late features (DRE).",
      "IC-FS, a reference selector that satisfies the certificate by construction, with a fairness audit and a single-school case study.",
    ],
    figures: [
      { value: "5/5", label: "standard selectors show the strict Illusion of Actionability at course start (τ = 1)" },
      { value: "0.484", label: "deployable fail-class F1 of IC-FS in that test; the five selectors reach 0.000" },
      { value: "24–31%", label: "relative gain in available actionability over the strongest baseline on OULAD" },
      { value: "675", label: "students in the Vietnamese school cohort, fail prevalence 30.7%" },
    ],
    chart: {
      title: "Course-start diagnostic: deployable fail-class F1",
      caption: "OULAD, risk-set cohort N = 24,601, k = 10 features chosen for the course-start horizon.",
      max: 0.5,
      rows: [
        { label: "IC-FS", value: 0.484, display: "0.484", emphasis: true, note: "Ten deployable features, zero penalty under audit" },
        { label: "IC-FS without temporal filter, retrained", value: 0.456, display: "0.456", note: "Only one of ten features is deployable (τ = 0.848)" },
        { label: "Same model under the DRE audit", value: 0, display: "0.000", note: "Collapses once late features are missing" },
        { label: "MI, RF importance, correlation, L1-LR, Boruta", value: 0, display: "0.000", note: "No selected feature exists at course start" },
      ],
    },
    data: ["OULAD · 24,601–29,496 enrolments per horizon", "UCI Mathematics · 395", "UCI Portuguese · 649", "Vietnamese school · 675"],
    keywords: ["Early warning systems", "Feature selection", "Temporal leakage", "Learning analytics"],
  },
  {
    venue: "PLOS ONE",
    year: "2026",
    date: "Published 17 Jun 2026",
    title: "Best-first search–based approach for mining top-k closed frequent itemsets from uncertain databases",
    authors: "Le, N., Vo, H., & Nguyen, T.",
    details: "21(6), e0351951",
    quartile: "Q1",
    href: "https://doi.org/10.1371/journal.pone.0351951",
    route: "tufci",
    citation: "Le, N., Vo, H., & Nguyen, T. (2026). Best-first search–based approach for mining top-k closed frequent itemsets from uncertain databases. PLOS ONE, 21(6), e0351951. https://doi.org/10.1371/journal.pone.0351951",
    summary:
      "Computing probabilistic support is expensive, so the order in which candidates are explored decides how fast the top-k threshold rises. TUFCI explores in descending probabilistic support with a priority queue: strong patterns first, early termination, and closure checks that start with the supersets most likely to fail.",
    contributions: [
      "The first algorithm to combine best-first search with closure checking for top-k closed frequent itemsets over uncertain data.",
      "A closure-verification strategy that uses support order to skip redundant superset checks.",
      "Seven pruning strategies (P1–P7) proven never to remove a true top-k closed itemset, including safe early termination.",
      "Experiments on dense and sparse benchmarks against TopKPFIM and ITUFP, with ablations separating search order from pruning.",
    ],
    figures: [
      { value: "3.2×", label: "faster than TopKPFIM on Chess at k = 50 (2.8× faster than ITUFP)" },
      { value: "−60%", label: "closure checks versus depth-first search with identical pruning (Chess, k = 50)" },
      { value: "10–100×", label: "fewer candidates processed than naive depth-first search on dense data" },
      { value: "1.5–2×", label: "speed-up kept on the sparse datasets, Retail and Liquor" },
    ],
    chart: {
      title: "Closure checks on Chess, k = 50",
      caption: "Same seven pruning strategies, only the search order differs. Mean of 5 runs; difference significant at p < 0.01.",
      max: 25000,
      rows: [
        { label: "TUFCI, best-first", value: 9200, display: "9,200", emphasis: true, note: "± 340 over 5 runs" },
        { label: "Depth-first, same pruning", value: 23800, display: "23,800", note: "± 1,120 over 5 runs" },
      ],
    },
    data: ["Chess · 3,197", "Mushroom · 8,125", "Retail · 88,162", "Liquor · 52,819 transactions"],
    keywords: ["Uncertain databases", "Closed itemsets", "Top-k mining", "Best-first search"],
  },
  {
    venue: "Journal of King Saud University – Computer and Information Sciences",
    year: "In press",
    date: "Accepted Aug 2026",
    title: "Exact and heuristic approaches for mining top-k high-utility itemsets in uncertain databases with mixed utilities",
    authors: "Le, N., Vo, H., & Nguyen, T.",
    details: "In press",
    quartile: "Q1",
    route: "ptk-huim",
    citation: "Le, N., Vo, H., & Nguyen, T. (in press). Exact and heuristic approaches for mining top-k high-utility itemsets in uncertain databases with mixed utilities. Journal of King Saud University – Computer and Information Sciences.",
    summary:
      "No algorithm handled top-k utility mining on uncertain data where items can bring profit or loss. A counterexample shows the classical bound is unsafe there; two safe bounds make an exact algorithm, PTK-HUIM, correct, and UTKU-PSO is the first heuristic, with its accuracy–speed trade-off measured honestly.",
    contributions: [
      "A formulation of top-k high-utility itemset mining for uncertain databases with positive and negative utilities.",
      "PTK-HUIM: exact prefix growth on the UPU-List with two-level pruning (PTWU, PUB); depth-first, breadth-first and best-first orders proven equivalent.",
      "UTKU-PSO: probability-aware fitness, PTWU-based bit clearing and a shifted roulette wheel for negative expected utilities.",
      "Robustness under three further probability models; one that breaks independence shifts up to 61% of the top-k set.",
    ],
    figures: [
      { value: "5.9×", label: "up to this many fewer nodes for frontier-ordered strategies, which pay up to 17.9× more per node" },
      { value: "5.6×", label: "up to this much faster: UTKU-PSO versus the exact family on large, sparse datasets" },
      { value: "83%", label: "of total expected utility still recovered by UTKU-PSO at k = 20,000 on the sparsest data" },
      { value: "0.998", label: "Spearman ρ between a ground-truth-free diagnostic and true accuracy" },
    ],
    chart: {
      title: "UTKU-PSO at k = 20,000 on the sparsest benchmark",
      caption: "Set accuracy falls at very large k, while most of the expected utility is still found.",
      max: 100,
      rows: [
        { label: "Expected utility recovered", value: 83, display: "83%", emphasis: true, note: "Of the exact top-k total" },
        { label: "Returned itemsets inside the exact top-k", value: 50, display: "≈ 50%", note: "Roughly half fall outside" },
      ],
    },
    data: ["Chess", "Mushroom", "Accidents · 340,183", "Pumsb", "Retail", "Kosarak · 990,002 transactions"],
    keywords: ["High-utility itemsets", "Negative utilities", "Uncertain data", "Particle swarm optimisation"],
  },
];

export const publicationStats = [
  { label: "Journal articles", value: "3" },
  { label: "Quartile (SJR 2025)", value: "3 × Q1" },
  { label: "Authorship", value: "First author on all" },
  { label: "Status", value: "2 published · 1 in press" },
];

export const education = [
  { when: "09/2022 – 04/2026", title: "B.Sc. Computer Science", where: "Ton Duc Thang University", note: "GPA 8.98/10, ranked 1st. Thesis 9.1/10." },
  { when: "03/2024 – 09/2024", title: "Exchange semester", where: "OTH Regensburg, Germany", note: "TL-Stiftung scholarship." },
  { when: "2019 – 2022", title: "Upper-secondary school", where: "Nguyen Viet Hong, Can Tho", note: "" },
];

export const honours = [
  { when: "2026", title: "Valedictorian, Ton Duc Thang University" },
  { when: "2024", title: "TL-Stiftung Scholarship" },
  { when: "2022 – 2026", title: "Academic Merit Scholarship, TDTU" },
  { when: "2015 – 2023", title: "Academic Merit Scholarship, Vietnam General Confederation of Labour" },
];

export const skills = [
  { label: "Programming", value: "Python, Java, SQL" },
  { label: "ML and data", value: "PyTorch, scikit-learn, pandas, NumPy" },
  { label: "Tools", value: "Git, LaTeX" },
  { label: "Languages", value: "Vietnamese (native), English (IELTS 7.0), German (A2), Chinese (HSK 3)" },
];

export const faq = [
  { q: "Which name do you publish under?", a: "Nguyen Le. My full name is Dang Nguyen Le." },
  { q: "Where can I find all of your papers?", a: "On Google Scholar and ORCID, linked at the bottom of this page. The published routes also link to their DOI pages." },
  { q: "What are you working on now?", a: "I am a researcher at the Faculty of IT, Ton Duc Thang University, working with Assoc. Prof. Anh-Cuong Le." },
  { q: "How do I get in touch?", a: "By email at elio.ruanli@gmail.com." },
];

/* ---------- the exchange semester (source: the owner's exchange report for TL-Stiftung) ---------- */

export const exchangeFigures = [
  { value: "1 °C", label: "on landing in Munich, March 2024: the first real cold" },
  { value: "5", label: "courses taken at OTH Regensburg, with more audited" },
  { value: "3 weeks", label: "to build the data-science project from scratch; at home it would have taken two months" },
  { value: "4", label: "countries beyond Germany: Italy, France, Monaco and Austria" },
];

export const exchangeNotes = [
  { title: "Self-directed study", body: "No attendance lists, and lecturers who treat students as peers. With only the course requirements to meet, I built my Python data-science project from scratch in three weeks and received the highest grade I had earned in so short a time." },
  { title: "Ask in the moment", body: "My German classmates asked questions the second they had them and aimed for the top mark or nothing. I came home with the habit of asking during class, not after it." },
  { title: "Protected time", body: "Cafés that close at six, shops shut on Sunday: rest is part of the plan, not what is left of it. It changed how I schedule research." },
  { title: "An idea to bring home", body: "A supermarket checkout near my dorm recognised products without scanning, in under thirty seconds. It is the kind of applied machine learning I would like to build for shops in Vietnam." },
];

// Map stops: [name, longitude, latitude, label placement]
export const exchangeMap = {
  base: ["Regensburg", 12.1, 49.02] as const,
  stops: [
    ["Bamberg", 10.89, 49.89, "w"],
    ["Munich", 11.58, 48.14, "s"],
    ["Memmingen", 10.18, 47.99, "w"],
    ["Pisa", 10.4, 43.72, "e"],
    ["Monaco", 7.42, 43.74, "e"],
    ["Nice", 7.26, 43.7, "n"],
    ["Antibes", 7.12, 43.58, ""],
    ["Cannes", 7.01, 43.55, ""],
    ["Èze", 7.36, 43.73, ""],
    ["Marseille", 5.37, 43.3, "s"],
    ["Salzburg", 13.04, 47.81, "s"],
    ["Vienna", 16.37, 48.21, "s"],
  ] as const,
  trips: [
    ["Regensburg", "Bamberg"],
    ["Regensburg", "Munich"],
    ["Regensburg", "Memmingen", "Pisa"],
    ["Regensburg", "Nice", "Antibes", "Cannes", "Marseille"],
    ["Nice", "Èze", "Monaco"],
    ["Regensburg", "Salzburg", "Vienna"],
  ],
  danube: [[9.99, 48.4], [11.42, 48.76], [12.1, 49.02], [13.46, 48.57], [14.29, 48.31], [15.6, 48.39], [16.37, 48.21]],
};

/* ---------- gallery: photographs, paper figures and route plates ---------- */

export type GalleryItem =
  | { kind: "photo"; src: string; thumb: string; w: number; h: number; caption: string; place: string }
  | { kind: "figure"; src: string; thumb: string; w: number; h: number; caption: string; place: string }
  | { kind: "plate"; plate: PlateKind; id: string; caption: string; place: string };

export const gallery: GalleryItem[] = [
  { kind: "photo", src: "media/gallery/regensburg-bridge.webp", thumb: "media/gallery/regensburg-bridge-s.webp", w: 1050, h: 1400, caption: "Stone Bridge at dusk", place: "Regensburg" },
  { kind: "plate", plate: "lattice", id: "tufci", caption: "TUFCI, the itemset lattice", place: "PLOS ONE" },
  { kind: "photo", src: "media/gallery/vienna-strauss.webp", thumb: "media/gallery/vienna-strauss-s.webp", w: 844, h: 1125, caption: "Johann Strauss monument, Stadtpark", place: "Vienna" },
  { kind: "figure", src: "media/papers/tufci-fig2.webp", thumb: "media/papers/tufci-fig2.webp", w: 1600, h: 812, caption: "Depth-first vs best-first search", place: "TUFCI · Fig 2" },
  { kind: "plate", plate: "cohort", id: "feature", caption: "675 students, one horizon", place: "ESWA" },
  { kind: "photo", src: "media/gallery/magnolia.webp", thumb: "media/gallery/magnolia-s.webp", w: 632, h: 843, caption: "Magnolia in spring", place: "Exchange semester" },
  { kind: "figure", src: "media/papers/tufci-fig5.webp", thumb: "media/papers/tufci-fig5.webp", w: 1600, h: 1527, caption: "Closure checks, BestFS vs DFS", place: "TUFCI · Fig 5" },
  { kind: "photo", src: "media/gallery/vienna-athene.webp", thumb: "media/gallery/vienna-athene-s.webp", w: 1050, h: 1400, caption: "Pallas Athene fountain, Parliament", place: "Vienna" },
  { kind: "plate", plate: "utility", id: "ptk-huim", caption: "Profits above, losses below", place: "PTK-HUIM" },
  { kind: "figure", src: "media/papers/tufci-fig3.webp", thumb: "media/papers/tufci-fig3.webp", w: 1600, h: 1528, caption: "Runtime against the baselines", place: "TUFCI · Fig 3" },
  { kind: "plate", plate: "danube", id: "regensburg-plate", caption: "The Danube, drawn", place: "Regensburg" },
];
