// All copy comes from docs/content.md (filled from the CV). Do not add facts that are not there.

export const person = {
  name: "Dang Nguyen Le",
  publishedAs: "Nguyen Le",
  role: "Researcher in data mining and educational machine learning, English teacher, solo traveller.",
  location: "Ho Chi Minh City, Vietnam",
  email: "elio.ruanli@gmail.com",
  scholar: "https://scholar.google.com/citations?user=AeLm94oAAAAJ",
  orcid: "https://orcid.org/0009-0009-5517-9996",
};

export const facts = [
  {
    title: "Valedictorian, Computer Science",
    body: "Ranked 1st of the 2022–2026 cohort at Ton Duc Thang University with a GPA of 8.98/10, and graduated in April 2026, one semester ahead of schedule.",
  },
  {
    title: "Researcher at Ton Duc Thang University",
    body: "Appointed to the Faculty of Information Technology in September 2026 after a review of my research record. I work with Assoc. Prof. Anh-Cuong Le, Dean of the Faculty.",
  },
  {
    title: "A semester on the Danube",
    body: "Exchange semester at OTH Regensburg, Germany, from March to September 2024, funded by a merit-based TL-Stiftung scholarship. IELTS Academic 7.0.",
  },
  {
    title: "Industry practice",
    body: "Intern at FPT Information System from August to December 2025, helping deploy an information system for a provincial Civil Judgment Enforcement Department. Graded 9.5/10.",
  },
];

export const affiliations = [
  "Ton Duc Thang University",
  "OTH Regensburg",
  "FPT Information System",
  "MAC English centre",
  "Expert Systems with Applications",
  "PLOS ONE",
  "Journal of King Saud University – CIS",
];

export type Paper = {
  venue: string;
  year: string;
  title: string;
  authors: string;
  finding: string;
  href?: string;
  status?: string;
};

export const papers: Paper[] = [
  {
    venue: "Expert Systems with Applications",
    year: "2026",
    title:
      "Behavioural leakage and the illusion of actionability: a deployment-honest evaluation framework for educational early warning systems",
    authors: "Le, N., Lam, T., & Duong, H.-P.",
    finding:
      "Common early-warning models pick behaviour features a school does not yet have when it must predict. IC-FS selects only what is available at prediction time.",
    href: "https://doi.org/10.1016/j.eswa.2026.134262",
  },
  {
    venue: "PLOS ONE",
    year: "2026",
    title:
      "Best-first search–based approach for mining top-k closed frequent itemsets from uncertain databases",
    authors: "Le, N., Vo, H., & Nguyen, T.",
    finding:
      "TUFCI, a best-first search algorithm for the top-k closed frequent itemsets in uncertain data.",
    href: "https://doi.org/10.1371/journal.pone.0351951",
  },
  {
    venue: "Journal of King Saud University – CIS",
    year: "In press",
    title:
      "Exact and heuristic approaches for mining top-k high-utility itemsets in uncertain databases with mixed utilities",
    authors: "Le, N., Vo, H., & Nguyen, T.",
    finding:
      "A counterexample shows the standard pruning bound fails when items can bring loss; two correct bounds, the exact PTK-HUIM and the first heuristic, UTKU-PSO.",
    status: "Accepted August 2026",
  },
];

export const interests = [
  "Data mining",
  "Learning from imperfect data",
  "Exact pattern mining with provable pruning bounds",
  "Educational machine learning",
];

export const languages = [
  { name: "Vietnamese", level: "native" },
  { name: "English", level: "IELTS Academic 7.0" },
  { name: "German", level: "A2" },
  { name: "Chinese", level: "HSK 3" },
];

/* ---------- v2: journey, expeditions, profile, FAQ (all from the CV) ---------- */

export const stats = [
  { value: 3, decimals: 0, suffix: "", label: "first-author articles in Q1 journals" },
  { value: 8.98, decimals: 2, suffix: "/10", label: "final GPA, ranked 1st of the cohort" },
  { value: 4, decimals: 0, suffix: "", label: "languages, from native to HSK 3" },
  { value: 5, decimals: 0, suffix: "", label: "north–south journeys across Vietnam" },
];

export type Station = { date: string; place: string; title: string; body: string };

export const stations: Station[] = [
  { date: "2019", place: "Can Tho", title: "Upper-secondary school", body: "Nguyen Viet Hong Upper-Secondary School, Can Tho, until 2022. Chinese starts here." },
  { date: "09/2022", place: "Ho Chi Minh City", title: "B.Sc. Computer Science begins", body: "Ton Duc Thang University, on an Academic Merit Scholarship over several semesters." },
  { date: "2023", place: "Ho Chi Minh City", title: "First English classes", body: "Part-time teacher at MAC English centre, for primary to upper-secondary learners." },
  { date: "03/2024", place: "Regensburg", title: "Exchange semester in Germany", body: "OTH Regensburg on a merit-based TL-Stiftung scholarship. German begins; teaching continues online." },
  { date: "09/2024", place: "Ho Chi Minh City", title: "First research project", body: "Starts in the course Design and Analysis of Algorithms and becomes TUFCI." },
  { date: "06/2025", place: "Ho Chi Minh City", title: "Thesis research", body: "Top-k high-utility itemsets in uncertain data where items can bring profit or loss." },
  { date: "08/2025", place: "FPT IS", title: "Internship and a school study", body: "Intern at FPT IS until December; the early-warning project with a lower-secondary school begins." },
  { date: "04/2026", place: "Ho Chi Minh City", title: "Valedictorian", body: "Graduates 1st of the cohort, GPA 8.98/10, one semester early. Thesis graded 9.1/10." },
  { date: "06/2026", place: "PLOS ONE", title: "First article published", body: "Top-k closed frequent itemsets from uncertain databases, published 17 June 2026." },
  { date: "08/2026", place: "JKSU – CIS", title: "Thesis article accepted", body: "Exact and heuristic approaches for top-k HUIM with mixed utilities. IELTS Academic 7.0 the same month." },
  { date: "09/2026", place: "Ton Duc Thang University", title: "Researcher", body: "Appointed to the Faculty of IT. The ESWA article on early-warning systems is published online on 6 September." },
];

export type Expedition = {
  id: string;
  name: string;
  subtitle: string;
  period: string;
  months: number;
  cover: "lattice" | "utility" | "cohort";
  summary: string;
  team: string;
  steps: { title: string; body: string }[];
  result: { label: string; href?: string };
};

export const expeditions: Expedition[] = [
  {
    id: "tufci",
    name: "TUFCI",
    subtitle: "Top-k closed frequent itemsets in uncertain data",
    period: "09/2024 – 02/2026",
    months: 18,
    cover: "lattice",
    summary: "A best-first search algorithm that finds the k most frequent closed itemsets when every item only appears with some probability.",
    team: "With advisor Dr. Chi-Thien Nguyen",
    steps: [
      { title: "Starting point", body: "The project starts in the course Design and Analysis of Algorithms (grade 10.0)." },
      { title: "The algorithm", body: "TUFCI explores candidate itemsets best-first, so the most promising ones are expanded before the rest." },
      { title: "Arrival", body: "Published in PLOS ONE 21(6), e0351951, on 17 June 2026." },
    ],
    result: { label: "PLOS ONE, 2026", href: "https://doi.org/10.1371/journal.pone.0351951" },
  },
  {
    id: "ptk-huim",
    name: "PTK-HUIM",
    subtitle: "Top-k high-utility itemsets with profits and losses",
    period: "06/2025 – 06/2026",
    months: 13,
    cover: "utility",
    summary: "Finding the k most profitable item combinations in uncertain transaction data where items can bring profit or loss.",
    team: "Undergraduate thesis, advisor Dr. Chi-Thien Nguyen",
    steps: [
      { title: "A broken bound", body: "A counterexample shows the standard pruning bound gives wrong results once negative utilities are allowed." },
      { title: "Two correct bounds", body: "Derived two upper bounds that stay correct with mixed utilities." },
      { title: "Exact algorithm", body: "PTK-HUIM, with three search orders that are provably equivalent." },
      { title: "First heuristic", body: "UTKU-PSO, the first heuristic for this problem." },
      { title: "Arrival", body: "Thesis graded 9.1/10; article accepted in JKSU – CIS in August 2026." },
    ],
    result: { label: "JKSU – CIS, in press" },
  },
  {
    id: "ic-fs",
    name: "IC-FS",
    subtitle: "Deployment-honest early-warning systems",
    period: "08/2025 – 05/2026",
    months: 10,
    cover: "cohort",
    summary: "Early-warning models often rely on behaviour data a school does not have yet when it must predict. IC-FS only uses what is available at prediction time.",
    team: "With M.Sc. Huu-Phuoc Duong and a lower-secondary school in southern Vietnam",
    steps: [
      { title: "The data", body: "An anonymised Mathematics cohort of 675 students, with written confirmation from the school." },
      { title: "The leak", body: "Common models select student-behaviour features that are not yet known at prediction time, so reported results overstate what can be used for intervention." },
      { title: "The fix", body: "IC-FS, a feature-selection method restricted to data available at prediction time. Its automatic no-leakage check held in every cross-validation fold." },
      { title: "Arrival", body: "Published in Expert Systems with Applications, online 6 September 2026." },
    ],
    result: { label: "ESWA, 2026", href: "https://doi.org/10.1016/j.eswa.2026.134262" },
  },
];

export const education = [
  {
    period: "09/2022 – 04/2026",
    title: "B.Sc. in Computer Science",
    place: "Ton Duc Thang University, Ho Chi Minh City",
    points: [
      "GPA 8.98/10, ranked 1st in the graduating class; finished one semester ahead of schedule.",
      "Thesis on top-k high-utility itemsets in uncertain databases with positive and negative utilities, 9.1/10.",
      "Design and Analysis of Algorithms 10.0 · Data Structures and Algorithms 10.0 · Deep Learning 9.4",
    ],
  },
  {
    period: "03/2024 – 09/2024",
    title: "Exchange semester",
    place: "OTH Regensburg, Germany",
    points: ["Funded by a merit-based TL-Stiftung scholarship."],
  },
  {
    period: "2019 – 2022",
    title: "Upper-secondary school",
    place: "Nguyen Viet Hong Upper-Secondary School, Can Tho",
    points: [],
  },
];

export const honours = [
  { year: "2026", title: "Valedictorian, B.Sc. Computer Science, Ton Duc Thang University" },
  { year: "2024", title: "TL-Stiftung Scholarship for an exchange semester in Germany" },
  { year: "2022 – 2026", title: "Academic Merit Scholarship, Ton Duc Thang University" },
  { year: "2015 – 2023", title: "Academic Merit Scholarship, Vietnam General Confederation of Labour" },
];

export const skills = [
  { group: "Programming", items: ["Python", "Java", "SQL"] },
  { group: "ML and data", items: ["PyTorch", "scikit-learn", "pandas", "NumPy"] },
  { group: "Tools", items: ["Git", "LaTeX"] },
];

export const faq = [
  { q: "Which name do you publish under?", a: "Nguyen Le. My full name is Dang Nguyen Le." },
  { q: "Where can I find all of your papers?", a: "On Google Scholar and ORCID, linked at the bottom of this page. Each paper above also links to its DOI." },
  { q: "What are you working on now?", a: "I am a researcher at the Faculty of Information Technology, Ton Duc Thang University, working with Assoc. Prof. Anh-Cuong Le." },
  { q: "Which languages can we work in?", a: "Vietnamese (native), English (IELTS Academic 7.0), German (A2) and Chinese (HSK 3)." },
  { q: "How do I get in touch?", a: "By email at elio.ruanli@gmail.com." },
];
