// @ts-check
import { defineConfig } from "astro/config";

// Served from GitHub Pages as a project site: https://druanli.github.io/22-p/
// If you move this to a <username>.github.io repo, set base to "/".
export default defineConfig({
  site: "https://druanli.github.io",
  base: "/22-p/",
});
