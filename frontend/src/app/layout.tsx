import type { Metadata } from "next";
import "./globals.css";

// 系统字体栈（避免国内构建下载 Google Fonts 超时）
const interFont = {
  variable: "--font-inter",
};

export const metadata: Metadata = {
  title: "Crypto Risk Dashboard",
  description: "加密货币风控评估系统",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={interFont.variable}>
      <body
        className="min-h-screen"
        style={{ background: "#0A0A0B" }}
      >
        {/* Subtle top gradient glow */}
        <div
          className="fixed inset-0 pointer-events-none z-0"
          style={{
            background:
              "radial-gradient(ellipse 80% 40% at 50% -10%, rgba(59,130,246,0.08) 0%, transparent 70%)",
          }}
        />
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
