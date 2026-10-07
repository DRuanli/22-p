// The site sets body text in uppercase. Mathematical symbols must keep their case
// (τ is not T, k is not K), so wrap them in a span that opts out of the transform.
const escape = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const MATH = /(τ|ρ|BL\(S, h\)|IUS_deploy|\bk\b|\bp\b|\bh\b(?= =|\)))/g;
export const math = (s: string) => escape(s).replace(MATH, '<span class="nc">$1</span>');
