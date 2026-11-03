const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const envPath = path.resolve(__dirname, "../../.env");
if (!fs.existsSync(envPath)) {
  console.error("Не найден корневой .env. Положите его в корень репозитория.");
  process.exit(1);
}

for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) continue;
  const separator = trimmed.indexOf("=");
  if (separator === -1) continue;
  const key = trimmed.slice(0, separator).trim();
  let value = trimmed.slice(separator + 1).trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  if (process.env[key] === undefined) process.env[key] = value;
}

const [command, ...args] = process.argv.slice(2);
if (!command) {
  console.error("Не указана команда.");
  process.exit(1);
}

const entries = {
  next: "next/dist/bin/next",
  prisma: "prisma/build/index.js",
  tsx: "tsx/dist/cli.mjs",
};
const entry = entries[command];
const script = entry ? path.join(__dirname, "..", "node_modules", entry) : "";
if (!script || !fs.existsSync(script)) {
  console.error("Неизвестная команда.");
  process.exit(1);
}

const child = spawn(process.execPath, [script, ...args], {
  stdio: "inherit",
  env: process.env,
});
child.on("exit", (code) => process.exit(code ?? 1));
