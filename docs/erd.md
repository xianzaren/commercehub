# CommerceHub ERD

## 核心实体关系

```mermaid
erDiagram
    USERS ||--o| MERCHANTS : applies
    MERCHANTS ||--o| STORES : owns
    CATEGORIES ||--o{ CATEGORIES : parent_of
    CATEGORIES ||--o{ PRODUCTS : classifies
    STORES ||--o{ PRODUCTS : sells
    PRODUCTS ||--|| INVENTORY : has
    PRODUCTS ||--o{ PRODUCT_PRICES : changes
    USERS ||--o{ PRODUCT_PRICES : changes_by
    PRODUCTS ||--o{ INVENTORY_TRANSACTIONS : produces
    USERS ||--o{ INVENTORY_TRANSACTIONS : creates
    USERS ||--o{ CARTS : owns
    STORES ||--o{ CARTS : scopes
    CARTS ||--o{ CART_ITEMS : contains
    PRODUCTS ||--o{ CART_ITEMS : selected
    USERS ||--o{ ADDRESSES : owns
    USERS ||--o{ ORDERS : places
    STORES ||--o{ ORDERS : receives
    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : snapshots
    ORDERS ||--o{ PAYMENTS : attempts
    USERS ||--o{ AUDIT_LOGS : acts
```

## 字段级 ERD

```mermaid
erDiagram
    USERS {
        bigint id PK
        varchar email UK
        varchar password_hash
        varchar role
        varchar status
        datetime created_at
        datetime updated_at
    }
    MERCHANTS {
        bigint id PK
        bigint user_id FK,UK
        varchar business_name
        varchar status
        datetime approved_at
        bigint approved_by FK
        datetime created_at
        datetime updated_at
    }
    STORES {
        bigint id PK
        bigint merchant_id FK,UK
        varchar name
        text description
        varchar status
        datetime created_at
        datetime updated_at
    }
    CATEGORIES {
        bigint id PK
        bigint parent_id FK
        varchar name
        varchar slug UK
        varchar status
        datetime created_at
        datetime updated_at
    }
    PRODUCTS {
        bigint id PK
        bigint store_id FK
        bigint category_id FK
        varchar sku
        varchar name
        text description
        decimal current_price
        varchar status
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }
    PRODUCT_PRICES {
        bigint id PK
        bigint product_id FK
        decimal old_price
        decimal new_price
        bigint changed_by FK
        datetime changed_at
    }
    INVENTORY {
        bigint product_id PK,FK
        int quantity
        bigint version
        datetime updated_at
    }
    INVENTORY_TRANSACTIONS {
        bigint id PK
        bigint product_id FK
        varchar type
        int quantity_change
        int quantity_before
        int quantity_after
        varchar reference_type
        bigint reference_id
        varchar reason
        bigint created_by FK
        datetime created_at
    }
    CARTS {
        bigint id PK
        bigint user_id FK
        bigint store_id FK
        varchar status
        bigint active_user_id UK
        datetime created_at
        datetime updated_at
    }
    CART_ITEMS {
        bigint id PK
        bigint cart_id FK
        bigint product_id FK
        int quantity
        datetime created_at
        datetime updated_at
    }
    ADDRESSES {
        bigint id PK
        bigint user_id FK
        varchar recipient_name
        varchar phone
        varchar province
        varchar city
        varchar district
        varchar detail
        varchar postal_code
        boolean is_default
        datetime created_at
        datetime updated_at
    }
    ORDERS {
        bigint id PK
        varchar order_no UK
        bigint user_id FK
        bigint store_id FK
        json address_snapshot
        varchar status
        decimal subtotal
        decimal total_amount
        varchar payment_status
        datetime created_at
        datetime updated_at
    }
    ORDER_ITEMS {
        bigint id PK
        bigint order_id FK
        bigint product_id FK
        bigint store_id FK
        varchar product_name_snapshot
        varchar sku_snapshot
        decimal unit_price
        int quantity
        decimal subtotal
    }
    PAYMENTS {
        bigint id PK
        bigint order_id FK
        varchar payment_no UK
        varchar idempotency_key
        varchar method
        decimal amount
        varchar status
        bigint paid_order_id UK
        datetime paid_at
        datetime created_at
        datetime updated_at
    }
    AUDIT_LOGS {
        bigint id PK
        bigint actor_user_id FK
        varchar actor_role
        varchar action
        varchar entity_type
        bigint entity_id
        json before_data
        json after_data
        datetime created_at
    }

    USERS ||--o| MERCHANTS : user_id
    USERS ||--o{ ADDRESSES : user_id
    USERS ||--o{ CARTS : user_id
    USERS ||--o{ ORDERS : user_id
    MERCHANTS ||--o| STORES : merchant_id
    CATEGORIES ||--o{ CATEGORIES : parent_id
    CATEGORIES ||--o{ PRODUCTS : category_id
    STORES ||--o{ PRODUCTS : store_id
    STORES ||--o{ CARTS : store_id
    STORES ||--o{ ORDERS : store_id
    PRODUCTS ||--|| INVENTORY : product_id
    PRODUCTS ||--o{ PRODUCT_PRICES : product_id
    PRODUCTS ||--o{ INVENTORY_TRANSACTIONS : product_id
    PRODUCTS ||--o{ CART_ITEMS : product_id
    PRODUCTS ||--o{ ORDER_ITEMS : product_id
    CARTS ||--o{ CART_ITEMS : cart_id
    ORDERS ||--|{ ORDER_ITEMS : order_id
    ORDERS ||--o{ PAYMENTS : order_id
```

## 删除策略

| 关系 | 策略 | 原因 |
|---|---|---|
| user → merchant/address/cart/order | RESTRICT | 用户不物理删除，保留交易历史 |
| merchant → store | RESTRICT | 商家关闭使用状态字段 |
| store → product/order | RESTRICT | 保留商品及订单历史 |
| category.parent | RESTRICT | 有子分类时禁止物理删除 |
| category → product | RESTRICT | 分类停用代替删除 |
| product → inventory | CASCADE | 仅用于尚无业务数据时的开发清理；生产商品软删除 |
| cart → cart_item | CASCADE | 购物车条目无独立历史价值 |
| order → order_item/payment | RESTRICT | 订单及支付记录永久保留 |
| user → audit_log actor | RESTRICT | 审计主体必须可追溯 |

正常业务不物理删除 user、merchant、store、product、order、payment、inventory transaction 和 audit log。
