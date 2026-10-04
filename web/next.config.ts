import type { NextConfig } from "next";

// ---------------------------------------------------------------------------
// Bức tường biến môi trường — chặn một lỗi deploy đã xảy ra thật.
// ---------------------------------------------------------------------------
// `NEXT_PUBLIC_*` được NHÚNG lúc build. Quên đặt `NEXT_PUBLIC_API_BASE_URL` trên Vercel nghĩa là xuất bản
// một bản dựng gọi về localhost của NGƯỜI ĐANG MỞ TRANG: trang vẫn lên, mọi thứ chỉ hỏng khi bấm, và thông
// báo lỗi không nhắc gì tới biến môi trường. Một dòng tài liệu là tấm biển; bản dựng đổ là bức tường.
// Chỉ chặn khi có `VERCEL`: CI và máy dev trỏ 127.0.0.1 là lựa chọn tường minh, không phải bỏ quên.
// Khoá bởi `npm run check:env-wall` (scripts/check-env-wall.mts) — đổi `throw` thành cảnh báo là bước đó đỏ.
if (process.env.VERCEL) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  // Biến trên Vercel đặt RIÊNG cho Production / Preview / Development — nêu môi trường để người sửa biết chỗ thiếu.
  const environment = process.env.VERCEL_ENV || "không rõ";
  if (!apiBase) {
    throw new Error(
      `NEXT_PUBLIC_API_BASE_URL chưa được đặt trên Vercel (môi trường: ${environment}). ` +
        "Đặt ở Project Settings → Environment Variables cho CẢ Production, Preview và Development.",
    );
  }
  if (/^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:|\/|$)/i.test(apiBase)) {
    throw new Error(`NEXT_PUBLIC_API_BASE_URL trỏ về máy cục bộ (${apiBase}) trong bản dựng Vercel.`);
  }
}

const nextConfig: NextConfig = {
  // `standalone` chỉ cho image Docker (web/Dockerfile đặt NEXT_OUTPUT). Vercel tự đóng gói, còn `next start`
  // trong CI/e2e không chạy đúng với standalone.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
};

export default nextConfig;
