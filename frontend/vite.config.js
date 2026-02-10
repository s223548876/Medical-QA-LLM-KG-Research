import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const repoName = process.env.GITHUB_REPOSITORY?.split("/")[1] || "medical_demo";
const envBasePath = process.env.VITE_BASE_PATH;
const base = envBasePath || `/${repoName}/`;

export default defineConfig({
  plugins: [react()],
  base,
});
