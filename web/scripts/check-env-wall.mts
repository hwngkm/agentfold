// Kiểm bức tường biến môi trường bằng cách NẠP THẬT next.config.ts với từng bộ biến.
// `grep` tìm chữ `throw` sẽ vẫn xanh sau khi ai đó đổi nó thành console.warn — đúng cách bức tường này chết.
import { spawnSync } from "node:child_process";

type Case = { label: string; env: Record<string, string>; shouldFail: boolean };

const cases: Case[] = [
  { label: "Vercel thiếu biến", env: { VERCEL: "1", VERCEL_ENV: "preview" }, shouldFail: true },
  { label: "Vercel trỏ localhost", env: { VERCEL: "1", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" }, shouldFail: true },
  { label: "Vercel trỏ 127.0.0.1", env: { VERCEL: "1", NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000" }, shouldFail: true },
  { label: "Vercel đúng", env: { VERCEL: "1", NEXT_PUBLIC_API_BASE_URL: "https://api.example.onrender.com" }, shouldFail: false },
  { label: "CI/dev ngoài Vercel", env: { NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000" }, shouldFail: false },
];

const baseEnv = { ...process.env };
for (const key of ["VERCEL", "VERCEL_ENV", "NEXT_PUBLIC_API_BASE_URL"]) delete baseEnv[key];

let failures = 0;
for (const item of cases) {
  const result = spawnSync(
    process.execPath,
    ["--import", "tsx", "--input-type=module", "-e", "await import('./next.config.ts')"],
    { env: { ...baseEnv, ...item.env }, encoding: "utf8" },
  );
  const failed = result.status !== 0;
  const ok = failed === item.shouldFail;
  if (!ok) failures += 1;
  console.log(`${ok ? "ĐẠT" : "SAI"}  ${item.label}: ${failed ? "bản dựng đổ" : "bản dựng qua"}`);
}

if (failures > 0) {
  console.error(`🔴 ${failures} ca sai — bức tường biến môi trường đã bị nới.`);
  process.exit(1);
}
console.log("✅ Bức tường biến môi trường còn đứng.");
