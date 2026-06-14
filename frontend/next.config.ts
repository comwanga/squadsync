import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  turbopack: {
    // Pin the workspace root to this app directory so Turbopack doesn't infer it
    // from parent lockfiles (the repo root and the home directory both have one),
    // which produced a "multiple lockfiles" warning.
    root: path.join(__dirname),
  },
};

export default nextConfig;
