import Link from "next/link";

export default function NotFound() {
  return (
    <main>
      <section className="error-page">
        <span className="error-code">已安全停止显示 · 404</span>
        <h1>尚无正式研究结果</h1>
        <p>当前公开快照没有这家公司的 canonical Research Output。</p>
        <small>不会使用暂存、试运行或其他公司的结果作为替代。</small>
        <Link className="button-link" href="/">返回公司列表</Link>
      </section>
    </main>
  );
}
