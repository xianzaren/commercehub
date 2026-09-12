# 数据库结构草案

## 通用约定

- 主键统一 `BIGINT UNSIGNED AUTO_INCREMENT`。
- 时间统一以 UTC 写入 `DATETIME(6)`；API 使用带时区 ISO 8601。
- 字符集使用 `utf8mb4`，排序规则使用大小写不敏感的现代 Unicode collation。
- 金额统一 `DECIMAL(12,2)`，Python 端使用 `Decimal`；金额不得为负。
- 状态字段使用 `VARCHAR` + SQLAlchemy/Pydantic Enum + CHECK，避免 MySQL ENUM 修改困难。
- 所有数量使用有符号 INT，以允许库存流水表达负变化；库存余额有非负 CHECK。

## users

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| email | VARCHAR(254) | NOT NULL, UNIQUE；写入前 trim/lower |
| password_hash | VARCHAR(255) | NOT NULL |
| role | VARCHAR(20) | NOT NULL, CHECK CUSTOMER/MERCHANT/ADMIN |
| status | VARCHAR(20) | NOT NULL, CHECK ACTIVE/SUSPENDED/DISABLED |
| created_at / updated_at | DATETIME(6) | NOT NULL |

索引：`uq_users_email(email)`、`ix_users_role_status(role,status)`。

## merchants

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| user_id | BIGINT UNSIGNED | FK users, NOT NULL, UNIQUE |
| business_name | VARCHAR(120) | NOT NULL |
| status | VARCHAR(20) | CHECK PENDING/ACTIVE/SUSPENDED/CLOSED |
| approved_at | DATETIME(6) | NULL |
| approved_by | BIGINT UNSIGNED | FK users, NULL |
| created_at / updated_at | DATETIME(6) | NOT NULL |

索引：`ix_merchants_status_created(status,created_at)`。批准时要求 `approved_at` 与 `approved_by` 同时存在。

## stores

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| merchant_id | BIGINT UNSIGNED | FK merchants, NOT NULL, UNIQUE（MVP 一商家一店） |
| name | VARCHAR(120) | NOT NULL |
| description | TEXT | NULL |
| status | VARCHAR(20) | CHECK ACTIVE/SUSPENDED/CLOSED |
| created_at / updated_at | DATETIME(6) | NOT NULL |

索引：`uq_stores_merchant_id(merchant_id)`、`ix_stores_status(status)`。

## categories

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| parent_id | BIGINT UNSIGNED | self FK, NULL |
| name | VARCHAR(80) | NOT NULL |
| slug | VARCHAR(100) | NOT NULL, UNIQUE |
| status | VARCHAR(20) | CHECK ACTIVE/INACTIVE |
| created_at / updated_at | DATETIME(6) | NOT NULL |

索引：`uq_categories_slug(slug)`、`ix_categories_parent_status(parent_id,status)`。

## products

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| store_id | BIGINT UNSIGNED | FK stores, NOT NULL |
| category_id | BIGINT UNSIGNED | FK categories, NOT NULL |
| sku | VARCHAR(64) | NOT NULL |
| name | VARCHAR(200) | NOT NULL |
| description | TEXT | NULL |
| current_price | DECIMAL(12,2) | NOT NULL, CHECK > 0 |
| status | VARCHAR(20) | CHECK DRAFT/ACTIVE/INACTIVE/DELETED |
| created_at / updated_at | DATETIME(6) | NOT NULL |
| deleted_at | DATETIME(6) | NULL |

约束与索引：

- `uq_products_store_sku(store_id,sku)`；SKU 为店铺内唯一。
- `ix_products_browse(status,category_id,created_at,id)`；支持分类和新旧排序。
- `ix_products_store_status(store_id,status,id)`；支持商家商品列表。
- `ix_products_active_price(status,current_price,id)`；支持价格筛选和稳定分页。
- keyword 初版使用转义后的 `LIKE`；不承诺普通 B-tree 对 `%keyword%` 的优化，数据量扩大后再评估 FULLTEXT。

## product_prices

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| product_id | BIGINT UNSIGNED | FK products, NOT NULL |
| old_price / new_price | DECIMAL(12,2) | NOT NULL, CHECK > 0 且不相等 |
| changed_by | BIGINT UNSIGNED | FK users, NOT NULL |
| changed_at | DATETIME(6) | NOT NULL |

索引：`ix_product_prices_product_changed(product_id,changed_at,id)`。

## inventory

| 字段 | 类型 | 约束 |
|---|---|---|
| product_id | BIGINT UNSIGNED | PK, FK products |
| quantity | INT | NOT NULL DEFAULT 0, CHECK >= 0 |
| version | BIGINT UNSIGNED | NOT NULL DEFAULT 0 |
| updated_at | DATETIME(6) | NOT NULL |

`version` 用于调试与可观测性；MVP 正确性依靠悲观行锁，不依靠乐观锁。

## inventory_transactions

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| product_id | BIGINT UNSIGNED | FK products, NOT NULL |
| type | VARCHAR(20) | CHECK RESTOCK/SALE/ADJUSTMENT/RETURN/RELEASE |
| quantity_change | INT | NOT NULL, CHECK != 0 |
| quantity_before / quantity_after | INT | NOT NULL, CHECK >= 0 |
| reference_type | VARCHAR(30) | NULL，如 ORDER/MANUAL/SEED |
| reference_id | BIGINT UNSIGNED | NULL；多态引用，不建 FK |
| reason | VARCHAR(255) | NULL；ADJUSTMENT 必填 |
| created_by | BIGINT UNSIGNED | FK users, NULL；系统操作允许 NULL |
| created_at | DATETIME(6) | NOT NULL |

索引：`ix_inventory_tx_product_created(product_id,created_at,id)`、`ix_inventory_tx_reference(reference_type,reference_id)`。

Service 必须保证 `quantity_after = quantity_before + quantity_change`。

## carts

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| user_id | BIGINT UNSIGNED | FK users, NOT NULL |
| store_id | BIGINT UNSIGNED | FK stores, NULL；空购物车允许 NULL |
| status | VARCHAR(20) | CHECK ACTIVE/CHECKED_OUT/ABANDONED |
| active_user_id | BIGINT UNSIGNED | 生成列：ACTIVE 时等于 user_id，否则 NULL |
| created_at / updated_at | DATETIME(6) | NOT NULL |

索引：`uq_carts_one_active_user(active_user_id)`。MySQL UNIQUE 允许多个 NULL，从数据库层保证每个用户最多一个 ACTIVE cart。

## cart_items

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| cart_id | BIGINT UNSIGNED | FK carts, NOT NULL |
| product_id | BIGINT UNSIGNED | FK products, NOT NULL |
| quantity | INT | NOT NULL, CHECK > 0 |
| created_at / updated_at | DATETIME(6) | NOT NULL |

索引：`uq_cart_items_cart_product(cart_id,product_id)`、`ix_cart_items_product(product_id)`。

## addresses

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| user_id | BIGINT UNSIGNED | FK users, NOT NULL |
| recipient_name | VARCHAR(80) | NOT NULL |
| phone | VARCHAR(32) | NOT NULL |
| province/city/district | VARCHAR(80) | NOT NULL |
| detail | VARCHAR(255) | NOT NULL |
| postal_code | VARCHAR(20) | NULL |
| is_default | BOOLEAN | NOT NULL DEFAULT false |
| created_at / updated_at | DATETIME(6) | NOT NULL |

索引：`ix_addresses_user(user_id,id)`。默认地址唯一性由锁定用户地址集合的 Service 事务维护。

## orders

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| order_no | VARCHAR(32) | NOT NULL, UNIQUE |
| user_id | BIGINT UNSIGNED | FK users, NOT NULL |
| store_id | BIGINT UNSIGNED | FK stores, NOT NULL |
| address_snapshot | JSON | NOT NULL |
| status | VARCHAR(24) | CHECK PENDING_PAYMENT/PAID/PROCESSING/SHIPPED/COMPLETED/CANCELLED |
| subtotal / total_amount | DECIMAL(12,2) | NOT NULL, CHECK >= 0 |
| payment_status | VARCHAR(20) | CHECK UNPAID/PAID |
| created_at / updated_at | DATETIME(6) | NOT NULL |

MVP 无运费和优惠，因此 `total_amount = subtotal`。字段分开保留扩展空间。

索引：

- `uq_orders_order_no(order_no)`。
- `ix_orders_user_created(user_id,created_at,id)`。
- `ix_orders_store_status_created(store_id,status,created_at,id)`。
- `ix_orders_status_created(status,created_at,id)`，用于管理员与超时订单查询。

## order_items

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| order_id | BIGINT UNSIGNED | FK orders, NOT NULL |
| product_id | BIGINT UNSIGNED | FK products, NOT NULL |
| store_id | BIGINT UNSIGNED | FK stores, NOT NULL |
| product_name_snapshot | VARCHAR(200) | NOT NULL |
| sku_snapshot | VARCHAR(64) | NOT NULL |
| unit_price | DECIMAL(12,2) | NOT NULL, CHECK > 0 |
| quantity | INT | NOT NULL, CHECK > 0 |
| subtotal | DECIMAL(12,2) | NOT NULL, CHECK > 0 |

索引：`uq_order_items_order_product(order_id,product_id)`、`ix_order_items_store_product(store_id,product_id)`。Service 保证 subtotal 等于量价乘积。

## payments

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| order_id | BIGINT UNSIGNED | FK orders, NOT NULL |
| payment_no | VARCHAR(32) | NOT NULL, UNIQUE |
| idempotency_key | VARCHAR(64) | NOT NULL |
| method | VARCHAR(20) | CHECK MOCK_CARD/MOCK_WALLET |
| amount | DECIMAL(12,2) | NOT NULL, CHECK > 0 |
| status | VARCHAR(20) | CHECK PENDING/PAID/FAILED/REFUNDED |
| paid_order_id | BIGINT UNSIGNED | 生成列：PAID 时等于 order_id，否则 NULL |
| paid_at | DATETIME(6) | NULL |
| created_at / updated_at | DATETIME(6) | NOT NULL |

索引：`uq_payments_payment_no(payment_no)`、`uq_payments_order_idempotency(order_id,idempotency_key)`、`uq_payments_one_paid_order(paid_order_id)`、`ix_payments_order_created(order_id,created_at,id)`。

## audit_logs

| 字段 | 类型 | 约束 |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| actor_user_id | BIGINT UNSIGNED | FK users, NOT NULL |
| actor_role | VARCHAR(20) | NOT NULL，保存操作时角色快照 |
| action | VARCHAR(80) | NOT NULL |
| entity_type | VARCHAR(50) | NOT NULL |
| entity_id | BIGINT UNSIGNED | NOT NULL，多态引用不建 FK |
| before_data / after_data | JSON | NULL |
| created_at | DATETIME(6) | NOT NULL |

索引：`ix_audit_actor_created(actor_user_id,created_at,id)`、`ix_audit_entity_created(entity_type,entity_id,created_at,id)`、`ix_audit_action_created(action,created_at,id)`。

审计 JSON 写入前移除 password_hash、token、连接串和任何 secret。
