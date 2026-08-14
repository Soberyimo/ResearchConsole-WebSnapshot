import type { Metadata } from "next";
import snapshot from "../snapshot/research_snapshot.json";

export const metadata: Metadata = {
  title: "首页",
};

export default function Home() {
  return <main dangerouslySetInnerHTML={{ __html: snapshot.home_html }} />;
}
