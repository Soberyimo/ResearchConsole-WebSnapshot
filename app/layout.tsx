import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://soberyimo.github.io"),
  title: {
    default: "云见财报 · Visualizer",
    template: "%s · 云见财报",
  },
  description: "GPT 结构化财报数据的只读可视化展示层。",
  robots: { index: true, follow: true },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <head>
        {/* eslint-disable-next-line @next/next/no-css-tags */}
        <link rel="stylesheet" href="/snapshot-styles.css" />
        {/* eslint-disable-next-line @next/next/no-css-tags */}
        <link rel="stylesheet" href="/snapshot-polish.css" />
      </head>
      <body>
        <header className="topbar">
          <Link className="brand" href="/">
            <span className="brand-mark">云见</span>
            <span>
              <strong>云见财报</strong>
              <small>Financial Data Visualizer</small>
            </span>
          </Link>
        </header>
        {children}
        <footer>
          <span>GPT-owned structured input</span>
          <span>JSON / CSV · display only</span>
        </footer>
        <Script src="/snapshot-app.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
