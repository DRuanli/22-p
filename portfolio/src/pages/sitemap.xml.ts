import type { APIRoute } from "astro";
import { routes } from "../data/site";

export const GET: APIRoute = ({ site }) => {
  const base = import.meta.env.BASE_URL;
  const paths = ["", "gallery/", ...routes.map((r) => `routes/${r.id}/`)];
  const urls = paths.map((p) => `  <url><loc>${new URL(base + p, site)}</loc></url>`).join("\n");
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
    { headers: { "Content-Type": "application/xml" } },
  );
};
