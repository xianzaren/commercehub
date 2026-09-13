"use client";

import { useCallback, useEffect, useState } from "react";

import { AppShell, EmptyState, LoadingState, Notice, StatusBadge } from "./app-shell";
import { api, errorMessage, formatDate, money, Order, Page } from "../lib/api";

type AdminView = "dashboard" | "users" | "merchants" | "products" | "orders" | "audit";
type PlatformSummary = { user_count: number; merchant_count: number; store_count: number; product_count: number; order_count: number; paid_order_count: number; total_revenue: string; average_order_amount: string };
type AdminUser = { id: number; email: string; role: string; status: string; created_at: string };
type AdminMerchant = { id: number; user_id: number; business_name: string; status: string; created_at: string };
type AdminProduct = { id: number; store_id: number; sku: string; name: string; current_price: string; status: string };
type AuditLog = { id: number; actor_user_id: number; actor_role: string; action: string; entity_type: string; entity_id: number; before_data?: Record<string, unknown>; after_data?: Record<string, unknown>; created_at: string };

const titles: Record<AdminView, [string, string]> = {
  dashboard: ["平台概览", "全平台账户、交易和销售额摘要。"],
  users: ["用户管理", "管理账户状态，变更将立即影响现有会话。"],
  merchants: ["商家审核", "审批申请并管理商家经营状态。"],
  products: ["商品治理", "查看全平台商品并强制下架违规内容。"],
  orders: ["平台订单", "跨店铺查看订单、支付与商品信息。"],
  audit: ["审计日志", "追踪重要管理操作的前后状态。"],
};

export function AdminPage({ view }: { view: AdminView }) {
  const [summary, setSummary] = useState<PlatformSummary | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [merchants, setMerchants] = useState<AdminMerchant[]>([]);
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true); setMessage("");
    try {
      if (view === "dashboard") setSummary(await api<PlatformSummary>("/api/admin/analytics/summary"));
      if (view === "users") setUsers((await api<Page<AdminUser>>("/api/admin/users?page_size=100")).items);
      if (view === "merchants") setMerchants((await api<Page<AdminMerchant>>("/api/admin/merchants?page_size=100")).items);
      if (view === "products") setProducts((await api<Page<AdminProduct>>("/api/admin/products?page_size=100")).items);
      if (view === "orders") setOrders((await api<Page<Order>>("/api/admin/orders?page_size=100")).items);
      if (view === "audit") setLogs((await api<Page<AuditLog>>("/api/admin/audit-logs?page_size=100")).items);
    } catch (error) { setMessage(errorMessage(error)); } finally { setLoading(false); }
  }, [view]);
  useEffect(() => { load(); }, [load]);

  async function userStatus(id: number, status: string) {
    try { await api(`/api/admin/users/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, reason: "管理员前端操作" }) }); setMessage("用户状态已更新"); load(); } catch (error) { setMessage(errorMessage(error)); }
  }
  async function merchantAction(item: AdminMerchant, action: "approve" | "status", status?: string) {
    try {
      if (action === "approve") await api(`/api/admin/merchant-applications/${item.id}/approve`, { method: "POST" });
      else await api(`/api/admin/merchants/${item.id}/status`, { method: "PATCH", body: JSON.stringify({ status, reason: "管理员前端操作" }) });
      setMessage("商家状态已更新"); load();
    } catch (error) { setMessage(errorMessage(error)); }
  }
  async function deactivate(id: number) {
    try { await api(`/api/admin/products/${id}/force-deactivate`, { method: "POST", body: JSON.stringify({ reason: "管理员前端强制下架" }) }); setMessage("商品已强制下架"); load(); } catch (error) { setMessage(errorMessage(error)); }
  }

  const [title, description] = titles[view];
  return <AppShell title={title} description={description} activePath={`/admin/${view}`} expectedRole="ADMIN"><Notice message={message} tone={message.includes("已") ? "success" : "error"} />{loading ? <LoadingState /> : render()}</AppShell>;

  function render() {
    if (view === "dashboard") {
      const metrics = [["平台用户", summary?.user_count ?? 0], ["活跃商家", summary?.merchant_count ?? 0], ["商品总数", summary?.product_count ?? 0], ["订单总数", summary?.order_count ?? 0]];
      return <><div className="metric-grid">{metrics.map(([label, value]) => <article className="metric-card" key={String(label)}><span>{label}</span><strong>{value}</strong></article>)}</div><div className="dashboard-grid"><section className="panel revenue-panel"><p className="eyebrow">平台成交额</p><h2>{money(summary?.total_revenue ?? 0)}</h2><p>来自 {summary?.paid_order_count ?? 0} 笔有效成交订单</p><div className="summary-line"><span>平均订单金额</span><strong>{money(summary?.average_order_amount ?? 0)}</strong></div></section><section className="panel"><div className="panel-heading"><h2>平台构成</h2><span>当前平台数据</span></div><div className="composition"><div><b>{summary?.store_count ?? 0}</b><span>店铺</span></div><div><b>{summary?.merchant_count ?? 0}</b><span>商家</span></div><div><b>{summary?.product_count ?? 0}</b><span>商品</span></div></div></section></div></>;
    }
    if (view === "users") return users.length ? <section className="table-card"><table><thead><tr><th>账户</th><th>角色</th><th>状态</th><th>注册时间</th><th>操作</th></tr></thead><tbody>{users.map((item) => <tr key={item.id}><td><strong>{item.email}</strong><small>ID {item.id}</small></td><td>{item.role}</td><td><StatusBadge value={item.status} /></td><td>{formatDate(item.created_at)}</td><td><div className="row-actions">{item.status === "ACTIVE" ? <button onClick={() => userStatus(item.id, "SUSPENDED")}>冻结</button> : <button onClick={() => userStatus(item.id, "ACTIVE")}>恢复</button>}<button className="danger-link" onClick={() => userStatus(item.id, "DISABLED")}>禁用</button></div></td></tr>)}</tbody></table></section> : <EmptyState>暂无用户</EmptyState>;
    if (view === "merchants") return merchants.length ? <section className="table-card"><table><thead><tr><th>商家</th><th>状态</th><th>申请时间</th><th>操作</th></tr></thead><tbody>{merchants.map((item) => <tr key={item.id}><td><strong>{item.business_name}</strong><small>User #{item.user_id}</small></td><td><StatusBadge value={item.status} /></td><td>{formatDate(item.created_at)}</td><td><div className="row-actions">{item.status === "PENDING" && <button className="primary" onClick={() => merchantAction(item, "approve")}>批准</button>}{item.status === "ACTIVE" && <button onClick={() => merchantAction(item, "status", "SUSPENDED")}>冻结</button>}{item.status === "SUSPENDED" && <button onClick={() => merchantAction(item, "status", "ACTIVE")}>恢复</button>}</div></td></tr>)}</tbody></table></section> : <EmptyState>暂无商家申请</EmptyState>;
    if (view === "products") return products.length ? <section className="table-card"><table><thead><tr><th>商品</th><th>店铺</th><th>价格</th><th>状态</th><th>操作</th></tr></thead><tbody>{products.map((item) => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.sku}</small></td><td>#{item.store_id}</td><td>{money(item.current_price)}</td><td><StatusBadge value={item.status} /></td><td>{item.status === "ACTIVE" && <button className="danger-link" onClick={() => deactivate(item.id)}>强制下架</button>}</td></tr>)}</tbody></table></section> : <EmptyState>暂无商品</EmptyState>;
    if (view === "orders") return orders.length ? <div className="order-list">{orders.map((order) => <article className="order-card" key={order.id}><header><div><small>{order.order_no}</small><strong>用户 #{order.user_id} · 店铺 #{order.store_id}</strong></div><StatusBadge value={order.status} /></header><div className="order-items">{order.items.map((item) => <span key={item.id}>{item.product_name_snapshot} × {item.quantity}</span>)}</div><footer><span>{formatDate(order.created_at)}</span><strong>{money(order.total_amount)}</strong></footer></article>)}</div> : <EmptyState>暂无平台订单</EmptyState>;
    return logs.length ? <div className="audit-list">{logs.map((item) => <article className="audit-card" key={item.id}><div className="audit-icon">{item.actor_role.slice(0, 1)}</div><div><header><strong>{item.action}</strong><StatusBadge value={item.actor_role} /></header><p>{item.entity_type} #{item.entity_id} · 操作人 #{item.actor_user_id}</p><details><summary>查看状态变化</summary><pre>{JSON.stringify({ before: item.before_data, after: item.after_data }, null, 2)}</pre></details></div><time>{formatDate(item.created_at)}</time></article>)}</div> : <EmptyState>暂无审计日志</EmptyState>;
  }
}
