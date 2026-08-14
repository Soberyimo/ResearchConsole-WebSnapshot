import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://soberyimo.github.io"),
  title: {
    default: "Research Console · 公开快照",
    template: "%s · Research Console",
  },
  description: "云见财报 ResearchOS 的只读 Web Snapshot。",
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
        <link rel="stylesheet" href="/snapshot-styles.css" />
        <link rel="stylesheet" href="/snapshot-polish.css" />
      </head>
      <body>
        <header className="topbar">
          <Link className="brand" href="/">
            <span className="brand-mark">云见</span>
            <span>
              <strong>Research Console</strong>
              <small>公开快照 · 只读</small>
            </span>
          </Link>
          <div className="readonly-badge">Public Snapshot</div>
        </header>
        {children}
        <footer>
          <span>派生快照 · ResearchOS production 仍是唯一事实源</span>
          <span>Console v0.1.3 · 无写回能力</span>
        </footer>
        <Script src="/snapshot-app.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
