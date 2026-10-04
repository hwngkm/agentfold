"use client";

import { useEffect, useState } from "react";

import { getHealth, type Health } from "@/lib/api/health";
import { ApiRequestError } from "@/lib/api/http";

// Mẫu "đủ trạng thái" (docs/rules/30-frontend.md R30.4): đang tải · sẵn sàng · lỗi có thử lại.
type State = { kind: "loading" } | { kind: "ready"; health: Health } | { kind: "error"; message: string };

function describe(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.body?.retryable ? `${error.body.detail} Đang có thể thử lại.` : `Máy chủ trả lỗi ${error.status}.`;
  }
  return "Chưa kết nối được máy chủ — máy chủ có thể đang khởi động (tới ~1 phút). Thử lại sau ít giây.";
}

export default function Home() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((health) => {
        if (!cancelled) setState({ kind: "ready", health });
      })
      .catch((error: unknown) => {
        if (!cancelled) setState({ kind: "error", message: describe(error) });
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  return (
    <main className="page">
      <h1>Agentfold</h1>
      <p>Trạng thái máy chủ:</p>
      {state.kind === "loading" && <p role="status">Đang kiểm tra…</p>}
      {state.kind === "ready" && (
        <p role="status" data-testid="health-status">
          {state.health.status} · môi trường {state.health.env}
        </p>
      )}
      {state.kind === "error" && (
        <div role="alert">
          <p>{state.message}</p>
          <button
            type="button"
            onClick={() => {
              setState({ kind: "loading" });
              setAttempt((value) => value + 1);
            }}
          >
            Thử lại
          </button>
        </div>
      )}
    </main>
  );
}
