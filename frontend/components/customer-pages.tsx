"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { AppShell, EmptyState, LoadingState, Notice, ShopHeader, StatusBadge } from "./app-shell";
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
    variant_id: number | null;
    variant_name: string | null;
    variant_sku: string | null;
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

const categoryIcons: Record<string, string> = {
  "数码办公": "💻",
  "居家生活": "🏠",
  "运动户外": "🏃",
  "食品饮品": "🍪",
  "图书文创": "📚",
  "个人护理": "🧴",
  "服饰鞋包": "👕",
  "家用电器": "🫖",
  "母婴用品": "🧸",
  "宠物生活": "🐾",
};

function categoryIcon(name?: string) {
  return categoryIcons[name ?? ""] ?? "🛍️";
}

function PublicHeader() {
  return <ShopHeader activePath="/products" />;
}

function HeartIcon({ filled = false }: { filled?: boolean }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path className={filled ? "filled" : ""} d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" /></svg>;
}

function ProductCard({ item, onFavorite, onAdd }: {
  item: Product;
  onFavorite: (item: Product) => void;
  onAdd: (item: Product) => void;
}) {
  const image = item.images[0];
  return (
    <article className="product-card">
      <div className="product-card-visual-wrap">
        <Link className={`product-visual ${image ? "has-image" : ""}`} href={`/products/${item.id}`}>
          {image ? <img src={image.url} alt={image.alt_text} /> : <strong className="category-symbol">{categoryIcon(item.category_name)}</strong>}
          <span>{item.category_name ?? "精选好物"}</span>
        </Link>
        <button className={`favorite-button ${item.is_favorite ? "active" : ""}`} type="button" onClick={() => onFavorite(item)} aria-label={item.is_favorite ? "取消收藏" : "收藏商品"}><HeartIcon filled={item.is_favorite} /></button>
      </div>
      <div className="product-body">
        <div className="product-tags">{item.tags.slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}</div>
        <Link href={`/products/${item.id}`}><h2>{item.name}</h2></Link>
        <p>{item.description || "用心挑选的品质好物。"}</p>
        <div className="product-meta"><strong>{money(item.current_price)}{item.has_variants && <em>起</em>}</strong><span>{item.inventory_quantity > 5 ? "现货" : item.inventory_quantity > 0 ? `仅剩 ${item.inventory_quantity} 件` : "暂时缺货"}</span></div>
        <div className="product-store"><span>{item.store_name ?? "CommerceHub 精选"}</span><span>{item.sales_count > 0 ? `已售 ${item.sales_count} 件` : "新品"}</span></div>
        {item.has_variants ? <Link className="button product-action-button" href={`/products/${item.id}`}>选择规格</Link> : <button onClick={() => onAdd(item)} disabled={!item.inventory_quantity}>{item.inventory_quantity ? "加入购物车" : "暂时缺货"}</button>}
      </div>
    </article>
  );
}

export function ProductsPage({ productId }: { productId?: number }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [product, setProduct] = useState<Product | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("newest");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedImage, setSelectedImage] = useState("");
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (productId) {
        const nextProduct = await api<Product>(`/api/products/${productId}`);
        setProduct(nextProduct);
        setSelectedImage(nextProduct.images[0]?.url ?? "");
        setSelectedVariantId(nextProduct.variants[0]?.id ?? null);
      } else {
        const query = new URLSearchParams({ keyword: searchKeyword, sort, page_size: "60" });
        if (category) query.set("category_id", category);
        const data = await api<Page<Product>>(`/api/products?${query}`);
        setProducts(data.items);
        setTotal(data.total);
      }
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [category, productId, searchKeyword, sort]);

  useEffect(() => {
    api<Category[]>("/api/categories").then(setCategories).catch(() => undefined);
    load();
  }, [load]);

  useEffect(() => {
    if (productId || !keyword.trim()) {
      setSuggestions([]);
      return;
    }
    const timer = window.setTimeout(() => {
      api<string[]>(`/api/products/suggestions?keyword=${encodeURIComponent(keyword.trim())}`)
        .then(setSuggestions)
        .catch(() => setSuggestions([]));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [keyword, productId]);

  async function addToCart(id: number, variantId?: number | null) {
    try {
      await api<Cart>("/api/cart/items", { method: "POST", body: JSON.stringify({ product_id: id, variant_id: variantId ?? null, quantity: 1 }) });
      setMessage("已加入购物车");
    } catch (error) {
      if (error instanceof Error && "status" in error && (error as { status: number }).status === 401) {
        window.location.href = "/login";
        return;
      }
      setMessage(errorMessage(error));
    }
  }

  async function toggleFavorite(item: Product) {
    try {
      const state = await api<{ is_favorite: boolean }>(`/api/favorites/${item.id}`, { method: item.is_favorite ? "DELETE" : "POST" });
      setProducts((current) => current.map((productItem) => productItem.id === item.id ? { ...productItem, is_favorite: state.is_favorite } : productItem));
      setProduct((current) => current?.id === item.id ? { ...current, is_favorite: state.is_favorite } : current);
      setMessage(state.is_favorite ? "已加入收藏" : "已取消收藏");
    } catch (error) {
      if (error instanceof Error && "status" in error && (error as { status: number }).status === 401) {
        window.location.href = `/login?next=${encodeURIComponent(productId ? `/products/${productId}` : "/products")}`;
        return;
      }
      setMessage(errorMessage(error));
    }
  }

  if (productId && product) {
    const selectedVariant = product.variants.find((item) => item.id === selectedVariantId) ?? null;
    const selectedImageData = product.images.find((item) => item.url === selectedImage) ?? product.images[0];
    return (
      <main className="public-page">
        <PublicHeader />
        <section className="product-detail">
          <div className="product-gallery">
            <div className={`detail-visual ${selectedImageData ? "has-image" : ""}`}>
              {selectedImageData ? <img src={selectedImageData.url} alt={selectedImageData.alt_text} /> : <strong className="category-symbol">{categoryIcon(product.category_name)}</strong>}
              <span>{product.category_name ?? "精选好物"}</span>
            </div>
            {product.images.length > 1 && <div className="gallery-thumbnails">{product.images.map((image) => <button className={selectedImageData?.url === image.url ? "active" : ""} type="button" key={image.url} onClick={() => setSelectedImage(image.url)}><img src={image.url} alt={image.alt_text} /></button>)}</div>}
          </div>
          <div className="detail-copy">
            <Link href="/products">← 返回全部商品</Link>
            <div className="detail-title-row"><div><p className="eyebrow">{product.store_name ?? "精选店铺"}</p><h1>{product.name}</h1></div><button className={`favorite-detail-button ${product.is_favorite ? "active" : ""}`} type="button" onClick={() => toggleFavorite(product)}><HeartIcon filled={product.is_favorite} />{product.is_favorite ? "已收藏" : "收藏"}</button></div>
            <p>{product.description || "用心挑选的品质好物。"}</p>
            <div className="product-tags detail-tags">{product.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
            {product.variants.length > 0 && <section className="variant-picker"><strong>选择规格</strong><div>{product.variants.map((variant) => <button className={selectedVariantId === variant.id ? "active" : ""} type="button" key={variant.id} onClick={() => setSelectedVariantId(variant.id)}><span>{variant.name}</span><small>{Object.values(variant.attributes).join(" · ")}</small></button>)}</div></section>}
            <div className="detail-price">{money(selectedVariant?.price ?? product.current_price)}</div>
            <div className="detail-market-meta"><span>{product.store_name ?? "CommerceHub 精选"}</span><span>{product.sales_count > 0 ? `已售 ${product.sales_count} 件` : "新品上架"}</span></div>
            <div className="stock-line"><StatusBadge value={product.inventory_quantity > 0 ? "IN_STOCK" : "OUT_OF_STOCK"} />{product.inventory_quantity > 0 ? `还剩 ${product.inventory_quantity} 件` : "补货中"}</div>
            <button className="primary detail-cart-button" onClick={() => addToCart(product.id, selectedVariantId)} disabled={!product.inventory_quantity || (product.has_variants && !selectedVariantId)}>{product.has_variants && !selectedVariantId ? "请先选择规格" : "加入购物车"}</button>
            <Notice message={message} tone={message.includes("已加入") || message.includes("收藏") ? "success" : "error"} />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="public-page"><PublicHeader /><section className="catalog-page" id="catalog">
      <div className="catalog-title"><div><p className="eyebrow">今日精选</p><h1>今天，想买点什么？</h1><p>从日常好物到数码装备，轻松挑选你的心仪商品。</p></div><Link className="button soft" href="/cart">查看购物车</Link></div>
      <div className="category-strip" aria-label="商品分类"><button className={!category ? "active" : ""} type="button" onClick={() => setCategory("")}><span>✨</span>全部好物</button>{categories.map((item) => <button className={category === String(item.id) ? "active" : ""} type="button" key={item.id} onClick={() => setCategory(String(item.id))}><span>{categoryIcon(item.name)}</span>{item.name}</button>)}</div>
      <form className="filterbar" onSubmit={(event) => { event.preventDefault(); setSearchKeyword(keyword.trim()); setSuggestions([]); }}><div className="search-field"><input aria-label="关键词" value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="输入关键词，按 Enter 搜索" maxLength={100} autoComplete="off" />{suggestions.length > 0 && <div className="search-suggestions" role="listbox">{suggestions.map((suggestion) => <button type="button" key={suggestion} onClick={() => { setKeyword(suggestion); setSearchKeyword(suggestion); setSuggestions([]); }}>{suggestion}</button>)}</div>}</div><select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">全部分类</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="newest">综合推荐</option><option value="price_asc">价格从低到高</option><option value="price_desc">价格从高到低</option></select><button type="submit">搜索商品</button></form>
      <div className="catalog-summary"><strong>{searchKeyword ? `“${searchKeyword}”的搜索结果` : category ? "分类商品" : "全部商品"}</strong><span>共 {total} 件</span></div>
      <Notice message={message} tone="error" />
      {loading ? <LoadingState /> : products.length === 0 ? <EmptyState>暂时没有找到合适的商品，换个条件试试吧。</EmptyState> : <div className="product-grid">{products.map((item) => <ProductCard item={item} key={item.id} onFavorite={toggleFavorite} onAdd={(productItem) => addToCart(productItem.id)} />)}</div>}
    </section></main>
  );
}

function ProductCollectionPage({ mode }: { mode: "favorites" | "history" }) {
  const [items, setItems] = useState<Product[]>([]);
  const [message, setMessage] = useState("");
  const endpoint = mode === "favorites" ? "/api/favorites" : "/api/history/views";
  const title = mode === "favorites" ? "我的收藏" : "浏览记录";
  const description = mode === "favorites" ? "保存喜欢的商品，方便下次继续挑选。" : "最近浏览过的商品会自动保留在这里。";
  const activePath = mode === "favorites" ? "/favorites" : "/history";

  const load = useCallback(() => api<Product[]>(endpoint).then(setItems).catch((error) => setMessage(errorMessage(error))), [endpoint]);
  useEffect(() => { load(); }, [load]);

  async function toggleFavorite(item: Product) {
    try {
      const state = await api<{ is_favorite: boolean }>(`/api/favorites/${item.id}`, { method: item.is_favorite ? "DELETE" : "POST" });
      if (mode === "favorites" && !state.is_favorite) setItems((current) => current.filter((product) => product.id !== item.id));
      else setItems((current) => current.map((product) => product.id === item.id ? { ...product, is_favorite: state.is_favorite } : product));
      setMessage(state.is_favorite ? "已加入收藏" : "已取消收藏");
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  async function add(item: Product) {
    if (item.has_variants) {
      window.location.href = `/products/${item.id}`;
      return;
    }
    try {
      await api<Cart>("/api/cart/items", { method: "POST", body: JSON.stringify({ product_id: item.id, quantity: 1 }) });
      setMessage("已加入购物车");
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  return (
    <AppShell title={title} description={description} activePath={activePath} expectedRole="CUSTOMER" actions={<Link className="button soft" href="/products">继续逛商品</Link>}>
      <Notice message={message} tone={message.includes("已") ? "success" : "error"} />
      {items.length === 0 ? <EmptyState>{mode === "favorites" ? "还没有收藏商品。" : "还没有浏览记录。"}<Link href="/products">去逛逛</Link></EmptyState> : <div className="product-grid collection-grid">{items.map((item) => <ProductCard item={item} key={item.id} onFavorite={toggleFavorite} onAdd={add} />)}</div>}
    </AppShell>
  );
}

export function FavoritesPage() {
  return <ProductCollectionPage mode="favorites" />;
}

export function ViewHistoryPage() {
  return <ProductCollectionPage mode="history" />;
}

export function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [message, setMessage] = useState("");
  const load = useCallback(() => api<Cart>("/api/cart").then(setCart).catch((error) => setMessage(errorMessage(error))), []);
  useEffect(() => { load(); }, [load]);
  async function update(id: number, quantity: number) { try { setCart(await api<Cart>(`/api/cart/items/${id}`, { method: "PATCH", body: JSON.stringify({ quantity }) })); } catch (error) { setMessage(errorMessage(error)); } }
  async function remove(id: number) { try { await api<void>(`/api/cart/items/${id}`, { method: "DELETE" }); load(); } catch (error) { setMessage(errorMessage(error)); } }
  return <AppShell title="购物车" description="确认商品与数量，准备好后即可结算。" activePath="/cart" expectedRole="CUSTOMER" actions={<Link className="button soft" href="/products">继续选购</Link>}><Notice message={message} tone="error" />{!cart ? <LoadingState /> : cart.items.length === 0 ? <EmptyState>购物车还是空的。<Link href="/products">去选择商品</Link></EmptyState> : <><div className="table-card"><table><thead><tr><th>商品</th><th>单价</th><th>数量</th><th>小计</th><th /></tr></thead><tbody>{cart.items.map((item) => <tr key={item.id}><td><strong>{item.product_name}</strong>{item.variant_name && <small>{item.variant_name} · {item.variant_sku}</small>}</td><td>{money(item.unit_price)}</td><td><div className="stepper"><button onClick={() => update(item.id, item.quantity - 1)} disabled={item.quantity <= 1}>−</button><span>{item.quantity}</span><button onClick={() => update(item.id, item.quantity + 1)} disabled={item.quantity >= item.available_stock}>+</button></div></td><td>{money(item.subtotal)}</td><td><button className="danger-link" onClick={() => remove(item.id)}>移除</button></td></tr>)}</tbody></table></div><div className="checkout-bar"><div><span>合计</span><strong>{money(cart.total_amount)}</strong></div><Link className="button primary" href="/checkout">去结算</Link></div></>}</AppShell>;
}

export function AddressesPage() {
  const [items, setItems] = useState<Address[]>([]);
  const [message, setMessage] = useState("");
  const load = useCallback(() => api<Address[]>("/api/addresses").then(setItems).catch((error) => setMessage(errorMessage(error))), []);
  useEffect(() => { load(); }, [load]);
  async function create(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); try { await api<Address>("/api/addresses", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) }); event.currentTarget.reset(); setMessage("地址已保存"); load(); } catch (error) { setMessage(errorMessage(error)); } }
  async function makeDefault(id: number) { await api<Address>(`/api/addresses/${id}`, { method: "PATCH", body: JSON.stringify({ is_default: true }) }); load(); }
  async function remove(id: number) { await api<void>(`/api/addresses/${id}`, { method: "DELETE" }); load(); }
  return <AppShell title="收货地址" description="管理常用地址，让每次下单更方便。" activePath="/profile/addresses" expectedRole="CUSTOMER"><Notice message={message} tone={message.includes("已保存") ? "success" : "error"} /><div className="split-grid"><section className="panel"><h2>地址簿</h2><div className="address-list">{items.map((item) => <article className="address-card" key={item.id}><div><strong>{item.recipient_name} · {item.phone}</strong><p>{item.province} {item.city} {item.district} {item.detail}</p></div>{item.is_default ? <StatusBadge value="DEFAULT" /> : <button className="soft" onClick={() => makeDefault(item.id)}>设为默认</button>}<button className="danger-link" onClick={() => remove(item.id)}>删除</button></article>)}</div></section><form className="panel form-grid" onSubmit={create}><h2>新增地址</h2><label>收件人<input name="recipient_name" required minLength={2} /></label><label>联系电话<input name="phone" required minLength={6} /></label><div className="form-row"><label>省份<input name="province" required /></label><label>城市<input name="city" required /></label></div><label>区县<input name="district" required /></label><label>详细地址<input name="detail" required minLength={2} /></label><label>邮编（选填）<input name="postal_code" /></label><button className="primary">保存地址</button></form></div></AppShell>;
}

export function CheckoutPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressId, setAddressId] = useState("");
  const [method, setMethod] = useState("MOCK_CARD");
  const [message, setMessage] = useState("");
  useEffect(() => { Promise.all([api<Cart>("/api/cart"), api<Address[]>("/api/addresses")]).then(([nextCart, nextAddresses]) => { setCart(nextCart); setAddresses(nextAddresses); const preferred = nextAddresses.find((item) => item.is_default) ?? nextAddresses[0]; if (preferred) setAddressId(String(preferred.id)); }).catch((error) => setMessage(errorMessage(error))); }, []);
  async function checkout() { if (!addressId) { setMessage("请先选择或添加收货地址"); return; } try { await api<Order>("/api/checkout", { method: "POST", body: JSON.stringify({ address_id: Number(addressId), payment_method: method, idempotency_key: `checkout-${crypto.randomUUID()}` }) }); window.location.href = "/orders"; } catch (error) { setMessage(errorMessage(error)); } }
  return <AppShell title="确认订单" description="选择收货地址和支付方式，确认无误后提交。" activePath="/checkout" expectedRole="CUSTOMER"><Notice message={message} tone="error" /><div className="split-grid"><section className="panel"><h2>商品清单</h2>{cart?.items.map((item) => <div className="summary-line" key={item.id}><span>{item.product_name}{item.variant_name ? ` · ${item.variant_name}` : ""} × {item.quantity}</span><strong>{money(item.subtotal)}</strong></div>)}<div className="summary-total"><span>应付金额</span><strong>{money(cart?.total_amount ?? 0)}</strong></div></section><section className="panel form-grid"><h2>配送与支付</h2>{addresses.length ? <label>收货地址<select value={addressId} onChange={(event) => setAddressId(event.target.value)}>{addresses.map((item) => <option key={item.id} value={item.id}>{item.recipient_name} · {item.city} {item.detail}</option>)}</select></label> : <EmptyState>还没有地址。<Link href="/profile/addresses">先添加地址</Link></EmptyState>}<label>支付方式<select value={method} onChange={(event) => setMethod(event.target.value)}><option value="MOCK_CARD">银行卡</option><option value="MOCK_WALLET">电子钱包</option></select></label><button className="primary" onClick={checkout} disabled={!cart?.items.length}>提交订单</button></section></div></AppShell>;
}

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [message, setMessage] = useState("");
  const load = useCallback(() => api<Order[]>("/api/orders").then(setOrders).catch((error) => setMessage(errorMessage(error))), []);
  useEffect(() => { load(); }, [load]);
  async function pay(order: Order) { try { await api(`/api/orders/${order.id}/pay`, { method: "POST", body: JSON.stringify({ method: "MOCK_CARD", amount: order.total_amount, idempotency_key: `pay-${crypto.randomUUID()}`, simulate_failure: false }) }); setMessage("支付成功"); load(); } catch (error) { setMessage(errorMessage(error)); } }
  async function cancel(id: number) { try { await api(`/api/orders/${id}/cancel`, { method: "POST" }); setMessage("订单已取消，库存已返还"); load(); } catch (error) { setMessage(errorMessage(error)); } }
  return <AppShell title="我的订单" description="查看订单状态、商品信息和配送进度。" activePath="/orders" expectedRole="CUSTOMER"><Notice message={message} tone={message.includes("成功") || message.includes("已取消") ? "success" : "error"} />{orders.length === 0 ? <EmptyState>还没有订单。<Link href="/products">去逛逛商品</Link></EmptyState> : <div className="order-list">{orders.map((order) => <article className="order-card" id={`order-${order.id}`} key={order.id}><header><div><Link href={`/orders/${order.id}`}><small>{order.order_no}</small></Link><strong>{formatDate(order.created_at)}</strong></div><StatusBadge value={order.status} /></header><div className="order-items">{order.items.map((item) => <span key={item.id}>{item.product_name_snapshot}{item.variant_name_snapshot ? ` · ${item.variant_name_snapshot}` : ""} × {item.quantity}</span>)}</div><footer><strong>{money(order.total_amount)}</strong><div>{order.status === "PENDING_PAYMENT" && <button className="primary" onClick={() => pay(order)}>去支付</button>}{["PENDING_PAYMENT", "PAID"].includes(order.status) && <button className="soft" onClick={() => cancel(order.id)}>取消订单</button>}</div></footer></article>)}</div>}</AppShell>;
}

export function CustomerOrderDetailPage({ orderId }: { orderId: number }) {
  const [order, setOrder] = useState<Order | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => { api<Order>(`/api/orders/${orderId}`).then(setOrder).catch((error) => setMessage(errorMessage(error))); }, [orderId]);
  return <AppShell title="订单详情" description="查看这笔订单的商品、配送和支付信息。" activePath="/orders" expectedRole="CUSTOMER" actions={<Link className="button soft" href="/orders">返回订单列表</Link>}><Notice message={message} tone="error" />{!order ? message ? null : <LoadingState /> : <OrderDetail order={order} />}</AppShell>;
}

function OrderDetail({ order }: { order: Order }) {
  return <div className="split-grid"><section className="panel"><div className="panel-heading"><div><p className="eyebrow">订单号 {order.order_no}</p><h2>{formatDate(order.created_at)}</h2></div><StatusBadge value={order.status} /></div><div className="table-scroll"><table><thead><tr><th>商品</th><th>单价</th><th>数量</th><th>小计</th></tr></thead><tbody>{order.items.map((item) => <tr key={item.id}><td>{item.product_name_snapshot}{item.variant_name_snapshot && <small>{item.variant_name_snapshot} · {item.variant_sku_snapshot}</small>}</td><td>{money(item.unit_price)}</td><td>{item.quantity}</td><td>{money(item.subtotal)}</td></tr>)}</tbody></table></div><div className="summary-total"><span>订单合计</span><strong>{money(order.total_amount)}</strong></div></section><section className="panel"><h2>配送与支付</h2><p>{Object.values(order.address_snapshot).filter(Boolean).join(" · ")}</p><div className="order-items">{order.payments.length ? order.payments.map((payment) => <span key={payment.id}>{payment.method === "MOCK_CARD" ? "银行卡" : "电子钱包"} · {money(payment.amount)} · {payment.status === "SUCCESS" ? "支付成功" : payment.status}</span>) : <span>尚无支付记录</span>}</div></section></div>;
}

export function MerchantApplyPage() {
  const [message, setMessage] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const business_name = String(new FormData(event.currentTarget).get("business_name")); try { const result = await api<{ status: string }>("/api/merchant/applications", { method: "POST", body: JSON.stringify({ business_name }) }); setMessage(`申请已提交，当前状态：${result.status}`); } catch (error) { setMessage(errorMessage(error)); } }
  return <AppShell title="商家入驻" description="提交店铺信息，审核通过后即可开始经营。" activePath="/merchant/apply" expectedRole="CUSTOMER"><section className="panel narrow-panel"><p className="eyebrow">开设店铺</p><h2>填写店铺信息</h2><p className="muted">填写你的店铺名称并提交申请，我们会尽快处理。</p><Notice message={message} tone={message.includes("已提交") ? "success" : "error"} /><form className="form-grid" onSubmit={submit}><label>店铺名称<input name="business_name" required minLength={2} maxLength={120} placeholder="例如：星云数码旗舰店" /></label><button className="primary">提交申请</button></form></section></AppShell>;
}
