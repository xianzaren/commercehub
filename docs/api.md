# CommerceHub API

当前实现范围：Phase 0–7 完整 MVP。交互式文档位于 `http://localhost:8000/docs`。

## 认证方式

登录成功后同时：

1. 返回 JWT access token，API 客户端可使用 `Authorization: Bearer <token>`；
2. 设置 `commercehub_access` HttpOnly、SameSite=Lax cookie，供浏览器前端使用。

Header 优先于 cookie。受保护请求会回查数据库中的用户状态和角色；账户被冻结或角色改变后，旧 token 立即失效。

## 错误结构

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "邮箱或密码错误",
    "details": {}
  }
}
```

## Auth

### POST /api/auth/register

```json
{
  "email": "customer@example.com",
  "password": "Resume123!"
}
```

创建 CUSTOMER/ACTIVE 用户。邮箱不区分大小写；密码要求 8–128 字符且至少包含一个字母和一个数字。成功返回 201；重复邮箱返回 409。

### POST /api/auth/login

请求体与 register 相同。成功返回 access token、有效秒数和当前用户，同时设置认证 cookie。错误凭据统一返回 401，不区分邮箱不存在与密码错误。

### GET /api/auth/me

返回当前用户。缺少或无效 token 返回 401；用户被冻结或禁用返回 403。

### POST /api/auth/logout

删除浏览器认证 cookie，返回 204。MVP 使用无状态 access token，因此已复制到其他客户端的 Bearer token 会持续到过期；管理员冻结账户可使其立即失效。

## RBAC 验证端点

- `GET /api/customer/ping`：仅 CUSTOMER。
- `GET /api/merchant/ping`：仅角色为 MERCHANT 且 merchant.status=ACTIVE。
- `GET /api/admin/ping`：仅 ADMIN。

这些端点用于 Phase 2 验证权限依赖；后续阶段的真实业务路由复用同一依赖。

## 商家申请与管理

- `POST /api/merchant/applications`：CUSTOMER 提交商家申请。
- `GET /api/merchant/application`：查看自己的申请。
- `GET /api/admin/merchant-applications`：管理员查看申请，可用 `application_status` 筛选。
- `POST /api/admin/merchant-applications/{id}/approve`：批准申请，同时将账户角色切换为 MERCHANT 并写审计日志。
- `PATCH /api/admin/merchants/{id}/status`：冻结、恢复或关闭商家，并同步店铺状态。

角色变更后旧 JWT 会返回 `ROLE_CHANGED`，商家需重新登录取得包含新角色的 token。

## 店铺

- `POST /api/merchant/store`：已批准商家创建店铺；MVP 每个商家一个店铺。
- `GET /api/merchant/store`：查看自己的店铺。
- `PATCH /api/merchant/store`：修改店铺名称或描述。

所有店铺接口均要求 `user.role=MERCHANT` 且 `merchant.status=ACTIVE`。

## 分类

- `GET /api/categories`：公开读取有效分类。
- `POST /api/admin/categories`：管理员创建分类，slug 全局唯一。

## 商家商品

- `POST /api/merchant/products`：创建 DRAFT 商品并原子创建零库存记录。
- `GET /api/merchant/products`：列出自己的未删除商品。
- `GET /api/merchant/products/{id}`：查看自己的商品。
- `PATCH /api/merchant/products/{id}`：修改分类、SKU、名称或描述；价格必须走调价接口。
- `DELETE /api/merchant/products/{id}`：软删除，写入 `deleted_at`。
- `POST /api/merchant/products/{id}/status`：上架、下架或恢复草稿；零库存不能上架。
- `POST /api/merchant/products/{id}/price`：调价并在同一事务写入 `product_prices`。
- `GET /api/merchant/products/{id}/prices`：查看价格历史。

SKU 会规范为大写，并在同一店铺内唯一。跨商家访问返回 403。

## 库存

- `POST /api/merchant/products/{id}/inventory/restock`：正数进货，写 RESTOCK 流水。
- `POST /api/merchant/products/{id}/inventory/adjust`：有原因的正负库存调整，写 ADJUSTMENT 流水。
- `GET /api/merchant/products/{id}/inventory/transactions`：查看库存流水。

库存更新使用 MySQL `SELECT ... FOR UPDATE` 锁定库存行。余额、版本号和流水在同一事务提交；调整后为负数时整体回滚并返回 `INSUFFICIENT_INVENTORY`。

## 公开商品

- `GET /api/products`：只返回 ACTIVE 商品，支持 `keyword`、`category_id`、`min_price`、`max_price`、`sort`、`page` 和 `page_size`。
- `GET /api/products/{id}`：读取可售商品详情与当前库存。

`sort` 可选 `price_asc`、`price_desc`、`newest` 或 `oldest`。冻结店铺的商品不会出现在公开结果中。

## 购物车

- `GET /api/cart`：读取当前 CUSTOMER 的活动购物车。
- `POST /api/cart/items`：加入商品；相同商品累加数量。
- `PATCH /api/cart/items/{id}`：修改数量。
- `DELETE /api/cart/items/{id}`：删除商品。

MVP 使用单店购物车：首次加入商品后绑定店铺，再加入其他店铺商品返回 `CART_STORE_CONFLICT`。加入购物车时检查商品和库存，但 Checkout 会在锁定库存后再次校验。

## 收货地址

- `GET /api/addresses`
- `POST /api/addresses`
- `PATCH /api/addresses/{id}`
- `DELETE /api/addresses/{id}`

用户只能访问自己的地址。第一条地址自动设为默认；设置新默认地址时会取消原默认地址。

## Checkout 与订单

- `POST /api/checkout`：提交 `address_id`、`payment_method` 和 8–64 字符的 `idempotency_key`。
- `GET /api/orders`：查询自己的订单。
- `GET /api/orders/{id}`：读取订单、成交快照和支付记录。
- `POST /api/orders/{id}/pay`：模拟支付。
- `POST /api/orders/{id}/cancel`：取消早期订单并返还库存。

Checkout 在单个 MySQL 事务中完成：锁定活动购物车、加载条目、按 `product_id` 排序并 `SELECT ... FOR UPDATE` 锁库存、复查商品与店铺状态、创建订单和成交价快照、扣库存、写 SALE 流水、创建 PENDING payment、关闭购物车。任何异常都会整体回滚。

支付请求必须提交与订单一致的 `amount`。相同幂等键和参数返回同一支付结果；相同键用于不同参数返回 `IDEMPOTENCY_KEY_REUSED`。`simulate_failure=true` 会产生 FAILED 记录但订单保持 PENDING_PAYMENT，可使用新的幂等键重试。

取消 PENDING_PAYMENT 或尚未处理的 PAID 订单会锁定库存并写 RETURN 流水。已支付记录转为 REFUNDED；重复取消不会重复返库。

## 商家订单处理

- `GET /api/merchant/orders`：分页查看自己的店铺订单，支持状态、订单号和创建时间筛选。
- `GET /api/merchant/orders/{id}`：查看订单、地址快照、商品快照和支付记录。
- `PATCH /api/merchant/orders/{id}/status`：按状态机处理订单。

商家允许的状态转换为 `PAID → PROCESSING → SHIPPED`。跳级、倒退或处理未支付订单返回 `INVALID_ORDER_TRANSITION`；访问其他店铺订单返回 403。每次成功变更写入审计日志。

## 商家分析

- `GET /api/merchant/analytics/summary`：今日收入、本月收入、累计收入、已支付订单数和平均订单金额。
- `GET /api/merchant/analytics/top-products`：按成交数量排序的热门商品，可设置 `limit`。
- `GET /api/merchant/analytics/low-stock`：低库存商品，支持阈值与分页。

收入只聚合 payment_status=PAID 且处于 PAID、PROCESSING、SHIPPED、COMPLETED 的订单，待支付和已取消订单不会计入收入。

## 管理员管理

- `GET /api/admin/users`：按角色、状态和邮箱关键词分页查询用户。
- `PATCH /api/admin/users/{id}/status`：激活、冻结或禁用账户并写审计日志；管理员不能冻结自己。
- `GET /api/admin/merchants`：按状态分页查询商家。
- `GET /api/admin/stores`：分页查询所有店铺。
- `GET /api/admin/products`：按状态和关键词分页查询商品。
- `POST /api/admin/products/{id}/force-deactivate`：强制下架商品并记录原因和审计日志。
- `GET /api/admin/orders`：按状态或订单号分页查询平台订单。
- `GET /api/admin/audit-logs`：按操作或操作人分页查询审计日志。
- `GET /api/admin/analytics/summary`：用户、商家、店铺、商品、订单数量和平台成交统计。

管理员修改用户、商家或商品状态后，后续认证或公开商品查询会立即反映最新数据库状态。
