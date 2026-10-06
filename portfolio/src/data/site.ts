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
