"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { AppShell, EmptyState, LoadingState, Notice, StatusBadge } from "./app-shell";
import { api, errorMessage, formatDate, money, Order, Page, Product } from "../lib/api";

type MerchantView = "dashboard" | "store" | "products" | "inventory" | "orders" | "analytics";
type Store = { id: number; name: string; description?: string | null; status: string };
type Category = { id: number; name: string };
type Summary = { today_revenue: string; month_revenue: string; total_revenue: string; paid_order_count: number; average_order_amount: string };
type TopProduct = { product_id: number; product_name: string; quantity_sold: number; revenue: string };
type LowStock = { product_id: number; sku: string; name: string; status: string; quantity: number };

const titles: Record<MerchantView, [string, string]> = {
  dashboard: ["经营概览", "销售、订单与库存的实时摘要。"],
  store: ["店铺资料", "维护向用户展示的经营主体信息。"],
  products: ["商品管理", "创建商品、调价、上下架并维护库存。"],
  inventory: ["库存中心", "查看当前库存并执行可追溯调整。"],
  orders: ["订单处理", "按照 PAID → PROCESSING → SHIPPED 状态机处理订单。"],
  analytics: ["经营分析", "基于已支付订单快照聚合销售表现。"],
};

export function MerchantPage({ view }: { view: MerchantView }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [top, setTop] = useState<TopProduct[]>([]);
  const [low, setLow] = useState<LowStock[]>([]);
  const [store, setStore] = useState<Store | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      if (["dashboard", "analytics"].includes(view)) {
        const [nextSummary, nextTop, nextLow] = await Promise.all([
          api<Summary>("/api/merchant/analytics/summary"),
          api<TopProduct[]>("/api/merchant/analytics/top-products?limit=8"),
          api<Page<LowStock>>("/api/merchant/analytics/low-stock?threshold=5&page_size=20"),
        ]);
        setSummary(nextSummary); setTop(nextTop); setLow(nextLow.items);
      }
      if (view === "store") setStore(await api<Store>("/api/merchant/store"));
      if (["products", "inventory"].includes(view)) {
        const [nextProducts, nextCategories] = await Promise.all([
          api<Product[]>("/api/merchant/products"), api<Category[]>("/api/categories"),
        ]);
        setProducts(nextProducts); setCategories(nextCategories);
      }
      if (view === "orders") setOrders((await api<Page<Order>>("/api/merchant/orders?page_size=50")).items);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally { setLoading(false); }
  }, [view]);

  useEffect(() => { load(); }, [load]);

  async function saveStore(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
    try { setStore(await api<Store>("/api/merchant/store", { method: store ? "PATCH" : "POST", body: JSON.stringify(values) })); setMessage("店铺资料已保存"); } catch (error) { setMessage(errorMessage(error)); }
  }
  async function createProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
    try { await api("/api/merchant/products", { method: "POST", body: JSON.stringify(values) }); event.currentTarget.reset(); setMessage("商品已创建为草稿"); load(); } catch (error) { setMessage(errorMessage(error)); }
  }
  async function productAction(id: number, action: "restock" | "price" | "status" | "delete", value?: string) {
    try {
      if (action === "delete") await api(`/api/merchant/products/${id}`, { method: "DELETE" });
      if (action === "status") await api(`/api/merchant/products/${id}/status`, { method: "POST", body: JSON.stringify({ status: value }) });
      if (action === "restock") await api(`/api/merchant/products/${id}/inventory/restock`, { method: "POST", body: JSON.stringify({ quantity: Number(value), reason: "前端商家工作台进货" }) });
      if (action === "price") await api(`/api/merchant/products/${id}/price`, { method: "POST", body: JSON.stringify({ new_price: value }) });
      setMessage("商品数据已更新"); load();
    } catch (error) { setMessage(errorMessage(error)); }
  }
  async function updateOrder(id: number, status: string) {
    try { await api(`/api/merchant/orders/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }); setMessage("订单状态已更新"); load(); } catch (error) { setMessage(errorMessage(error)); }
  }

  const [title, description] = titles[view];
  return <AppShell title={title} description={description} activePath={`/merchant/${view}`} expectedRole="MERCHANT"><Notice message={message} tone={message.includes("已") ? "success" : "error"} />{loading ? <LoadingState /> : render()}</AppShell>;

  function render() {
    if (view === "dashboard") return <><MetricGrid summary={summary} /><div className="dashboard-grid"><TopProducts items={top} /><LowStock items={low} /></div></>;
    if (view === "analytics") return <><MetricGrid summary={summary} /><section className="panel"><div className="panel-heading"><h2>商品销售排行</h2><span>按成交数量排序</span></div><TopProducts items={top} expanded /></section></>;
    if (view === "store") return <section className="panel narrow-panel"><div className="panel-heading"><h2>{store ? "编辑店铺" : "创建店铺"}</h2>{store && <StatusBadge value={store.status} />}</div><form className="form-grid" onSubmit={saveStore}><label>店铺名称<input name="name" required minLength={2} defaultValue={store?.name} /></label><label>店铺描述<textarea name="description" rows={5} defaultValue={store?.description ?? ""} /></label><button className="primary">{store ? "保存修改" : "创建店铺"}</button></form></section>;
    if (view === "products") return <div className="split-grid wide-left"><section className="panel"><div className="panel-heading"><h2>商品列表</h2><span>{products.length} 件</span></div><ProductTable items={products} action={productAction} /></section><form id="new-product" className="panel form-grid" onSubmit={createProduct}><div className="panel-heading"><h2>新增商品</h2><Link href="/merchant/products/new">独立页面</Link></div><label>商品名称<input name="name" required minLength={2} /></label><label>SKU<input name="sku" required /></label><label>分类<select name="category_id" required><option value="">选择分类</option>{categories.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>价格<input name="current_price" type="number" min="0.01" step="0.01" required /></label><label>描述<textarea name="description" rows={3} /></label><button className="primary">创建草稿</button></form></div>;
    if (view === "inventory") return <section className="panel"><div className="panel-heading"><h2>库存总览</h2><span>每次变更都会生成流水</span></div><ProductTable items={products} action={productAction} inventoryOnly /></section>;
    return orders.length === 0 ? <EmptyState>当前没有店铺订单。</EmptyState> : <div className="order-list">{orders.map((order) => <article className="order-card" id={`order-${order.id}`} key={order.id}><header><div><Link href={`/merchant/orders/${order.id}`}><small>{order.order_no}</small></Link><strong>{formatDate(order.created_at)}</strong></div><StatusBadge value={order.status} /></header><div className="order-items">{order.items.map((item) => <span key={item.id}>{item.product_name_snapshot} × {item.quantity}</span>)}</div><footer><strong>{money(order.total_amount)}</strong><div>{order.status === "PAID" && <button className="primary" onClick={() => updateOrder(order.id, "PROCESSING")}>开始处理</button>}{order.status === "PROCESSING" && <button className="primary" onClick={() => updateOrder(order.id, "SHIPPED")}>确认发货</button>}</div></footer></article>)}</div>;
  }
}

export function MerchantProductForm({ productId }: { productId?: number }) {
  const [product, setProduct] = useState<Product | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(Boolean(productId));
  const [message, setMessage] = useState("");
  useEffect(() => {
    Promise.all([
      api<Category[]>("/api/categories"),
      productId ? api<Product>(`/api/merchant/products/${productId}`) : Promise.resolve(null),
    ]).then(([nextCategories, nextProduct]) => { setCategories(nextCategories); setProduct(nextProduct); }).catch((error) => setMessage(errorMessage(error))).finally(() => setLoading(false));
  }, [productId]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const body = { ...values, category_id: Number(values.category_id) };
    try {
      await api(productId ? `/api/merchant/products/${productId}` : "/api/merchant/products", { method: productId ? "PATCH" : "POST", body: JSON.stringify(body) });
      window.location.href = "/merchant/products";
    } catch (error) { setMessage(errorMessage(error)); }
  }
  return <AppShell title={productId ? "编辑商品" : "新增商品"} description={productId ? "修改商品基础资料；调价和库存变更请使用商品工作台。" : "新商品会以草稿状态创建。"} activePath="/merchant/products" expectedRole="MERCHANT" actions={<Link className="button soft" href="/merchant/products">返回商品管理</Link>}><Notice message={message} tone="error" />{loading ? <LoadingState /> : <form className="panel form-grid narrow-panel" onSubmit={submit}><label>商品名称<input name="name" required minLength={2} defaultValue={product?.name} /></label><label>SKU<input name="sku" required defaultValue={product?.sku} /></label><label>分类<select name="category_id" required defaultValue={product?.category_id}><option value="">选择分类</option>{categories.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>{!productId && <label>初始价格<input name="current_price" type="number" min="0.01" step="0.01" required /></label>}<label>描述<textarea name="description" rows={5} defaultValue={product?.description ?? ""} /></label><button className="primary">{productId ? "保存商品资料" : "创建草稿"}</button></form>}</AppShell>;
}

export function MerchantOrderDetailPage({ orderId }: { orderId: number }) {
  const [order, setOrder] = useState<Order | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => { api<Order>(`/api/merchant/orders/${orderId}`).then(setOrder).catch((error) => setMessage(errorMessage(error))); }, [orderId]);
  return <AppShell title="店铺订单详情" description="查看客户地址、成交快照与支付记录。" activePath="/merchant/orders" expectedRole="MERCHANT" actions={<Link className="button soft" href="/merchant/orders">返回订单处理</Link>}><Notice message={message} tone="error" />{!order ? message ? null : <LoadingState /> : <div className="split-grid"><section className="panel"><div className="panel-heading"><div><p className="eyebrow">{order.order_no}</p><h2>{formatDate(order.created_at)}</h2></div><StatusBadge value={order.status} /></div><div className="table-scroll"><table><thead><tr><th>商品快照</th><th>成交单价</th><th>数量</th><th>小计</th></tr></thead><tbody>{order.items.map((item) => <tr key={item.id}><td>{item.product_name_snapshot}<small>{item.sku_snapshot}</small></td><td>{money(item.unit_price)}</td><td>{item.quantity}</td><td>{money(item.subtotal)}</td></tr>)}</tbody></table></div><div className="summary-total"><span>订单合计</span><strong>{money(order.total_amount)}</strong></div></section><section className="panel"><h2>收货信息</h2><p>{Object.values(order.address_snapshot).filter(Boolean).join(" · ")}</p><h2>支付记录</h2><div className="order-items">{order.payments.length ? order.payments.map((payment) => <span key={payment.id}>{payment.payment_no} · {payment.method} · {payment.status}</span>) : <span>尚无支付记录</span>}</div></section></div>}</AppShell>;
}

function MetricGrid({ summary }: { summary: Summary | null }) {
  const metrics = [["今日销售额", summary?.today_revenue ?? 0], ["本月销售额", summary?.month_revenue ?? 0], ["累计销售额", summary?.total_revenue ?? 0], ["成交订单", summary?.paid_order_count ?? 0]];
  return <div className="metric-grid">{metrics.map(([label, value], index) => <article className="metric-card" key={String(label)}><span>{label}</span><strong>{index < 3 ? money(value) : value}</strong>{index === 3 && <small>平均 {money(summary?.average_order_amount ?? 0)}</small>}</article>)}</div>;
}

function TopProducts({ items, expanded = false }: { items: TopProduct[]; expanded?: boolean }) {
  return <section className={expanded ? "ranking" : "panel"}><div className="panel-heading"><h2>热门商品</h2><span>已支付订单</span></div>{items.length === 0 ? <EmptyState>暂无成交数据</EmptyState> : <div className="ranking-list">{items.map((item, index) => <div key={item.product_id}><b>{String(index + 1).padStart(2, "0")}</b><span>{item.product_name}<small>售出 {item.quantity_sold} 件</small></span><strong>{money(item.revenue)}</strong></div>)}</div>}</section>;
}

function LowStock({ items }: { items: LowStock[] }) {
  return <section className="panel"><div className="panel-heading"><h2>低库存提醒</h2><span>≤ 5 件</span></div>{items.length === 0 ? <EmptyState>库存状态良好</EmptyState> : <div className="low-list">{items.map((item) => <div key={item.product_id}><span><strong>{item.name}</strong><small>{item.sku}</small></span><b>{item.quantity}</b></div>)}</div>}</section>;
}

function ProductTable({ items, action, inventoryOnly = false }: { items: Product[]; action: (id: number, action: "restock" | "price" | "status" | "delete", value?: string) => void; inventoryOnly?: boolean }) {
  if (!items.length) return <EmptyState>还没有商品，请先创建商品。</EmptyState>;
  return <div className="table-scroll"><table><thead><tr><th>商品</th><th>状态</th><th>价格</th><th>库存</th><th>快捷操作</th></tr></thead><tbody>{items.map((item) => <tr id={`product-${item.id}`} key={item.id}><td><strong>{item.name}</strong><small>{item.sku}</small></td><td><StatusBadge value={item.status ?? "DRAFT"} /></td><td>{money(item.current_price)}</td><td><strong>{item.inventory_quantity}</strong></td><td><div className="row-actions"><button onClick={() => { const value = window.prompt("进货数量", "10"); if (value) action(item.id, "restock", value); }}>进货</button>{!inventoryOnly && <><Link className="button" href={`/merchant/products/${item.id}/edit`}>编辑</Link><button onClick={() => { const value = window.prompt("新价格", item.current_price); if (value) action(item.id, "price", value); }}>调价</button><button onClick={() => action(item.id, "status", item.status === "ACTIVE" ? "INACTIVE" : "ACTIVE")}>{item.status === "ACTIVE" ? "下架" : "上架"}</button><button className="danger-link" onClick={() => action(item.id, "delete")}>删除</button></>}</div></td></tr>)}</tbody></table></div>;
}
