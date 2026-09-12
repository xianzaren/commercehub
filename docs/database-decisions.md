# 数据库与业务决策记录

本文件记录会影响数据库一致性、接口语义或后续迁移的决定。Phase 7 的真实 EXPLAIN 结果见 [查询优化报告](query-optimization.md)。

## ADR-001：采用模块化单体与同步 SQLAlchemy

**状态：** Accepted  
**决定：** FastAPI 单体按 Router、Service、Repository、ORM 分层；使用 SQLAlchemy 2.x 同步 Session 和 PyMySQL。  
**原因：** 本项目重点是数据库事务与业务边界。同步事务更容易阅读、测试和在面试中解释，也避免为简历项目引入无实际收益的异步复杂度。  
**影响：** FastAPI 同步路由在线程池运行；Session 每请求一个，禁止跨线程共享。

## ADR-002：每个购物车和订单只属于一个店铺

**状态：** Accepted  
**问题：** 原需求的 order 只有一个状态，但 order_items 可以来自多个 store。不同商家无法独立处理同一订单的发货状态。  
**决定：** MVP 为 carts 和 orders 增加 store_id；购物车有商品后不能加入其他店铺商品。  
**替代方案：** checkout batch + merchant sub-order。该方案更接近大型商城，但会增加支付分摊、取消和聚合状态复杂度，不符合本项目范围。  
**影响：** 演示流程不受影响；未来跨店结算需要新增表和 API 版本，而不是直接放宽约束。

## ADR-003：Checkout 时扣减库存

**状态：** Accepted  
**决定：** 成功创建 PENDING_PAYMENT 订单时立即扣库存并写 SALE。支付失败不自动恢复，用户可以重试支付或取消订单。  
**原因：** 能用一个明确事务展示订单、明细、库存、流水和支付记录的一致性；无需引入库存预占和后台超时任务。  
**影响：** 未支付订单可能占用库存。MVP 提供取消恢复；自动超时取消是明确扩展项。

## ADR-004：悲观锁作为防超卖主方案

**状态：** Accepted  
**决定：** Checkout 对 inventory 执行按 product_id 排序的 `SELECT ... FOR UPDATE`。事务隔离级别使用 READ COMMITTED。  
**原因：** 逻辑直接，能在 MySQL 中给出可复现的“最后一件商品”证明。  
**防线：** Service 库存检查 + 行锁 + `quantity >= 0` CHECK。  
**影响：** 热门单品 checkout 会串行化，这是正确性优先的可接受取舍。

## ADR-005：订单信息采用不可变快照

**状态：** Accepted  
**决定：** order_items 保存成交时的商品名、SKU、店铺、单价与小计；orders 保存地址 JSON 快照。  
**原因：** 商品调价、改名或用户编辑地址不得改变历史订单。  
**影响：** 快照存在有意的数据重复；历史查询不得 join 当前字段来替换快照。

## ADR-006：状态使用 VARCHAR + CHECK

**状态：** Accepted  
**决定：** Python 使用 Enum，数据库使用 VARCHAR 和 CHECK，不使用 MySQL 原生 ENUM。  
**原因：** 新增状态时 Alembic migration 更透明，测试库和应用层约束更容易维护。  
**影响：** 所有写入必须经过应用 Enum；数据库 CHECK 提供最终保护。

## ADR-007：使用生成列实现条件唯一性

**状态：** Accepted  
**决定：** carts.active_user_id 仅在 ACTIVE 时生成 user_id，并设 UNIQUE；payments.paid_order_id 仅在 PAID 时生成 order_id，并设 UNIQUE。  
**原因：** MySQL 没有 PostgreSQL 式 partial unique index；生成列配合 UNIQUE 可保证一个用户只有一个活动购物车、一个订单最多一笔成功支付。  
**影响：** migration 与测试必须显式验证生成列表达式和唯一约束。

## ADR-008：认证状态必须回查数据库

**状态：** Accepted  
**决定：** JWT 携带身份与角色，但每次认证请求都读取 users.status 和当前 role。  
**原因：** 如果完全信任 token，管理员冻结用户后旧 token 在过期前仍可操作。  
**影响：** 每个受保护请求多一次主键查询；对本项目负载可忽略。

## ADR-009：时间和金额规范

**状态：** Accepted  
**决定：** 应用内部 UTC；MySQL 存 UTC `DATETIME(6)`；API 输出带 `Z`/offset 的 ISO 8601。金额为 Decimal/DECIMAL(12,2)，统一 ROUND_HALF_UP 到两位。  
**原因：** 避免本地时区和二进制浮点导致历史、排序或对账错误。  
**影响：** 前端负责转换为用户时区；JSON 金额以字符串传输，避免 JavaScript number 精度风险。

## ADR-010：索引以真实查询为依据

**状态：** Accepted  
**决定：** 初始索引围绕商品浏览、用户订单、商家订单、库存历史和审计查询建立。Phase 7 使用 seed 数据记录真实 MySQL 8.4 `EXPLAIN ANALYZE`。  
**已验证案例一：** 商品按在售状态、分类和创建时间倒序浏览，`ix_products_browse(status, category_id, created_at, id)` 消除了额外排序，估算行数由 10 降到 3。  
**已验证案例二：** 商家按状态和时间倒序查看订单：

```sql
SELECT id, order_no, status, total_amount, created_at
FROM orders
WHERE store_id = ? AND status = ?
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

查询命中 `ix_orders_store_status_created(store_id, status, created_at, id)` 并反向扫描。本机数据和完整计划保存在 `docs/query-optimization.md`；小数据集耗时只作复现记录，不作为生产性能承诺。

## 尚未进入 MVP 的决定

- Refresh token：不实现。
- 自动取消超时订单：不实现，只保留可扩展字段与文档。
- 退款和 merchant_settlements：不实现。
- 商品图片上传：不实现；可使用可选外链占位图字段的后续 migration。
- FULLTEXT 搜索：初版不用；数据量与 EXPLAIN 证明需要时再增加。
