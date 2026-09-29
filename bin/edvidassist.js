#!/usr/bin/env node

import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, "..");
const args = process.argv.slice(2);

// Try using uv first, fallback to python3 -m edvidassist
const child = spawn("uv", ["run", "--project", projectRoot, "python", "-m", "edvidassist", ...args], {
  stdio: "inherit",
  env: process.env,
});

child.on("error", () => {
  // If uv is not available, fallback to python3
  const pyChild = spawn("python3", ["-m", "edvidassist", ...args], {
    cwd: projectRoot,
    stdio: "inherit",
    env: process.env,
  });

  pyChild.on("exit", (code) => {
    process.exit(code ?? 0);
  });
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
