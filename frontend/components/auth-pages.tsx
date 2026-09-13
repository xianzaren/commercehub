"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { api, errorMessage, User } from "../lib/api";

function destination(user: User): string {
  if (user.role === "ADMIN") return "/admin/dashboard";
  if (user.role === "MERCHANT") return "/merchant/dashboard";
  return "/products";
}

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      if (mode === "register") {
        await api<User>("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      }
      const result = await api<{ user: User }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      window.location.href = destination(result.user);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-story">
        <Link className="brand" href="/products"><span className="brand-mark">CH</span><span>CommerceHub</span></Link>
        <div>
          <p className="eyebrow">欢迎来到 CommerceHub</p>
          <h1>发现好物，享受简单自在的购物体验。</h1>
          <p>精选日常好物，轻松管理订单、收货地址和配送进度。</p>
        </div>
        <div className="tech-strip"><span>精选好物</span><span>便捷下单</span><span>订单随时查</span></div>
      </section>
      <section className="auth-form-panel">
        <form className="form-card" onSubmit={submit}>
          <p className="eyebrow">{mode === "login" ? "欢迎回来" : "加入我们"}</p>
          <h2>{mode === "login" ? "登录账户" : "创建新账户"}</h2>
          <p>{mode === "login" ? "登录后继续选购，并查看你的订单。" : "注册后即可收藏心仪好物并开始购物。"}</p>
          {message && <div className="notice-box error" role="alert">{message}</div>}
          <label>邮箱<input type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>
          <label>密码<input type="password" required minLength={8} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="至少 8 位，包含字母和数字" /></label>
          <button className="primary" type="submit" disabled={busy}>{busy ? "正在处理…" : mode === "login" ? "登录" : "注册并登录"}</button>
          <div className="form-foot">
            {mode === "login" ? <>还没有账户？<Link href="/register">立即注册</Link></> : <>已有账户？<Link href="/login">返回登录</Link></>}
          </div>
        </form>
      </section>
    </main>
  );
}
