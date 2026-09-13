"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";

import { api, Role, User } from "../lib/api";

type NavItem = { href: string; label: string };

const navigation: Record<Role, NavItem[]> = {
  CUSTOMER: [
    { href: "/products", label: "逛商品" },
    { href: "/favorites", label: "我的收藏" },
    { href: "/history", label: "浏览记录" },
    { href: "/orders", label: "我的订单" },
    { href: "/profile/addresses", label: "收货地址" },
    { href: "/merchant/apply", label: "商家入驻" },
  ],
  MERCHANT: [
    { href: "/merchant/dashboard", label: "经营概览" },
    { href: "/merchant/store", label: "店铺资料" },
    { href: "/merchant/products", label: "商品管理" },
    { href: "/merchant/inventory", label: "库存中心" },
    { href: "/merchant/orders", label: "订单处理" },
    { href: "/merchant/analytics", label: "经营分析" },
  ],
  ADMIN: [
    { href: "/admin/dashboard", label: "平台概览" },
    { href: "/admin/users", label: "用户管理" },
    { href: "/admin/merchants", label: "商家审核" },
    { href: "/admin/products", label: "商品治理" },
    { href: "/admin/orders", label: "平台订单" },
    { href: "/admin/audit", label: "审计日志" },
  ],
};

const statusLabels: Record<string, string> = {
  ACTIVE: "正常", INACTIVE: "已下架", PAID: "已支付", SHIPPED: "已发货",
  COMPLETED: "已完成", DEFAULT: "默认地址", IN_STOCK: "现货", OUT_OF_STOCK: "暂时缺货",
  PENDING: "待审核", PENDING_PAYMENT: "待支付", PROCESSING: "处理中", DRAFT: "草稿",
  SUSPENDED: "已冻结", DISABLED: "已禁用", CANCELLED: "已取消", DELETED: "已删除",
  FAILED: "失败", CUSTOMER: "用户", MERCHANT: "商家", ADMIN: "管理员",
};

function CartIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3 4h2l2.3 10.1a2 2 0 0 0 2 1.6h7.9a2 2 0 0 0 1.9-1.4L21 8H7" /><circle cx="10" cy="20" r="1.3" /><circle cx="18" cy="20" r="1.3" /></svg>;
}

function UserIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></svg>;
}

function ChevronIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="m7 10 5 5 5-5" /></svg>;
}

function LogoutIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10" /></svg>;
}

function dashboardFor(role: Role) {
  if (role === "ADMIN") return "/admin/dashboard";
  if (role === "MERCHANT") return "/merchant/dashboard";
  return "/profile";
}

export function ShopHeader({ activePath, user: suppliedUser, onLogout }: { activePath: string; user?: User | null; onLogout?: () => Promise<void> }) {
  const [sessionUser, setSessionUser] = useState<User | null>(suppliedUser ?? null);
  const user = suppliedUser === undefined ? sessionUser : suppliedUser;

  useEffect(() => {
    if (suppliedUser !== undefined) return;
    api<User>("/api/auth/me").then(setSessionUser).catch(() => setSessionUser(null));
  }, [suppliedUser]);

  async function logout() {
    if (onLogout) await onLogout();
    else {
      await api<void>("/api/auth/logout", { method: "POST" });
      window.location.href = "/products";
    }
  }

  return (
    <header className="shop-header">
      <Link className="brand shop-brand" href="/products" aria-label="CommerceHub 首页">
        <span className="brand-mark">CH</span><span>CommerceHub</span>
      </Link>
      <nav className="shop-nav" aria-label="商城导航">
        <Link className={activePath === "/products" ? "active" : ""} href="/products">首页</Link>
        <Link href="/products#catalog">全部商品</Link>
        <Link className={activePath === "/favorites" ? "active" : ""} href="/favorites">收藏</Link>
        <Link className={activePath.startsWith("/orders") ? "active" : ""} href="/orders">我的订单</Link>
      </nav>
      <div className="shop-actions">
        <Link className={`cart-link ${activePath === "/cart" ? "active" : ""}`} href="/cart" aria-label="打开购物车">
          <CartIcon /><span>购物车</span>
        </Link>
        {user ? (
          <div className="account-menu-wrap">
            <button className="avatar-button" type="button" aria-haspopup="menu" aria-label="打开账户菜单">
              <span className="avatar">{user.email.slice(0, 1).toUpperCase()}</span>
              <span className="account-name">{user.email.split("@")[0]}</span>
              <ChevronIcon />
            </button>
            <div className="account-menu" role="menu">
              <div className="account-menu-head"><strong>{user.email}</strong><span>{statusLabels[user.role]}</span></div>
              <Link role="menuitem" href={dashboardFor(user.role)}><UserIcon />{user.role === "CUSTOMER" ? "个人中心" : "进入工作台"}</Link>
              {user.role === "CUSTOMER" && <Link role="menuitem" href="/profile/addresses">收货地址</Link>}
              {user.role === "CUSTOMER" && <Link role="menuitem" href="/favorites">我的收藏</Link>}
              {user.role === "CUSTOMER" && <Link role="menuitem" href="/history">浏览记录</Link>}
              {user.role === "CUSTOMER" && <Link role="menuitem" href="/orders">我的订单</Link>}
              <button role="menuitem" type="button" onClick={logout}><LogoutIcon />退出登录</button>
            </div>
          </div>
        ) : (
          <div className="guest-actions"><Link href="/login">登录</Link><Link className="button primary compact" href="/register">免费注册</Link></div>
        )}
      </div>
    </header>
  );
}

export function LoadingState({ label = "正在加载…" }: { label?: string }) {
  return <div className="state-card"><span className="spinner" />{label}</div>;
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}

export function Notice({ message, tone = "info" }: { message: string; tone?: "info" | "error" | "success" }) {
  if (!message) return null;
  return <div className={`notice-box ${tone}`} role="status">{message}</div>;
}

export function StatusBadge({ value }: { value: string }) {
  const key = value.toLowerCase().replaceAll("_", "-");
  return <span className={`badge badge-${key}`}>{statusLabels[value] ?? value}</span>;
}

export function AppShell({ title, description, activePath, expectedRole, actions, children }: {
  title: string; description?: string; activePath: string; expectedRole: Role; actions?: ReactNode; children: ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<User>("/api/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  async function logout() {
    await api<void>("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  if (loading) return <main className="center-screen"><LoadingState label="正在进入账户…" /></main>;
  if (!user) {
    return <main className="center-screen"><section className="auth-required"><span className="brand-mark">CH</span><h1>请先登录</h1><p>登录后即可查看账户中的订单与资料。</p><Link className="button primary" href={`/login?next=${encodeURIComponent(activePath)}`}>前往登录</Link></section></main>;
  }
  if (user.role !== expectedRole) {
    return <main className="center-screen"><section className="auth-required"><span className="brand-mark">CH</span><h1>这个页面不属于当前账户</h1><p>请返回你的账户首页继续操作。</p><Link className="button primary" href={dashboardFor(user.role)}>返回账户首页</Link></section></main>;
  }

  if (expectedRole === "CUSTOMER") {
    return (
      <div className="shop-shell">
        <ShopHeader activePath={activePath} user={user} onLogout={logout} />
        <main className="shop-main">
          <header className="shop-page-header"><div><p className="eyebrow">我的账户</p><h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="header-actions">{actions}</div>}</header>
          {children}
        </main>
      </div>
    );
  }

  return (
    <div className={`portal role-${expectedRole.toLowerCase()}`}>
      <aside className="sidebar">
        <Link className="brand" href={navigation[expectedRole][0].href}><span className="brand-mark">CH</span><span>CommerceHub</span></Link>
        <div className="role-label">{expectedRole === "MERCHANT" ? "商家中心" : "平台管理"}</div>
        <nav className="side-nav" aria-label={`${statusLabels[expectedRole]}导航`}>{navigation[expectedRole].map((item) => <Link className={activePath === item.href ? "active" : ""} href={item.href} key={item.href}>{item.label}</Link>)}</nav>
        <div className="account-card"><div className="avatar">{user.email.slice(0, 1).toUpperCase()}</div><div><strong>{user.email}</strong><span>{statusLabels[user.role]}</span></div><button className="icon-button" onClick={logout} title="退出登录"><LogoutIcon /></button></div>
      </aside>
      <main className="portal-main">
        <header className="page-header"><div><p className="eyebrow">{expectedRole === "MERCHANT" ? "商家中心" : "平台管理"}</p><h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="header-actions">{actions}</div>}</header>
        {children}
      </main>
    </div>
  );
}
