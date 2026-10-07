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

export type PlateKind = "lattice" | "utility" | "cohort" | "danube" | "classroom";

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
      "My first research route. It started in the course Design and Analysis of Algorithms and ended as TUFCI, a best-first search algorithm for the top-k closed frequent itemsets in uncertain data, published in PLOS ONE.",
    overview:
      "When every item in a database appears only with some probability, which itemsets are frequent, closed, and among the k best? TUFCI answers it with a best-first search that expands the most promising candidates first.",
    stats: [
      { label: "Duration", value: "18 months" },
      { label: "Period", value: "09/2024 – 02/2026" },
      { label: "Advisor", value: "Dr. Chi-Thien Nguyen" },
      { label: "Outcome", value: "PLOS ONE, Q1" },
    ],
    steps: [
      { when: "09/2024", where: "Ton Duc Thang University", title: "Departure", body: "The project starts inside the course Design and Analysis of Algorithms, graded 10.0." },
      { when: "2024 – 2025", where: "Uncertain databases", title: "The problem", body: "Top-k closed frequent itemsets when every item only appears with some probability." },
      { when: "– 02/2026", where: "Best-first search", title: "The algorithm", body: "TUFCI expands the most promising candidate itemsets before the rest." },
      { when: "17/06/2026", where: "PLOS ONE 21(6)", title: "Arrival", body: "Published as e0351951. Le, N., Vo, H., & Nguyen, T." },
    ],
    cta: { label: "Read in PLOS ONE", href: "https://doi.org/10.1371/journal.pone.0351951" },
  },
  {
    id: "ptk-huim",
    name: "PTK-HUIM",
    title: "Profits, losses and uncertain data",
    length: "13 months",
    months: 13,
    plate: "utility",
    teaser:
      "My thesis route: finding the k most profitable item combinations in uncertain transaction data where items can bring profit or loss. A counterexample, two correct bounds, an exact algorithm and the first heuristic for the problem.",
    overview:
      "The standard pruning bound gives wrong results once items can bring a loss. I showed this by counterexample, derived two bounds that stay correct, and built PTK-HUIM, an exact algorithm with three provably equivalent search orders, together with UTKU-PSO, the first heuristic for the problem.",
    stats: [
      { label: "Duration", value: "13 months" },
      { label: "Period", value: "06/2025 – 06/2026" },
      { label: "Thesis grade", value: "9.1 / 10" },
      { label: "Outcome", value: "JKSU – CIS, Q1, in press" },
    ],
    steps: [
      { when: "06/2025", where: "Undergraduate thesis", title: "Departure", body: "Advisor Dr. Chi-Thien Nguyen. Mixed utilities: items can bring profit or loss." },
      { when: "Step 01", where: "A counterexample", title: "The broken bound", body: "The standard pruning bound gives wrong results once negative utilities are allowed." },
      { when: "Step 02", where: "Two upper bounds", title: "Correct pruning", body: "Two bounds that stay correct with mixed utilities." },
      { when: "Step 03", where: "PTK-HUIM", title: "Exact algorithm", body: "Three search orders, provably equivalent." },
      { when: "Step 04", where: "UTKU-PSO", title: "First heuristic", body: "The first heuristic approach for this problem." },
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
      "A route through a real school. With 675 students' anonymised Mathematics records, I showed that common early-warning models use behaviour data the school does not have yet when it must predict, and built IC-FS, which only uses what is available.",
    overview:
      "Early-warning systems report impressive results, but many of them select student-behaviour features the school does not have at the moment it must predict. IC-FS restricts feature selection to data available at prediction time, with an automatic no-leakage check.",
    stats: [
      { label: "Duration", value: "10 months" },
      { label: "Period", value: "08/2025 – 05/2026" },
      { label: "Cohort", value: "675 students" },
      { label: "Outcome", value: "ESWA, Q1" },
    ],
    steps: [
      { when: "08/2025", where: "Lower-secondary school", title: "Departure", body: "With M.Sc. Huu-Phuoc Duong and a lower-secondary school in southern Vietnam." },
      { when: "Step 01", where: "675 students", title: "The data", body: "An anonymised Mathematics cohort, with written confirmation of data provision." },
      { when: "Step 02", where: "Behavioural leakage", title: "The illusion", body: "Common models pick features not yet known at prediction time, so reported results overstate what can be used for intervention." },
      { when: "Step 03", where: "IC-FS", title: "The fix", body: "Feature selection restricted to data available at prediction time. The no-leakage check held in every cross-validation fold." },
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
      "From the Mekong to the Danube. An exchange semester at OTH Regensburg in Germany, funded by a merit-based TL-Stiftung scholarship. German began here, and my English classes in Vietnam kept going online.",
    overview:
      "An exchange semester at Ostbayerische Technische Hochschule Regensburg, funded by a merit-based TL-Stiftung scholarship. My English classes continued online the whole time. Solo trips have taken me to Germany, France, Austria and Taiwan.",
    stats: [
      { label: "Duration", value: "6 months" },
      { label: "Period", value: "03/2024 – 09/2024" },
      { label: "Funding", value: "TL-Stiftung scholarship" },
      { label: "Language", value: "German A2" },
    ],
    steps: [
      { when: "03/2024", where: "OTH Regensburg", title: "Departure", body: "Exchange semester on a merit-based TL-Stiftung scholarship." },
      { when: "2024", where: "Germany", title: "A new language", body: "German starts with the exchange; today at A2." },
      { when: "2024", where: "Online", title: "Classes keep going", body: "English classes in Ho Chi Minh City continue online throughout the semester." },
      { when: "09/2024", where: "Ho Chi Minh City", title: "Return", body: "Back home, and straight into the first research project." },
    ],
    cta: { label: "Write to me", href: "mailto:elio.ruanli@gmail.com" },
  },
  {
    id: "teaching",
    name: "MAC English",
    title: "Teaching English since 2023",
    length: "Since 2023",
    months: 0,
    plate: "classroom",
    teaser:
      "A route that runs alongside all the others. Since 2023 I teach English part-time at MAC English centre in Ho Chi Minh City, from primary learners to upper-secondary students preparing for Flyers, PET and IELTS.",
    overview:
      "Part-time English teacher at MAC English centre in Ho Chi Minh City since 2023, for primary, lower-secondary and upper-secondary learners. Current offline classes prepare students for Flyers, PET and IELTS.",
    stats: [
      { label: "Since", value: "2023" },
      { label: "Where", value: "MAC English centre" },
      { label: "Learners", value: "Primary to upper-secondary" },
      { label: "My English", value: "IELTS Academic 7.0" },
    ],
    steps: [
      { when: "2023", where: "MAC English centre", title: "First classes", body: "Part-time teacher in Ho Chi Minh City." },
      { when: "Level 01", where: "Flyers", title: "Young learners", body: "Cambridge Young Learners classes." },
      { when: "Level 02", where: "PET", title: "B1 Preliminary", body: "Cambridge B1 Preliminary classes." },
      { when: "Level 03", where: "IELTS", title: "Academic English", body: "IELTS preparation classes." },
      { when: "2024", where: "Online, from Germany", title: "Never paused", body: "Teaching continued online throughout the exchange semester." },
    ],
    cta: { label: "Ask about classes", href: "mailto:elio.ruanli@gmail.com?subject=English%20classes" },
  },
];

export const milestones = [
  { when: "2019", where: "Can Tho", title: "Upper-secondary school", body: "Nguyen Viet Hong Upper-Secondary School, until 2022. Chinese begins here." },
  { when: "09/2022", where: "Ho Chi Minh City", title: "B.Sc. Computer Science", body: "Ton Duc Thang University; Academic Merit Scholarship in several semesters." },
  { when: "2023", where: "MAC English centre", title: "First English classes", body: "Part-time teacher for primary to upper-secondary learners." },
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
};

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
