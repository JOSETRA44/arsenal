import type { NextConfig } from "next";

/**
 * Static export: this is a documentation site with no server-side needs, so it
 * builds to plain HTML that any static host — GitHub Pages included — can serve.
 * `images.unoptimized` is required because the optimizer needs a running server.
 */
const config: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default config;
