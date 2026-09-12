# Phase 4 完成报告

## 交付范围

Phase 4 已完成普通用户交易闭环：

- ACTIVE 商品公开查询、关键词搜索、分类和价格筛选、排序及分页；
- 商品详情与实时库存；
- 单店购物车的读取、新增、修改和删除；
- 收货地址 CRUD 与默认地址维护；
- Checkout 原子事务；
- Order、OrderItem 成交快照与 PENDING Payment；
- 模拟支付成功、失败、金额验证和幂等保护；
- 用户订单列表和详情；
- 早期订单取消、库存返还与 RETURN 流水；
- MySQL 行锁防超卖；
- 主动异常下的完整事务 rollback。

## Checkout 一致性边界

以下操作在一次事务中提交：

1. `FOR UPDATE` 锁定用户 ACTIVE cart；
2. 加载 cart_items 并验证非空；
3. 复查店铺和商品可售状态；
4. 按 product_id 升序锁定 inventory；
5. 在锁内再次验证库存；
6. 根据当前 DECIMAL 价格计算金额；
7. 创建 order 和不可变 order_items 快照；
8. 扣减库存、递增 version、写 SALE 流水；
9. 创建 PENDING payment；
10. 将购物车改为 CHECKED_OUT。

任何步骤抛出异常都会执行 rollback。订单号和支付号使用 32 位随机标识并受数据库唯一约束保护。

## 并发防超卖证明

集成测试使用两个线程、两个独立 SQLAlchemy Session 和两个 MySQL 连接，让两名用户同时购买库存为 1 的同一商品。最终断言：

- 一个 Checkout 成功；
- 另一个返回 `INSUFFICIENT_STOCK`；
- 最终库存为 0；
- 仅生成一个订单；
- 仅生成一条 SALE 流水。

这不是内存锁或测试替身，而是 MySQL InnoDB `SELECT ... FOR UPDATE` 的真实并发验证。

## Rollback 证明

测试在 order_items 写入后主动抛出异常，最终验证：

- order 和 order_items 均不存在；
- payment 不存在；
- inventory 数量未变化；
- SALE 流水不存在；
- cart 仍为 ACTIVE。

## 自动化结果

- Ruff：通过；
- pytest：34 项通过；
- 包含 Phase 1–3 的全部回归测试；
- 唯一警告是 Starlette TestClient 使用 AnyIO 旧类型别名的上游弃用提示，不影响功能。

## 数据库变更

无新增 migration。Phase 1 已建立 carts、cart_items、addresses、orders、order_items 和 payments，本阶段实现其业务逻辑和事务边界。Alembic 模型仍应与数据库 head 保持一致。

## 完整应用状态

Phase 4 完成后，后端已经拥有从商家上架商品到用户购买、支付和取消的核心电商闭环。但浏览器端仍是运行状态页面，尚不能称为最终可视化应用。Phase 5 将补商家订单处理、统计和管理员管理，Phase 6 才会交付三角色可交互前端。
