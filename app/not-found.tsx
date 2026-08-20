import Link from "next/link";

export default function NotFound() {
  return (
    <main>
      <section className="error-page">
        <span className="error-code">404</span>
        <h1>暂无这家公司的财报数据</h1>
        <p>当前结构化输入没有对应的公司页面。</p>
        <small>不会使用其他公司的数据代替。</small>
        <Link className="button-link" href="/">返回公司列表</Link>
      </section>
    </main>
  );
}
