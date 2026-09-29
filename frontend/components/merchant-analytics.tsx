"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";
import { api, errorMessage, money, Page } from "../lib/api";
import { AppShell, EmptyState, LoadingState, Notice } from "./app-shell";
import "./merchant-analytics.css";

type Totals = { revenue: string; order_count: number; quantity_sold: number; average_order_amount: string };
type Day = { date: string; revenue: string; order_count: number; quantity_sold: number };
type Dashboard = {
  start_date: string; end_date: string; generated_at: string; product_id: number | null;
  totals: Totals; previous_totals: Totals; daily: Day[];
  top_products: { product_id: number; product_name: string; quantity_sold: number; revenue: string }[];
  products: { id: number; name: string }[];
};
type LowStock = { product_id: number; name: string; quantity: number };

function beijingToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}

function change(current: number, previous: number) {
  if (!previous) return current ? "上期为 0，本期新增" : "与上期持平";
  const percent = (current - previous) / previous * 100;
  return percent === 0 ? "与上期持平" : `较上期 ${percent > 0 ? "+" : ""}${percent.toFixed(1)}%`;
}

function TrendChart({ rows, metric, title }: { rows: Day[]; metric: "revenue" | "quantity_sold"; title: string }) {
  const [active, setActive] = useState<number | null>(null);
  const titleId = useId();
  const values = rows.map(row => Number(row[metric]));
  const max = Math.max(1, ...values);
  const left = 64, right = 694, top = 22, bottom = 218;
  const width = (right - left) / Math.max(rows.length, 1);
  const x = (i: number) => left + width * (i + 0.5);
  const y = (value: number) => bottom - value / max * (bottom - top);
  const selected = active === null ? null : rows[active];
  return <section className="panel chart-panel">
    <div className="panel-heading"><h2 id={titleId}>{title}</h2><span>{metric === "revenue" ? "元 · CNY" : "件"}</span></div>
    <p className="chart-hint">{values.some(v => v > 0) ? "移到图表上查看每日数据，也可用 Tab 键选择。" : "所选时段暂无成交，日期已补零。"}</p>
    <svg className="merchant-chart" viewBox="0 0 720 260" aria-labelledby={titleId} role="group">
      {[0, 0.5, 1].map(fraction => <g key={fraction}>
        <line x1={left} x2={right} y1={y(max * fraction)} y2={y(max * fraction)} stroke="#ede4dd" strokeDasharray="4 5" />
        <text x={left - 10} y={y(max * fraction) + 4} textAnchor="end">{new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 }).format(max * fraction)}</text>
      </g>)}
      {metric === "revenue" && <>
        <polygon points={`${x(0)},${bottom} ${values.map((v, i) => `${x(i)},${y(v)}`).join(" ")} ${x(values.length - 1)},${bottom}`} fill="#ed927324" />
        <polyline points={values.map((v, i) => `${x(i)},${y(v)}`).join(" ")} fill="none" stroke="#d66648" strokeWidth="3" strokeLinejoin="round" />
      </>}
      {rows.map((row, index) => <g key={row.date}>
        {metric === "quantity_sold" ? <rect x={x(index) - width * .32} y={y(values[index])} width={width * .64} height={bottom - y(values[index])} rx="3" fill={active === index ? "#b95437" : "#eda079"} /> : <circle cx={x(index)} cy={y(values[index])} r={active === index ? 5 : 2.5} fill="#d66648" />}
        <rect x={x(index) - width / 2} y={top} width={width} height={bottom - top + 2} fill="transparent" tabIndex={0} role="img"
          aria-label={`${row.date}：${metric === "revenue" ? money(row.revenue) : `${row.quantity_sold} 件`}`}
          onMouseEnter={() => setActive(index)} onMouseLeave={() => setActive(null)} onFocus={() => setActive(index)} onBlur={() => setActive(null)}>
          <title>{row.date}：{metric === "revenue" ? money(row.revenue) : `${row.quantity_sold} 件`}</title>
        </rect>
        {(index === 0 || index === rows.length - 1 || index % Math.ceil(rows.length / 5) === 0) && <text x={x(index)} y="246" textAnchor="middle">{row.date.slice(5)}</text>}
      </g>)}
    </svg>
    <div className="chart-readout" aria-live="polite">{selected ? <><span>{selected.date}</span><strong>{metric === "revenue" ? money(selected.revenue) : `${selected.quantity_sold} 件`}</strong><span>{selected.order_count} 笔成交</span></> : <span>每日数据 · 北京时间</span>}</div>
  </section>;
}

export function MerchantAnalyticsDashboard({ overview = false }: { overview?: boolean }) {
  const [days, setDays] = useState(30);
  const [end, setEnd] = useState(beijingToday);
  const [product, setProduct] = useState("");
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState<Dashboard | null>(null);
  const [low, setLow] = useState<LowStock[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    const query = new URLSearchParams({ days: String(days), end_date: end });
    if (product) query.set("product_id", product);
    Promise.all([
      api<Dashboard>(`/api/merchant/analytics/dashboard?${query}`, { signal: controller.signal }),
      api<Page<LowStock>>("/api/merchant/analytics/low-stock?threshold=5&page_size=10", { signal: controller.signal }),
    ]).then(([next, stock]) => {
      if (!controller.signal.aborted) { setData(next); setLow(stock.items); }
    }).catch(err => {
      if (!controller.signal.aborted) { setError(errorMessage(err)); setData(null); }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [days, end, product, revision]);

  const metrics: [string, keyof Totals, boolean][] = [
    [product ? "商品销售额" : "店铺销售额", "revenue", true], ["成交订单", "order_count", false],
    ["售出商品", "quantity_sold", false], [product ? "每单商品金额" : "平均订单金额", "average_order_amount", true],
  ];
  return <AppShell title={overview ? "经营概览" : "经营分析"} description="看清收入变化，掌握商品销售表现。" activePath={overview ? "/merchant/dashboard" : "/merchant/analytics"} expectedRole="MERCHANT">
    <section className="analytics-toolbar panel" aria-label="分析筛选">
      <div className="analytics-period" aria-label="统计时段">{[7, 30, 90].map(value => <button key={value} type="button" aria-pressed={days === value} className={days === value ? "primary" : ""} onClick={() => setDays(value)}>近 {value} 天</button>)}</div>
      <label>截止日期<input type="date" min="2000-01-01" max={beijingToday()} value={end} onChange={event => { if (event.target.value) setEnd(event.target.value); }} /></label>
      <label>统计商品<select value={product} onChange={event => setProduct(event.target.value)}><option value="">全店商品</option>{data?.products.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <button type="button" disabled={loading} onClick={() => setRevision(value => value + 1)}>刷新数据</button>
    </section>
    <Notice message={error} tone="error" />
    {loading ? <LoadingState label="正在汇总店铺数据…" /> : data && <div className="analytics-content">
      <div className="analytics-caption"><span>{data.start_date} 至 {data.end_date} · 北京时间</span><span>更新于 {new Date(data.generated_at).toLocaleTimeString("zh-CN", { timeZone: "Asia/Shanghai" })}</span></div>
      <div className="metric-grid">{metrics.map(([label, key, currency]) => <article className="metric-card" key={key}><span>{label}</span><strong>{currency ? money(data.totals[key]) : data.totals[key]}</strong><small>{change(Number(data.totals[key]), Number(data.previous_totals[key]))}</small></article>)}</div>
      <div className="analytics-charts"><TrendChart key={`revenue-${days}-${end}-${product}`} rows={data.daily} metric="revenue" title="收入趋势" /><TrendChart key={`sales-${days}-${end}-${product}`} rows={data.daily} metric="quantity_sold" title={product ? "商品售卖趋势" : "每日销量"} /></div>
      <div className="analytics-charts">
        <section className="panel"><div className="panel-heading"><h2>商品销量排行</h2><span>当前时段 · 前 10 名</span></div>{data.top_products.length ? <ol className="sales-bars">{data.top_products.map(item => <li key={item.product_id}><div><Link href={`/merchant/products/${item.product_id}/edit`}>{item.product_name}</Link><strong>{item.quantity_sold} 件</strong></div><div className="sales-bar-track"><span style={{ width: `${item.quantity_sold / Math.max(1, ...data.top_products.map(p => p.quantity_sold)) * 100}%` }} /></div><small>销售额 {money(item.revenue)}</small></li>)}</ol> : <EmptyState>暂无成交商品</EmptyState>}</section>
        <section className="panel"><div className="panel-heading"><h2>补货提醒</h2><Link href="/merchant/inventory">查看库存</Link></div><p className="chart-hint">全店当前库存 ≤ 5 件，不受时段筛选影响。</p>{low.length ? <div className="low-list">{low.map(item => <div key={item.product_id}><span>{item.name}</span><b>{item.quantity}</b></div>)}</div> : <EmptyState>当前库存状态良好</EmptyState>}</section>
      </div>
      <details className="panel daily-details"><summary>查看每日数据明细（{data.daily.length} 天）</summary><div className="table-scroll"><table><caption>与上方图表一致的每日成交数据</caption><thead><tr><th>日期</th><th>销售额</th><th>成交订单</th><th>售出件数</th></tr></thead><tbody>{data.daily.map(row => <tr key={row.date}><td>{row.date}</td><td>{money(row.revenue)}</td><td>{row.order_count}</td><td>{row.quantity_sold}</td></tr>)}</tbody></table></div></details>
      <p className="analytics-note">统计说明：按成功支付时间统计，排除未付款、已取消及已退款订单；金额不扣除成本。商品筛选按订单中的该商品成交金额统计。对比前一个等长自然日区间；包含今天时，当日数据尚未结束。点击刷新获取最新结果。</p>
    </div>}
  </AppShell>;
}
