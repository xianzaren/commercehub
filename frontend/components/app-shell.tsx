"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";

import { api, Role, User } from "../lib/api";

type NavItem = { href: string; label: string };

const navigation: Record<Role, NavItem[]> = {
  CUSTOMER: [
    { href: "/products", label: "商品市场" },
    { href: "/cart", label: "购物车" },
    { href: "/orders", label: "我的订单" },
    { href: "/profile/addresses", label: "收货地址" },
    { href: "/merchant/apply", label: "申请商家" },
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

export function LoadingState({ label = "正在加载数据…" }: { label?: string }) {
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
  return <span className={`badge badge-${key}`}>{value}</span>;
}

export function AppShell({
  title,
  description,
  activePath,
  expectedRole,
  actions,
  children,
}: {
  title: string;
  description?: string;
  activePath: string;
  expectedRole: Role;
  actions?: ReactNode;
  children: ReactNode;
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

  if (loading) return <main className="center-screen"><LoadingState label="正在验证登录状态…" /></main>;
  if (!user) {
    return (
      <main className="center-screen"><section className="auth-required">
        <span className="brand-mark">CH</span><h1>请先登录</h1>
        <p>此页面需要有效的 CommerceHub 会话。</p>
        <Link className="button primary" href={`/login?next=${encodeURIComponent(activePath)}`}>前往登录</Link>
      </section></main>
    );
  }
  if (user.role !== expectedRole) {
    const home = user.role === "ADMIN" ? "/admin/dashboard" : user.role === "MERCHANT" ? "/merchant/dashboard" : "/products";
    return (
      <main className="center-screen"><section className="auth-required">
        <span className="brand-mark">CH</span><h1>当前角色无法访问</h1>
        <p>你以 {user.role} 身份登录，请返回对应工作台。</p>
        <Link className="button primary" href={home}>返回工作台</Link>
      </section></main>
    );
  }

  return (
    <div className={`portal role-${expectedRole.toLowerCase()}`}>
      <aside className="sidebar">
        <Link className="brand" href={navigation[expectedRole][0].href}>
          <span className="brand-mark">CH</span><span>CommerceHub</span>
        </Link>
        <div className="role-label">{expectedRole} WORKSPACE</div>
        <nav className="side-nav" aria-label={`${expectedRole} 导航`}>
          {navigation[expectedRole].map((item) => (
            <Link className={activePath === item.href ? "active" : ""} href={item.href} key={item.href}>{item.label}</Link>
          ))}
        </nav>
        <div className="account-card">
          <div className="avatar">{user.email.slice(0, 1).toUpperCase()}</div>
          <div><strong>{user.email}</strong><span>{user.role}</span></div>
          <button className="icon-button" onClick={logout} title="退出登录">↗</button>
        </div>
      </aside>
      <main className="portal-main">
        <header className="page-header">
          <div><p className="eyebrow">COMMERCEHUB / {expectedRole}</p><h1>{title}</h1>{description && <p>{description}</p>}</div>
          {actions && <div className="header-actions">{actions}</div>}
        </header>
        {children}
      </main>
    </div>
  );
}
