import type { Metadata } from "next";
import Link from "next/link";
import snapshot from "../../snapshot/data_platform_snapshot.json";

export const metadata: Metadata = {
  title: "财报预报",
  description: "查看即将发布与已发布的公司财报事件、时间、状态和来源。",
};

type CalendarEvent = (typeof snapshot.earnings_calendar)[number];

function formatDateTime(value?: string | null, dateOnly = false) {
  if (!value) return "—";
  const normalized = value.replace("T", " ");
  return dateOnly ? normalized.slice(0, 10) : normalized.slice(0, 16);
}

function releaseDisplay(event: CalendarEvent) {
  if (event.actual_release_beijing) return `${formatDateTime(event.actual_release_beijing)}（北京时间）`;
  if (event.planned_release_beijing) return `${formatDateTime(event.planned_release_beijing)}（北京时间）`;
  if (event.official_appointment_date) return `${formatDateTime(event.official_appointment_date, true)}（官方日期，时间未披露）`;
  if (event.estimated_date) return `${formatDateTime(event.estimated_date, true)}（第三方预计）`;
  return "待核实";
}

function EventTable({ events, emptyText }: { events: CalendarEvent[]; emptyText: string }) {
  if (!events.length) return <div className="empty-state"><strong>{emptyText}</strong></div>;
  return (
    <div className="table-scroll earnings-table">
      <table>
        <thead><tr><th>公司</th><th>财报期间</th><th>发布时间</th><th>状态</th><th>电话会</th><th>来源</th></tr></thead>
        <tbody>
          {events.map((event) => (
            <tr key={`${event.company_id}-${event.period}`}>
              <td><strong>{event.company}</strong><small>{event.ticker} · {event.market}</small></td>
              <td><strong>{event.period}</strong><small>{event.report_type}</small></td>
              <td>{releaseDisplay(event)}</td>
              <td><span className={`event-status ${event.released ? "released" : "upcoming"}`}>{event.status}</span></td>
              <td>{event.call_time_beijing ? `${formatDateTime(event.call_time_beijing)}（北京时间）` : "—"}</td>
              <td>
                {event.source_url
                  ? <a className="source-link" href={event.source_url} target="_blank" rel="noreferrer">{event.source_name || "查看来源"}</a>
                  : (event.source_name || "待核实")}
                <small>核查：{formatDateTime(event.last_checked_at)}</small>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function EarningsPage() {
  const events = snapshot.earnings_calendar as CalendarEvent[];
  const upcoming = events.filter((event) => !event.released);
  const released = events.filter((event) => event.released);

  return (
    <main>
      <Link className="back-link" href="/">← 返回公司数据</Link>
      <section className="section-heading forecast-heading">
        <div><p className="eyebrow">财报预报</p><h1>财报发布时间表</h1></div>
        <p>精确时间仅展示官方已披露字段；只有日期时不推测具体时刻。</p>
      </section>

      <section className="calendar-section">
        <div className="section-heading compact"><div><p className="eyebrow">Upcoming</p><h2>即将发布</h2></div><p>{upcoming.length} 条事件</p></div>
        <EventTable events={upcoming} emptyText="暂无已登记的即将发布事件" />
      </section>

      <section className="calendar-section">
        <div className="section-heading compact"><div><p className="eyebrow">Released</p><h2>已发布</h2></div><p>{released.length} 条事件</p></div>
        <EventTable events={released} emptyText="暂无已登记的已发布事件" />
      </section>
    </main>
  );
}
