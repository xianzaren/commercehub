"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { AppShell, EmptyState, LoadingState, Notice, StatusBadge } from "./app-shell";
import { api, errorMessage, formatDate, money, Order, Page, Product } from "../lib/api";

type Category = { id: number; name: string };
type Cart = {
  id: number | null;
  store_id: number | null;
  total_amount: string;
  items: Array<{
    id: number;
    product_id: number;
    product_name: string;
    sku: string;
    unit_price: string;
    quantity: number;
    available_stock: number;
    subtotal: string;
  }>;
};
type Address = {
  id: number;
  recipient_name: string;
  phone: string;
  province: string;
  city: string;
  district: string;
  detail: string;
  postal_code?: string | null;
  is_default: boolean;
};

function PublicHeader() {
  return <header className="topbar"><Link className="brand" href="/products"><span className="brand-mark">CH</span><span>CommerceHub</span></Link><nav><Link className="active" href="/products">商品</Link><Link href="/cart">购物车</Link><Link href="/orders">订单</Link><Link href="/login">登录</Link></nav></header>;
}

export function ProductsPage({ productId }: { productId?: number }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [product, setProduct] = useState<Product | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("newest");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (productId) {
        setProduct(await api<Product>(`/api/products/${productId}`));
      } else {
        const query = new URLSearchParams({ keyword, sort, page_size: "24" });
        if (category) query.set("category_id", category);
        const data = await api<Page<Product>>(`/api/products?${query}`);
        setProducts(data.items);
      }
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [category, keyword, productId, sort]);

  useEffect(() => {
    api<Category[]>("/api/categories").then(setCategories).catch(() => undefined);
    load();
  }, [load]);

  async function addToCart(id: number) {
    try {
      await api<Cart>("/api/cart/items", { method: "POST", body: JSON.stringify({ product_id: id, quantity: 1 }) });
      setMessage("已加入购物车");
    } catch (error) {
      if (error instanceof Error && "status" in error && (error as { status: number }).status === 401) {
        window.location.href = "/login";
        return;
      }
      setMessage(errorMessage(error));
    }
  }

  if (productId && product) {
    return <main className="public-page"><PublicHeader /><section className="product-detail"><div className="detail-visual"><span>{product.sku}</span><strong>{product.name.slice(0, 2).toUpperCase()}</strong></div><div className="detail-copy"><Link href="/products">← 返回商品列表</Link><p className="eyebrow">PRODUCT #{product.id}</p><h1>{product.name}</h1><p>{product.description || "该商品暂未填写详细说明。"}</p><div className="detail-price">{money(product.current_price)}</div><div className="stock-line"><StatusBadge value={product.inventory_quantity > 0 ? "IN_STOCK" : "OUT_OF_STOCK"} />库存 {product.inventory_quantity}</div><button className="primary" onClick={() => addToCart(product.id)} disabled={!product.inventory_quantity}>加入购物车</button><Notice message={message} tone={message.includes("已加入") ? "success" : "error"} /></div></section></main>;
  }

  return (
    <main className="public-page"><PublicHeader /><section className="catalog-page">
      <div className="catalog-title"><div><p className="eyebrow">CUSTOMER MARKETPLACE</p><h1>商品市场</h1><p>实时价格与库存，结账时由 MySQL 再次锁定校验。</p></div><Link className="button soft" href="/cart">查看购物车 →</Link></div>
      <form className="filterbar" onSubmit={(event) => { event.preventDefault(); load(); }}><input aria-label="关键词" value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索商品名称或描述" /><select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">全部分类</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="newest">最新上架</option><option value="price_asc">价格从低到高</option><option value="price_desc">价格从高到低</option></select><button type="submit">应用筛选</button></form>
      <Notice message={message} tone="error" />
      {loading ? <LoadingState /> : products.length === 0 ? <EmptyState>暂无在售商品。商家补充库存并上架后会显示在这里。</EmptyState> : <div className="product-grid">{products.map((item) => <article className="product-card" key={item.id}><Link className="product-visual" href={`/products/${item.id}`}><span>{item.sku}</span><strong>{item.name.slice(0, 2).toUpperCase()}</strong></Link><div className="product-body"><Link href={`/products/${item.id}`}><h2>{item.name}</h2></Link><p>{item.description || "品质商品，库存实时同步。"}</p><div className="product-meta"><strong>{money(item.current_price)}</strong><span>库存 {item.inventory_quantity}</span></div><button onClick={() => addToCart(item.id)} disabled={!item.inventory_quantity}>加入购物车</button></div></article>)}</div>}
    </section></main>
  );
}

export function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [message, setMessage] = useState("");
  const load = useCallback(() => api<Cart>("/api/cart").then(setCart).catch((error) => setMessage(errorMessage(error))), []);
  useEffect(() => { load(); }, [load]);
  async function update(id: number, quantity: number) { try { setCart(await api<Cart>(`/api/cart/items/${id}`, { method: "PATCH", body: JSON.stringify({ quantity }) })); } catch (error) { setMessage(errorMessage(error)); } }
  async function remove(id: number) { try { await api<void>(`/api/cart/items/${id}`, { method: "DELETE" }); load(); } catch (error) { setMessage(errorMessage(error)); } }
  return <AppShell title="购物车" description="同一个购物车只结算一家店铺的商品。" activePath="/cart" expectedRole="CUSTOMER" actions={<Link className="button soft" href="/products">继续选购</Link>}><Notice message={message} tone="error" />{!cart ? <LoadingState /> : cart.items.length === 0 ? <EmptyState>购物车还是空的。<Link href="/products">去选择商品</Link></EmptyState> : <><div className="table-card"><table><thead><tr><th>商品</th><th>单价</th><th>数量</th><th>小计</th><th /></tr></thead><tbody>{cart.items.map((item) => <tr key={item.id}><td><strong>{item.product_name}</strong><small>{item.sku}</small></td><td>{money(item.unit_price)}</td><td><div className="stepper"><button onClick={() => update(item.id, item.quantity - 1)} disabled={item.quantity <= 1}>−</button><span>{item.quantity}</span><button onClick={() => update(item.id, item.quantity + 1)} disabled={item.quantity >= item.available_stock}>+</button></div></td><td>{money(item.subtotal)}</td><td><button className="danger-link" onClick={() => remove(item.id)}>移除</button></td></tr>)}</tbody></table></div><div className="checkout-bar"><div><span>订单金额</span><strong>{money(cart.total_amount)}</strong></div><Link className="button primary" href="/checkout">去结算</Link></div></>}</AppShell>;
}

export function AddressesPage() {
  const [items, setItems] = useState<Address[]>([]);
  const [message, setMessage] = useState("");
  const load = useCallback(() => api<Address[]>("/api/addresses").then(setItems).catch((error) => setMessage(errorMessage(error))), []);
  useEffect(() => { load(); }, [load]);
  async function create(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); try { await api<Address>("/api/addresses", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) }); event.currentTarget.reset(); setMessage("地址已保存"); load(); } catch (error) { setMessage(errorMessage(error)); } }
  async function makeDefault(id: number) { await api<Address>(`/api/addresses/${id}`, { method: "PATCH", body: JSON.stringify({ is_default: true }) }); load(); }
  async function remove(id: number) { await api<void>(`/api/addresses/${id}`, { method: "DELETE" }); load(); }
  return <AppShell title="收货地址" description="Checkout 会保存地址快照，后续修改不会影响历史订单。" activePath="/profile/addresses" expectedRole="CUSTOMER"><Notice message={message} tone={message.includes("已保存") ? "success" : "error"} /><div className="split-grid"><section className="panel"><h2>地址簿</h2><div className="address-list">{items.map((item) => <article className="address-card" key={item.id}><div><strong>{item.recipient_name} · {item.phone}</strong><p>{item.province} {item.city} {item.district} {item.detail}</p></div>{item.is_default ? <StatusBadge value="DEFAULT" /> : <button className="soft" onClick={() => makeDefault(item.id)}>设为默认</button>}<button className="danger-link" onClick={() => remove(item.id)}>删除</button></article>)}</div></section><form className="panel form-grid" onSubmit={create}><h2>新增地址</h2><label>收件人<input name="recipient_name" required minLength={2} /></label><label>联系电话<input name="phone" required minLength={6} /></label><div className="form-row"><label>省份<input name="province" required /></label><label>城市<input name="city" required /></label></div><label>区县<input name="district" required /></label><label>详细地址<input name="detail" required minLength={2} /></label><label>邮编（选填）<input name="postal_code" /></label><button className="primary">保存地址</button></form></div></AppShell>;
}

export function CheckoutPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressId, setAddressId] = useState("");
  const [method, setMethod] = useState("MOCK_CARD");
  const [message, setMessage] = useState("");
  useEffect(() => { Promise.all([api<Cart>("/api/cart"), api<Address[]>("/api/addresses")]).then(([nextCart, nextAddresses]) => { setCart(nextCart); setAddresses(nextAddresses); const preferred = nextAddresses.find((item) => item.is_default) ?? nextAddresses[0]; if (preferred) setAddressId(String(preferred.id)); }).catch((error) => setMessage(errorMessage(error))); }, []);
  async function checkout() { if (!addressId) { setMessage("请先选择或添加收货地址"); return; } try { await api<Order>("/api/checkout", { method: "POST", body: JSON.stringify({ address_id: Number(addressId), payment_method: method, idempotency_key: `checkout-${crypto.randomUUID()}` }) }); window.location.href = "/orders"; } catch (error) { setMessage(errorMessage(error)); } }
  return <AppShell title="确认结算" description="提交后将在一个事务内创建订单并扣减库存。" activePath="/checkout" expectedRole="CUSTOMER"><Notice message={message} tone="error" /><div className="split-grid"><section className="panel"><h2>订单商品</h2>{cart?.items.map((item) => <div className="summary-line" key={item.id}><span>{item.product_name} × {item.quantity}</span><strong>{money(item.subtotal)}</strong></div>)}<div className="summary-total"><span>应付金额</span><strong>{money(cart?.total_amount ?? 0)}</strong></div></section><section className="panel form-grid"><h2>配送与支付</h2>{addresses.length ? <label>收货地址<select value={addressId} onChange={(event) => setAddressId(event.target.value)}>{addresses.map((item) => <option key={item.id} value={item.id}>{item.recipient_name} · {item.city} {item.detail}</option>)}</select></label> : <EmptyState>还没有地址。<Link href="/profile/addresses">先添加地址</Link></EmptyState>}<label>模拟支付方式<select value={method} onChange={(event) => setMethod(event.target.value)}><option value="MOCK_CARD">模拟银行卡</option><option value="MOCK_WALLET">模拟钱包</option></select></label><button className="primary" onClick={checkout} disabled={!cart?.items.length}>创建订单</button></section></div></AppShell>;
}

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [message, setMessage] = useState("");
  const load = useCallback(() => api<Order[]>("/api/orders").then(setOrders).catch((error) => setMessage(errorMessage(error))), []);
  useEffect(() => { load(); }, [load]);
  async function pay(order: Order) { try { await api(`/api/orders/${order.id}/pay`, { method: "POST", body: JSON.stringify({ method: "MOCK_CARD", amount: order.total_amount, idempotency_key: `pay-${crypto.randomUUID()}`, simulate_failure: false }) }); setMessage("模拟支付成功"); load(); } catch (error) { setMessage(errorMessage(error)); } }
  async function cancel(id: number) { try { await api(`/api/orders/${id}/cancel`, { method: "POST" }); setMessage("订单已取消，库存已返还"); load(); } catch (error) { setMessage(errorMessage(error)); } }
  return <AppShell title="我的订单" description="查看成交快照、支付状态和处理进度。" activePath="/orders" expectedRole="CUSTOMER"><Notice message={message} tone={message.includes("成功") || message.includes("已取消") ? "success" : "error"} />{orders.length === 0 ? <EmptyState>还没有订单。<Link href="/products">去商品市场</Link></EmptyState> : <div className="order-list">{orders.map((order) => <article className="order-card" id={`order-${order.id}`} key={order.id}><header><div><Link href={`/orders/${order.id}`}><small>{order.order_no}</small></Link><strong>{formatDate(order.created_at)}</strong></div><StatusBadge value={order.status} /></header><div className="order-items">{order.items.map((item) => <span key={item.id}>{item.product_name_snapshot} × {item.quantity}</span>)}</div><footer><strong>{money(order.total_amount)}</strong><div>{order.status === "PENDING_PAYMENT" && <button className="primary" onClick={() => pay(order)}>模拟支付</button>}{["PENDING_PAYMENT", "PAID"].includes(order.status) && <button className="soft" onClick={() => cancel(order.id)}>取消订单</button>}</div></footer></article>)}</div>}</AppShell>;
}

export function CustomerOrderDetailPage({ orderId }: { orderId: number }) {
  const [order, setOrder] = useState<Order | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => { api<Order>(`/api/orders/${orderId}`).then(setOrder).catch((error) => setMessage(errorMessage(error))); }, [orderId]);
  return <AppShell title="订单详情" description="订单商品、成交价和地址均为下单时快照。" activePath="/orders" expectedRole="CUSTOMER" actions={<Link className="button soft" href="/orders">返回订单列表</Link>}><Notice message={message} tone="error" />{!order ? message ? null : <LoadingState /> : <OrderDetail order={order} />}</AppShell>;
}

function OrderDetail({ order }: { order: Order }) {
  return <div className="split-grid"><section className="panel"><div className="panel-heading"><div><p className="eyebrow">{order.order_no}</p><h2>{formatDate(order.created_at)}</h2></div><StatusBadge value={order.status} /></div><div className="table-scroll"><table><thead><tr><th>商品快照</th><th>SKU</th><th>成交单价</th><th>数量</th><th>小计</th></tr></thead><tbody>{order.items.map((item) => <tr key={item.id}><td>{item.product_name_snapshot}</td><td>{item.sku_snapshot}</td><td>{money(item.unit_price)}</td><td>{item.quantity}</td><td>{money(item.subtotal)}</td></tr>)}</tbody></table></div><div className="summary-total"><span>订单合计</span><strong>{money(order.total_amount)}</strong></div></section><section className="panel"><h2>配送与支付</h2><p>{Object.values(order.address_snapshot).filter(Boolean).join(" · ")}</p><div className="order-items">{order.payments.length ? order.payments.map((payment) => <span key={payment.id}>{payment.method} · {money(payment.amount)} · {payment.status}</span>) : <span>尚无支付记录</span>}</div></section></div>;
}

export function MerchantApplyPage() {
  const [message, setMessage] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const business_name = String(new FormData(event.currentTarget).get("business_name")); try { const result = await api<{ status: string }>("/api/merchant/applications", { method: "POST", body: JSON.stringify({ business_name }) }); setMessage(`申请已提交，当前状态：${result.status}`); } catch (error) { setMessage(errorMessage(error)); } }
  return <AppShell title="申请成为商家" description="管理员审批后，重新登录即可进入 Merchant 工作台。" activePath="/merchant/apply" expectedRole="CUSTOMER"><section className="panel narrow-panel"><p className="eyebrow">MERCHANT ONBOARDING</p><h2>提交经营主体信息</h2><p className="muted">当前版本为简历演示项目，只需填写商家名称。审批动作将写入审计日志。</p><Notice message={message} tone={message.includes("已提交") ? "success" : "error"} /><form className="form-grid" onSubmit={submit}><label>商家名称<input name="business_name" required minLength={2} maxLength={120} placeholder="例如：星云数码旗舰店" /></label><button className="primary">提交申请</button></form></section></AppShell>;
}
