import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://soberyimo.github.io"),
  title: {
    default: "云见财报",
    template: "%s · 云见财报",
  },
  description: "看懂公司的收入、盈利、经营与销量变化。",
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
          {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
          <a className="brand" href="/">
            <span className="brand-mark">云见</span>
            <span>
              <strong>云见财报</strong>
              <small>公司财务与经营数据</small>
            </span>
          </a>
        </header>
        {children}
        <footer>
          <span>云见财报</span>
          <span>数据来源与口径可在公司页展开查看</span>
        </footer>
        <Script src="/snapshot-app.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
