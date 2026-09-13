export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Role = "CUSTOMER" | "MERCHANT" | "ADMIN";

export type User = {
  id: number;
  email: string;
  role: Role;
  status: string;
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export type Product = {
  id: number;
  store_id: number;
  store_name?: string;
  category_id: number;
  category_name?: string;
  sku: string;
  name: string;
  description?: string | null;
  tags: string[];
  current_price: string;
  inventory_quantity: number;
  sales_count: number;
  images: Array<{ url: string; alt_text: string; is_primary: boolean }>;
  variants: Array<{
    id: number;
    sku: string;
    name: string;
    attributes: Record<string, string>;
    price: string;
  }>;
  has_variants: boolean;
  is_favorite: boolean;
  status?: string;
  created_at?: string;
};

export type Order = {
  id: number;
  order_no: string;
  user_id?: number;
  store_id: number;
  status: string;
  payment_status: string;
  total_amount: string;
  address_snapshot: Record<string, string>;
  items: Array<{
    id: number;
    product_id: number;
    product_name_snapshot: string;
    variant_name_snapshot?: string | null;
    variant_sku_snapshot?: string | null;
    sku_snapshot: string;
    unit_price: string;
    quantity: number;
    subtotal: string;
  }>;
  payments: Array<{
    id: number;
    payment_no: string;
    method: string;
    amount: string;
    status: string;
  }>;
  created_at: string;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(
      response.status,
      data.error?.code ?? "REQUEST_FAILED",
      data.error?.message ?? `请求失败 (${response.status})`,
    );
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "操作失败，请稍后重试";
}

export function money(value: string | number): string {
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY" }).format(Number(value));
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value.endsWith("Z") ? value : `${value}Z`),
  );
}
