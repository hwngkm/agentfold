// Lớp gọi HTTP dùng chung — làn độc quyền `web-api-core` (coordination/policy.yaml).
// Mỗi tài nguyên API là một module riêng cạnh file này (health.ts, ...), không dồn vào một client khổng lồ.

export type ApiErrorBody = { code: string; detail: string; retryable: boolean };

export class ApiRequestError extends Error {
  constructor(
    readonly status: number,
    readonly body: ApiErrorBody | null,
  ) {
    super(body?.detail ?? `HTTP ${status}`);
    this.name = "ApiRequestError";
  }
}

// Gốc API KHÔNG kèm /api/v1. Trên Vercel, next.config.ts làm bản dựng đổ nếu biến này thiếu.
const BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
// Mọi lời gọi có timeout: backend gói miễn phí có cold start, không để giao diện treo vô hạn.
const TIMEOUT_MS = 20_000;

export async function apiGet<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { Accept: "application/json", ...init.headers },
    });
    if (!response.ok) {
      let body: ApiErrorBody | null = null;
      try {
        body = (await response.json()) as ApiErrorBody;
      } catch {
        body = null;
      }
      throw new ApiRequestError(response.status, body);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}
