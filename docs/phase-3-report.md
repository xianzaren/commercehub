# Phase 3 完成报告

## 交付范围

Phase 3 已实现完整的 Merchant / Product / Inventory 后端闭环：

- CUSTOMER 提交商家申请，ADMIN 查询和批准申请；
- 审批原子更新商家状态和用户角色，并生成 `audit_logs`；
- ADMIN 冻结、恢复、关闭商家，同步店铺状态；
- 已批准商家创建和维护自己的单一店铺；
- 管理员创建分类，公开查询有效分类；
- 商家商品创建、查询、编辑、软删除及上下架；
- 调价与 `product_prices` 历史记录同事务提交；
- 创建商品时原子初始化零库存；
- 进货、人工调整和 `inventory_transactions` 流水同事务提交；
- MySQL 行锁保护库存修改，禁止负库存；
- 所有商品写操作执行商家资源所有权校验。

## 关键规则

1. 待审批用户仍是 CUSTOMER；批准后才切换为 MERCHANT。
2. JWT 保存角色声明，角色改变后旧 token 立即失效，重新登录后生效。
3. 每个商家最多创建一个店铺。
4. 商品默认 DRAFT，库存大于零且店铺正常时才能 ACTIVE。
5. 普通编辑接口不能修改价格，避免绕过价格历史。
6. 删除商品只设置 DELETED 和 `deleted_at`，保留交易引用能力。
7. 库存余额、version 和流水始终在同一数据库事务更新。
8. 商家访问其他店铺商品明确返回 403，且不泄露或修改资源内容。

## 数据库变更

无新增 migration。Phase 1 的初始模型已经包含 merchants、stores、categories、products、product_prices、inventory、inventory_transactions 和 audit_logs，本阶段直接完成其业务实现。

## 自动化验证

- Ruff：通过；
- pytest：29 项通过；
- Phase 3 新增测试覆盖审批审计、角色切换、店铺维护、商品生命周期、零库存上架拒绝、调价历史、库存流水、负库存事务回滚、软删除、跨商家越权和冻结商家；
- Phase 1/2 全部测试继续通过；
- 唯一警告来自 Starlette TestClient 对 AnyIO 旧类型别名的上游弃用提示，不影响功能。

## 下一阶段

Phase 4 将实现公开商品搜索与筛选、购物车、地址、Checkout、订单与模拟支付，并重点验证 MySQL 事务 rollback 和“最后一件库存”并发防超卖。
