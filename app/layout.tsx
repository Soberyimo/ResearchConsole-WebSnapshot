import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://soberyimo.github.io"),
  title: {
    default: "云见财报 · 数据平台",
    template: "%s · 云见财报",
  },
  description: "财报预报与公司财务数据浏览平台。",
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
              <small>财报数据平台 · 只读</small>
            </span>
          </Link>
        </header>
        {children}
        <footer>
          <span>派生快照 · ResearchOS production 仍是唯一事实源</span>
          <span>财报预报与财务数据 · 无写回能力</span>
        </footer>
        <Script src="/snapshot-app.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
