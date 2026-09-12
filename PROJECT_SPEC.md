# CommerceHub 多角色电商交易与库存管理平台

**项目类型：** MySQL 数据库应用 / Python 后端 / Web 全栈 / 自动化测试  
**目标用途：** R4「软件开发 / 数据应用 / 金融科技技术」简历项目  
**推荐技术栈：** FastAPI + SQLAlchemy 2.x + MySQL 8 + Alembic + Next.js + TypeScript + Docker Compose + pytest + GitHub Actions  
**开发方式：** 分阶段交付，先架构与数据库，再业务、测试和前端；禁止一次性生成“完整商城”后再补结构。

---

## 1. 项目目标

构建一个可供 **普通用户（CUSTOMER）**、**商家（MERCHANT）** 和 **管理员（ADMIN）** 使用的多角色电商交易与库存管理平台。项目重点不是复刻大型电商平台的全部功能，而是完整展示以下工程能力：

1. 关系型数据库建模、主外键与约束设计；
2. MySQL 事务、并发控制、行级锁与数据一致性；
3. API / Service / Repository / Database 分层架构；
4. 登录认证、密码哈希、JWT 与 RBAC 权限控制；
5. 商品、库存、购物车、订单、支付、商家收益等业务流程；
6. 商品价格历史、库存流水、审计日志等可追溯设计；
7. 索引设计与 EXPLAIN 查询计划分析；
8. pytest 单元测试、集成测试与关键业务流程测试；
9. Docker Compose 本地部署与 GitHub Actions 持续集成；
10. Next.js 多角色可交互前端。

项目最终应达到“可以本地真实运行、可以演示完整交易闭环、可以通过测试验证关键数据一致性”的标准，而不是仅提供静态页面或 CRUD Demo。

---

## 2. 核心设计原则

### 2.1 分层架构

后端必须按以下调用链组织：

```text
Frontend Layer
      ↓ HTTP/JSON
API / Router Layer
      ↓
Service Layer
      ↓
Repository / Data Access Layer
      ↓
SQLAlchemy ORM
      ↓
MySQL 8
```

约束：

- API 层仅负责路由、鉴权、参数接收和响应；
- Service 层负责业务逻辑、事务边界和权限规则；
- Repository 层负责数据库读写；
- API 层不得直接写 SQL 或直接操作 ORM Session；
- 前端不得绕过后端直接访问数据库；
- 测试层独立存在，并覆盖 Service、Repository 和 API 关键逻辑。

### 2.2 数据一致性优先

系统必须将“订单创建、订单明细生成、库存扣减、库存流水、支付记录”等视为一个完整业务事务。任何关键步骤失败时，应整体回滚。

### 2.3 可追溯性

以下信息必须保存历史记录，而不是仅覆盖当前值：

- 商品历史价格；
- 库存变化流水；
- 管理员关键操作日志；
- 订单成交时的商品名称快照与成交单价；
- 支付状态变化时间。

### 2.4 真实项目感，而非过度复杂

项目应体现真实工程逻辑，但不实现真实第三方支付、复杂推荐系统、物流 API、优惠券中心、分布式消息队列等非核心模块。若主流程完成后仍有余力，可作为扩展项。

---

## 3. 技术栈

| 层级 | 技术 | 用途 |
|---|---|---|
| Frontend | Next.js + TypeScript | 用户端、商家端、管理员端页面 |
| UI | 可选 Tailwind CSS | 基础布局与组件样式 |
| Backend | FastAPI | REST API |
| Validation | Pydantic | 请求/响应校验 |
| ORM | SQLAlchemy 2.x | 数据映射与事务管理 |
| Database | MySQL 8 | 核心关系型数据库 |
| Migration | Alembic | Schema 版本管理 |
| Auth | JWT + Argon2/bcrypt | 登录认证和密码安全 |
| Testing | pytest + httpx/TestClient | 单元/集成/API 测试 |
| Deployment | Docker + Docker Compose | 本地一致性环境 |
| CI | GitHub Actions | 自动测试 |
| Version Control | Git | 版本管理 |

建议优先使用成熟、稳定、易维护的依赖，不为了“技术栈丰富”增加不必要中间件。

---

## 4. 推荐项目目录

```text
commercehub/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   ├── auth.py
│   │   │   ├── customer/
│   │   │   ├── merchant/
│   │   │   └── admin/
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── product_service.py
│   │   │   ├── inventory_service.py
│   │   │   ├── cart_service.py
│   │   │   ├── order_service.py
│   │   │   ├── payment_service.py
│   │   │   └── admin_service.py
│   │   ├── repositories/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── permissions.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt 或 pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── services/
│   ├── types/
│   └── Dockerfile
├── docs/
│   ├── architecture.md
│   ├── erd.md
│   ├── api.md
│   └── database-decisions.md
├── scripts/
│   └── seed_data.py
├── .github/
│   └── workflows/
│       └── test.yml
├── docker-compose.yml
├── .env.example
├── README.md
└── LICENSE（可选）
```

---

## 5. 用户角色与权限

### 5.1 CUSTOMER

可执行：

- 注册、登录、退出；
- 浏览商品；
- 按关键词搜索；
- 按分类、价格区间筛选；
- 按价格或创建时间排序；
- 查看商品详情；
- 加入购物车；
- 修改购物车数量；
- 删除购物车条目；
- 管理收货地址；
- 结账并生成订单；
- 使用模拟支付；
- 查看订单列表和订单详情；
- 取消符合规则的未处理订单；
- 确认收货（可选但推荐）。

禁止：

- 修改其他用户购物车或订单；
- 访问商家/管理员 API；
- 购买下架、删除、库存不足商品。

### 5.2 MERCHANT

商家账户状态建议：

```text
PENDING → ACTIVE → SUSPENDED
              ↓
           CLOSED（可选）
```

可执行：

- 申请成为商家；
- 经管理员审批后创建/维护店铺；
- 新增商品；
- 编辑商品信息；
- 商品上架/下架；
- 进货；
- 手动库存调整（需原因）；
- 商品调价；
- 查看自身店铺订单；
- 更新订单处理/发货状态；
- 查看销售额、订单量、平均订单金额、热门商品、低库存商品；
- 查看库存流水和价格历史。

权限规则：商家只能操作自己店铺的数据，禁止跨店访问或修改。

### 5.3 ADMIN

可执行：

- 查看用户列表；
- 冻结/解冻用户；
- 审核商家申请；
- 冻结/解冻商家；
- 查看所有店铺、商品、订单；
- 强制下架违规商品；
- 查看平台级销售统计；
- 查看审计日志；
- 查看异常库存/低库存信息；
- 对重要管理操作写入 audit_logs。

---

## 6. 认证与安全

### 6.1 账户

`users` 统一保存登录账户，至少包含：

```text
id
email
password_hash
role              CUSTOMER | MERCHANT | ADMIN
status            ACTIVE | SUSPENDED | DISABLED
created_at
updated_at
```

要求：

- email 唯一；
- 禁止明文密码；
- 使用 Argon2 或 bcrypt 哈希；
- JWT Access Token；
- 可选 Refresh Token；
- 认证错误返回统一、明确的 HTTP 状态码；
- 敏感配置只能通过环境变量传入。

### 6.2 RBAC

后端必须实现角色权限依赖，例如：

```text
/customer/*  → CUSTOMER
/merchant/*  → MERCHANT
/admin/*     → ADMIN
```

但只按角色仍不足够。商家访问商品/订单时还必须检查资源所有权。

---

## 7. 数据库核心模型

至少实现以下表。

### 7.1 users

账户信息与角色。

### 7.2 merchants

```text
id
user_id FK -> users.id
business_name
status
approved_at
created_at
updated_at
```

### 7.3 stores

```text
id
merchant_id FK
name
description
status
created_at
updated_at
```

初版可限制一个 merchant 一个 store，以降低复杂度；Schema 仍可保持可扩展。

### 7.4 categories

```text
id
name
parent_id nullable FK -> categories.id
status
```

### 7.5 products

```text
id
store_id FK
category_id FK
sku
name
description
current_price DECIMAL
status DRAFT | ACTIVE | INACTIVE | DELETED
created_at
updated_at
deleted_at nullable
```

要求：

- 金额必须使用 DECIMAL，禁止 float；
- 商品删除采用 soft delete；
- sku 在合理范围内唯一；
- 下架和删除商品不能继续购买。

### 7.6 product_prices

```text
id
product_id FK
old_price
new_price
changed_by
changed_at
```

每次调价必须写入历史表。

### 7.7 inventory

```text
product_id PK/FK
quantity
reserved_quantity（可选）
updated_at
version（可选，用于乐观锁实验）
```

### 7.8 inventory_transactions

```text
id
product_id FK
type RESTOCK | SALE | ADJUSTMENT | RETURN | RELEASE
quantity_change
quantity_before
quantity_after
reference_type
reference_id
reason
created_by
created_at
```

任何库存变化必须产生流水。

### 7.9 carts

```text
id
user_id FK
status ACTIVE | CHECKED_OUT | ABANDONED
created_at
updated_at
```

### 7.10 cart_items

```text
id
cart_id FK
product_id FK
quantity
created_at
updated_at
```

同一购物车的同一商品应有唯一约束，避免重复行。

### 7.11 addresses

保存用户收货地址。不要把地址只存在 users 表。

### 7.12 orders

```text
id
order_no UNIQUE
user_id FK
address_snapshot JSON/TEXT
status
subtotal
total_amount
payment_status
created_at
updated_at
```

推荐订单状态：

```text
PENDING_PAYMENT
PAID
PROCESSING
SHIPPED
COMPLETED
CANCELLED
```

### 7.13 order_items

```text
id
order_id FK
product_id FK
store_id FK
product_name_snapshot
sku_snapshot
unit_price
quantity
subtotal
```

关键规则：订单历史价格必须保存于 `order_items.unit_price`，查询历史订单时不能读取当前 `products.current_price` 重新计算。

### 7.14 payments

```text
id
order_id FK
payment_no UNIQUE
method MOCK_CARD | MOCK_WALLET
amount
status PENDING | PAID | FAILED | REFUNDED
paid_at
created_at
```

本项目只实现模拟支付。

### 7.15 audit_logs

```text
id
actor_user_id
actor_role
action
entity_type
entity_id
before_data JSON nullable
after_data JSON nullable
created_at
```

重点记录商家审批、账户冻结、商品强制下架等操作。

### 7.16 merchant_settlements（第二阶段可选）

若 MVP 主流程稳定，再加入商家结算表。初版收益统计可直接从已完成订单聚合。

---

## 8. 数据关系要求

需要在 `docs/erd.md` 中提供 Mermaid ER 图或其他文本可维护 ERD。

至少明确：

```text
User 1 ─── 0..1 Merchant
Merchant 1 ─── N Store
Store 1 ─── N Product
Category 1 ─── N Product
Product 1 ─── 1 Inventory
Product 1 ─── N InventoryTransaction
Product 1 ─── N ProductPrice
User 1 ─── N Address
User 1 ─── N Order
Order 1 ─── N OrderItem
Order 1 ─── N Payment
Cart 1 ─── N CartItem
Product 1 ─── N CartItem
```

外键删除行为（CASCADE / RESTRICT / SET NULL）必须明确说明，不允许全部无脑 CASCADE。

---

## 9. 核心业务流程

### 9.1 商家开店

```text
用户注册
→ 申请 MERCHANT
→ merchant.status = PENDING
→ ADMIN 审核
→ merchant.status = ACTIVE
→ 创建店铺
→ 创建商品
→ 初始进货
→ 商品上架
```

未审核商家不得上架和销售商品。

### 9.2 商品进货

```text
Merchant request
→ 检查商品所有权
→ 验证 quantity > 0
→ 开启事务
→ 锁定 inventory row
→ 更新 inventory.quantity
→ 写 inventory_transactions(type=RESTOCK)
→ commit
```

### 9.3 商品调价

```text
检查商家所有权
→ 校验新价格 > 0
→ 记录 old_price
→ 更新 products.current_price
→ 写 product_prices
→ commit
```

### 9.4 用户购物车

加入购物车时验证商品可售，但最终库存校验必须在 Checkout 再做一次，不能仅依赖加入购物车时的库存。

### 9.5 Checkout / 下单事务

这是整个项目最关键流程。

建议逻辑：

```text
BEGIN TRANSACTION

1. 查询并锁定用户 ACTIVE cart
2. 查询 cart_items
3. 验证购物车非空
4. 查询商品，并验证状态 ACTIVE
5. 按固定顺序锁定相关 inventory rows
6. 再次检查库存
7. 读取当前成交价格
8. 计算 subtotal / total_amount
9. 创建 orders
10. 创建 order_items（保存名称、SKU、成交价快照）
11. 扣减 inventory
12. 写 inventory_transactions(type=SALE)
13. 创建 payments(status=PENDING)
14. 将 cart 标记 CHECKED_OUT 或清空条目

COMMIT
```

任何步骤异常：

```text
ROLLBACK
```

### 9.6 模拟支付

支付服务支持：

- 正常支付成功；
- 可通过测试参数模拟支付失败；
- 重复支付必须具备幂等保护；
- 支付金额必须与订单金额一致。

是否在支付前扣库存需在架构阶段明确。本项目推荐为了降低复杂度，在 Checkout 阶段完成订单创建和库存扣减，并提供订单超时/取消后的库存归还逻辑作为扩展；若实现该方案，必须在文档中说明取舍。

### 9.7 订单取消

至少支持：

- `PENDING_PAYMENT` 或符合业务规则的早期状态可取消；
- 取消时若已经扣减库存，应在事务中恢复库存并写 RETURN/RELEASE 库存流水；
- 已发货订单不可直接取消。

---

## 10. 并发控制与超卖防护

必须实现并测试“最后一件商品”的并发购买场景。

基本方案：

- MySQL InnoDB；
- Checkout 在事务内对库存记录使用行级锁；
- SQLAlchemy 可使用 `SELECT ... FOR UPDATE`；
- 多商品订单锁库存时按稳定顺序（例如 product_id 升序）加锁，减少死锁风险；
- 数据库层不得允许库存最终变为负数；
- 并发失败应返回清晰业务错误，而不是 500。

验收测试：

```text
Given: product stock = 1
When: customer A 和 customer B 并发结账各购买 1 件
Then: 只能一个订单成功
And: inventory.quantity = 0
And: 只存在一条成功 SALE 流水
And: 另一个请求返回库存不足
```

---

## 11. 搜索、索引与查询优化

用户商品搜索至少支持：

- keyword；
- category；
- min_price；
- max_price；
- status=ACTIVE；
- price ascending / descending；
- created_at sort；
- pagination。

订单查询支持按：

- user / merchant；
- order status；
- created_at range；
- order_no。

数据库至少设计：

- 单列索引；
- 一个合理的组合索引；
- 唯一索引（email、order_no、payment_no 等）。

必须在 `docs/database-decisions.md` 中至少记录一个查询优化案例：

1. 原始查询；
2. `EXPLAIN` 结果；
3. 新增/调整索引；
4. 优化后的 `EXPLAIN`；
5. 为什么这样设计。

不要为了展示索引而对所有字段建索引。

---

## 12. REST API 范围

路由名称可由 Codex 适当调整，但功能必须覆盖。

### 12.1 Auth

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
POST /api/auth/refresh          optional
```

### 12.2 Customer

```text
GET    /api/products
GET    /api/products/{id}
GET    /api/categories
GET    /api/cart
POST   /api/cart/items
PATCH  /api/cart/items/{id}
DELETE /api/cart/items/{id}
GET    /api/addresses
POST   /api/addresses
PATCH  /api/addresses/{id}
DELETE /api/addresses/{id}
POST   /api/checkout
GET    /api/orders
GET    /api/orders/{id}
POST   /api/orders/{id}/cancel
POST   /api/orders/{id}/pay
POST   /api/orders/{id}/confirm-receipt   optional
```

### 12.3 Merchant

```text
POST   /api/merchant/apply
GET    /api/merchant/profile
POST   /api/merchant/store
PATCH  /api/merchant/store
GET    /api/merchant/products
POST   /api/merchant/products
GET    /api/merchant/products/{id}
PATCH  /api/merchant/products/{id}
POST   /api/merchant/products/{id}/activate
POST   /api/merchant/products/{id}/deactivate
POST   /api/merchant/products/{id}/restock
POST   /api/merchant/products/{id}/adjust-stock
POST   /api/merchant/products/{id}/change-price
GET    /api/merchant/products/{id}/inventory-history
GET    /api/merchant/products/{id}/price-history
GET    /api/merchant/orders
GET    /api/merchant/orders/{id}
PATCH  /api/merchant/orders/{id}/status
GET    /api/merchant/analytics/summary
GET    /api/merchant/analytics/top-products
GET    /api/merchant/analytics/low-stock
```

### 12.4 Admin

```text
GET  /api/admin/users
POST /api/admin/users/{id}/suspend
POST /api/admin/users/{id}/activate
GET  /api/admin/merchants
POST /api/admin/merchants/{id}/approve
POST /api/admin/merchants/{id}/suspend
GET  /api/admin/products
POST /api/admin/products/{id}/force-deactivate
GET  /api/admin/orders
GET  /api/admin/audit-logs
GET  /api/admin/analytics/summary
```

所有列表接口必须支持分页。

---

## 13. 前端页面

### 13.1 公共/用户端

```text
/login
/register
/products
/products/[id]
/cart
/checkout
/orders
/orders/[id]
/profile
/profile/addresses
```

### 13.2 商家端

```text
/merchant/apply
/merchant/dashboard
/merchant/store
/merchant/products
/merchant/products/new
/merchant/products/[id]/edit
/merchant/inventory
/merchant/orders
/merchant/orders/[id]
/merchant/analytics
```

Dashboard 至少显示：

- 今日/本月销售额；
- 累计订单量；
- 平均订单金额；
- 销量 Top 商品；
- 低库存商品。

### 13.3 管理员端

```text
/admin/dashboard
/admin/users
/admin/merchants
/admin/products
/admin/orders
/admin/audit
```

前端优先保证功能完整、状态清晰和可演示，不追求复杂视觉设计。

---

## 14. 测试要求

### 14.1 测试分层

```text
unit/
  service logic
  validators
  price/order calculations

integration/
  repository + MySQL
  transaction behavior
  API + test database

e2e/
  merchant onboarding
  customer purchase flow
  admin controls
```

### 14.2 必测场景

| 场景 | 预期 |
|---|---|
| 错误密码登录 | 401 |
| CUSTOMER 调管理员 API | 403 |
| MERCHANT 修改别家商品 | 403 |
| 未审核商家上架商品 | 拒绝 |
| 商品库存为 0 时结账 | 库存不足 |
| 下单成功 | 订单/明细/库存/流水/支付记录一致 |
| 下单过程中主动制造异常 | 全部 rollback |
| 两用户抢最后 1 件商品 | 仅 1 个成功 |
| 商品调价 | product_prices 有历史记录 |
| 商品调价后查历史订单 | 历史成交价不变 |
| 商品下架 | 新购买被拒绝 |
| 商家进货 | inventory 与流水同步 |
| 取消符合规则订单 | 库存恢复且生成流水 |
| 管理员冻结商家 | 商家后续受限 |
| 商家收益统计 | 与订单明细聚合结果一致 |

测试不能只验证 HTTP 200，还必须断言数据库最终状态。

---

## 15. Seed Data 与演示数据

提供 `scripts/seed_data.py`，至少创建：

- 1 个管理员；
- 2 个普通用户；
- 2 个已审核商家；
- 2 个店铺；
- 5-8 个商品分类；
- 20-50 个商品；
- 有高、中、低、零库存商品；
- 部分商品有历史价格记录；
- 若干历史订单与支付记录。

README 中给出演示账号，但只用于本地开发，禁止写真实密码或真实凭据。

---

## 16. Docker 与环境

`docker-compose.yml` 至少包含：

```text
mysql
backend
frontend
```

要求：

- MySQL 使用 volume 持久化；
- backend 等待 DB 可用后启动；
- 数据库密码、JWT Secret 等使用 `.env`；
- 仓库只提交 `.env.example`；
- 一条命令即可启动：

```bash
docker compose up --build
```

---

## 17. GitHub Actions

Pull Request / push 时至少执行：

1. 安装 Python 依赖；
2. 启动 MySQL service；
3. 执行 Alembic migration；
4. 运行 pytest；
5. 测试失败则 CI 失败。

如实现前端测试或 lint，可在核心后端完成后再加入。

---

## 18. 日志与错误处理

要求：

- 使用统一异常类型和错误响应；
- 库存不足、权限不足、商品不可售等属于业务错误，不返回 500；
- 后端使用结构化日志或至少规范 logging；
- 不在日志中输出密码、JWT、数据库密码等敏感信息；
- 关键管理操作由 audit_logs 保存业务审计信息。

---

## 19. 非功能要求

- 代码风格一致；
- 类型提示尽量完整；
- 函数和模块职责单一；
- 禁止把全部业务逻辑堆在 router；
- 禁止为了“快速完成”绕过 Service/Repository 分层；
- 金额使用 DECIMAL；
- 时间统一使用明确时区策略，并在文档说明；
- 所有关键数据表有 created_at / updated_at（合理场景）；
- 列表接口分页；
- 数据库 Migration 可从空库完整执行；
- README 应允许新开发者在合理时间内运行项目。

---

## 20. 开发阶段与 Gate

Codex 必须按阶段开发。每个阶段完成后先输出变更摘要、文件清单、测试结果和待确认问题，再进入下一阶段。

### Phase 0 - Architecture Proposal

仅设计，不写完整业务。

交付：

- 架构图；
- 目录结构；
- ERD；
- 表结构草案；
- 关键事务设计；
- RBAC 设计；
- 主要技术决策；
- 风险点清单。

**Gate：架构获确认后才能进入 Phase 1。**

### Phase 1 - Project Skeleton & Database

完成：

- FastAPI skeleton；
- MySQL；
- SQLAlchemy models；
- Alembic；
- Docker Compose；
- `.env.example`；
- 基础 Repository；
- migration 测试。

验收：从空数据库可一键迁移到最新 Schema。

### Phase 2 - Authentication & RBAC

完成：

- Register / Login；
- password hash；
- JWT；
- CUSTOMER/MERCHANT/ADMIN；
- 权限依赖；
- 所有权检查基础；
- 相关测试。

### Phase 3 - Merchant / Product / Inventory

完成：

- 商家申请与审批；
- 店铺；
- 商品 CRUD；
- soft delete；
- 上下架；
- 调价历史；
- 库存与库存流水；
- 对应测试。

### Phase 4 - Customer / Cart / Checkout / Order

完成：

- 商品查询、搜索、筛选；
- 购物车；
- 地址；
- Checkout；
- MySQL Transaction；
- 行级锁防超卖；
- Order / OrderItem；
- Mock Payment；
- rollback；
- 并发测试。

这是最重要阶段，不接受仅能“跑通 happy path”。

### Phase 5 - Merchant Analytics & Admin

完成：

- 商家订单处理；
- 收益统计；
- 热门商品；
- 低库存；
- 管理员用户/商家/商品管理；
- Audit Log；
- 平台统计。

### Phase 6 - Frontend

完成三套可交互界面：

- Customer；
- Merchant；
- Admin。

先确保功能闭环，再优化 UI。

### Phase 7 - QA / CI / Documentation

完成：

- 补充完整 pytest；
- GitHub Actions；
- EXPLAIN 优化案例；
- seed data；
- README；
- 架构文档；
- API 文档；
- 最终演示流程。

---

## 21. MVP 与扩展项

### 必须完成（MVP）

- 三角色登录；
- 商家审核；
- 店铺；
- 商品管理；
- 上下架；
- 价格历史；
- 库存与库存流水；
- 商品搜索；
- 购物车；
- Checkout；
- 订单；
- 模拟支付；
- MySQL 事务；
- 防超卖；
- 商家基础销售统计；
- Admin 基础管理；
- 自动化测试；
- Docker Compose；
- GitHub Actions；
- 前端可交互页面。

### 扩展项（主流程完成后再做）

- 收藏夹；
- 商品图片上传；
- 用户评价；
- 退款流程；
- merchant_settlements；
- 库存预占与支付超时释放；
- Refresh Token；
- 优惠券；
- 更复杂搜索；
- 前端 E2E 测试；
- 缓存；
- OpenTelemetry / metrics。

Codex 不应在 MVP 未完成前主动实现扩展项。

---

## 22. 明确不做

初版禁止把精力投入以下内容：

- 真实支付宝/微信/Stripe 支付；
- 微服务拆分；
- Kubernetes；
- Kafka/RabbitMQ；
- Elasticsearch；
- Redis 强依赖；
- AI 推荐系统；
- 实时聊天；
- 复杂物流 API；
- 多币种和国际税务；
- 高级促销引擎。

这些会稀释本项目“数据库应用开发”的核心价值。

---

## 23. Definition of Done

项目完成必须同时满足：

1. `docker compose up --build` 可启动完整环境；
2. Alembic 可从空库迁移；
3. 三种角色可以登录并访问各自页面；
4. 商家可以申请、获批、开店、创建商品、进货、调价、上下架；
5. 用户可以搜索、加入购物车、结账、支付、查看订单；
6. 管理员可以管理商家和商品；
7. Checkout 使用数据库事务；
8. 并发购买最后一件商品不会超卖；
9. 历史订单价格不会因商品后续调价改变；
10. 库存每次变化均有流水；
11. pytest 覆盖关键业务规则且通过；
12. GitHub Actions 通过；
13. 至少有一个 EXPLAIN 查询优化案例；
14. README 给出架构、启动方式、演示账号和完整演示流程；
15. 前端能完整演示 Customer → Merchant → Admin 三角色闭环。

---

## 24. 最终演示脚本

最终项目应能按以下顺序现场演示：

1. 管理员登录；
2. 新商家提交申请；
3. 管理员批准商家；
4. 商家创建店铺；
5. 商家创建商品并进货 10 件；
6. 商家设置价格并上架；
7. 用户搜索到商品；
8. 用户加入购物车；
9. 用户结账并模拟支付；
10. 页面显示订单成功；
11. 商家查看订单及销售额；
12. 查看库存从 10 变为 9，并存在 SALE 流水；
13. 商家将商品调价；
14. 用户查看旧订单，旧订单成交价不变；
15. 管理员查看平台订单和审计日志；
16. 运行“最后一件库存”并发测试，证明不会超卖；
17. 展示 GitHub Actions 通过；
18. 展示数据库索引与 EXPLAIN 优化案例。

---

## 25. Codex 工作规则

在整个开发过程中遵循以下约束：

1. 不得一次性生成完整系统后再解释；严格按 Phase 开发；
2. 未经确认不得大幅改变技术栈和架构；
3. 不得用大量 mock 替代核心数据库业务；
4. 不得绕过 Service / Repository 分层；
5. 不得用 SQLite 替代最终 MySQL 行为验证，尤其事务、锁和并发测试；
6. 不得忽略错误路径，只实现 happy path；
7. 每个阶段必须新增对应测试；
8. 修改 Schema 必须生成 Alembic migration；
9. 所有金额使用 Decimal；
10. 对重要数据库设计选择写入 `docs/database-decisions.md`；
11. 若发现需求之间存在冲突，先提出并给出选项，不自行悄悄更改业务规则；
12. 优先保持代码简单、清晰、可测试，不追求不必要的抽象；
13. 每个 Phase 结束时输出：完成内容、主要文件、测试命令、测试结果、已知问题、下一步计划。

---

# 附录 A：交给 Codex 的启动指令

将本文件放到仓库根目录，例如命名为 `PROJECT_SPEC.md`，然后向 Codex 发送：

> 阅读仓库根目录的 `PROJECT_SPEC.md`。这是本项目的最高优先级产品与工程规范。不要直接开始实现整个系统。
>
> 现在只执行 **Phase 0 - Architecture Proposal**：
> 1. 检查需求是否存在矛盾、缺失或会导致实现风险的部分；
> 2. 输出推荐目录结构；
> 3. 输出 Mermaid ERD；
> 4. 给出每个核心表的字段、主键、外键、唯一约束和重要索引建议；
> 5. 说明 Checkout 事务边界和防超卖方案；
> 6. 说明 RBAC 与商家资源所有权校验方案；
> 7. 说明订单状态、支付状态和库存流水之间的关系；
> 8. 给出 Phase 1 的具体实施清单。
>
> 此阶段不要生成完整前后端代码。先提交架构提案等待确认。

---

# 附录 B：简历项目最终应能支持的技术表述

本附录不是要求 Codex 为简历“制造结果”，而是项目真实完成后应自然具备的工程证据。任何简历数字和成果必须以实际实现、测试或测量结果为准。

完成后，项目原则上应能真实支持以下能力：

- 基于 MySQL 设计多角色电商交易数据库及关系模型；
- 使用 FastAPI + SQLAlchemy 实现分层后端；
- 使用 JWT + RBAC 完成 Customer/Merchant/Admin 权限控制；
- 使用事务和行级锁保证订单创建与库存扣减一致性并防止超卖；
- 实现商品价格历史、库存流水和订单成交价快照；
- 使用索引与 EXPLAIN 分析商品/订单查询；
- 使用 pytest 验证权限、事务 rollback、并发库存等关键业务规则；
- 使用 Docker Compose 搭建运行环境并通过 GitHub Actions 持续集成；
- 使用 Next.js 构建用户、商家和管理员可交互页面。

实际简历中只写最终真实完成并可以解释、演示和复现的部分。


