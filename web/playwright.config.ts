import { defineConfig, devices } from "@playwright/test";

const PORT = process.env.WEB_PORT || "3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  // KHÔNG retry: chạy lại tới khi xanh biến lỗi chập chờn thành lỗi vô hình, và deploy "chờ CI qua" sẽ đưa nó
  // lên production. Đỏ thì đọc trace + ảnh chụp (CI tải lên artifact). Khoá bởi tests/guards/test_deploy_waits_for_ci.py.
  retries: 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npm run start -- --port ${PORT}`,
    url: `http://127.0.0.1:${PORT}`,
    // Không tái dùng server đang chạy: biến NEXT_PUBLIC_* nhúng lúc khởi động, server cũ gọi backend cũ — mọi
    // con số e2e khi đó nói về một hệ thống khác (đã gặp thật).
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
