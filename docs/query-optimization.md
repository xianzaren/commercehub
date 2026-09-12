# MySQL EXPLAIN 优化案例

## 场景

商品市场最常见的查询是按“在售状态 + 分类”筛选，并按创建时间倒序分页：

```sql
SELECT id, name, current_price
FROM products
WHERE status = 'ACTIVE' AND category_id = ?
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

对应复合索引：

```sql
CREATE INDEX ix_products_browse
ON products (status, category_id, created_at, id);
```

等值过滤列位于索引左侧，排序列位于其后。MySQL 可以反向扫描同一 B-Tree，直接按 `created_at DESC, id DESC` 返回结果。

## 可复现命令

```bash
docker compose --profile tools run --rm seed
docker compose --profile tools run --rm explain
```

`scripts/explain_queries.py` 在相同数据上同时执行 `IGNORE INDEX` 基线与 `FORCE INDEX` 优化查询，并使用 MySQL 8.4 `EXPLAIN ANALYZE` 输出真实执行计划。

## 本机实测结果

测试环境：MySQL 8.4.11，Phase 7 seed 数据（24 个商品）。

| 方案 | 访问路径 | 估算行数 | 额外排序 | 实测时间 |
|---|---|---:|---|---:|
| 基线 | 分类外键索引 `fk_products_category_id_categories` | 10 | 有 | 约 0.184 ms |
| 复合索引 | `ix_products_browse`，status + category_id | 3 | 无 | 约 0.124 ms |

核心计划片段：

```text
baseline
  Sort: products.created_at DESC, products.id DESC
    Filter: products.status = 'ACTIVE'
      Index lookup using fk_products_category_id_categories (category_id=1)

optimized
  Index lookup using ix_products_browse
    (status='ACTIVE', category_id=1) (reverse)
```

本次小数据集单次执行时间约下降 32.6%，但该数字不作为通用性能承诺；真正稳定的工程证据是执行计划消除了显式排序，并将状态与分类过滤同时下推到复合索引。

商家待处理订单查询同样命中：

```text
ix_orders_store_status_created (store_id, status, created_at, id) (reverse)
```

它支持商家按店铺和订单状态读取最新订单队列。

## 索引代价

复合索引会增加商品写入、上下架和分类变更的维护成本。该项目的主要访问模式是高频浏览、低频商品维护，因此此空间与写放大成本可接受。关键词 `%keyword%` 模糊搜索仍不能有效利用普通 B-Tree；MVP 数据量较小，未引入全文索引或 Elasticsearch。
