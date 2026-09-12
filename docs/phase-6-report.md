# Phase 6 完成报告

## 交付范围

Phase 6 已将原有运行状态占位页替换为三角色可交互 Web 应用。前端统一通过 FastAPI 访问业务数据，不直连 MySQL。

### Customer

- 注册、登录、退出和按角色跳转；
- 商品搜索、分类筛选、排序、详情和实时库存展示；
- 加入购物车、修改数量、删除商品；
- 地址新增、设为默认和删除；
- Checkout 地址及模拟支付方式选择；
- 订单列表、订单详情、成交快照、模拟支付和取消订单；
- 提交商家入驻申请。

### Merchant

- 经营概览、今日/月度/累计销售指标；
- 店铺创建与资料维护；
- 商品创建、资料编辑、软删除、调价和上下架；
- 库存总览和进货；
- 店铺订单、订单详情、开始处理和确认发货；
- 热门商品和低库存分析。

### Admin

- 平台经营指标；
- 用户状态管理；
- 商家申请审批及商家状态管理；
- 商品强制下架；
- 全平台订单查询；
- 审计日志查看。

## 页面与交互设计

- Next.js App Router + React 19 + TypeScript；
- 按 CUSTOMER、MERCHANT、ADMIN 展示独立导航和角色色彩；
- 统一 API 错误、加载、空数据、状态徽标、金额和时间格式；
- 桌面端使用侧边工作台，窄屏自动改为横向导航和单栏布局；
- 商品、订单、统计、库存和审计数据全部来自真实后端接口；
- 路由覆盖项目书第 13 节列出的公共、用户、商家和管理员页面。

## 架构边界

```text
Browser / Next.js
        ↓ HTTP + JSON + HttpOnly JWT Cookie
FastAPI Router → Service → Repository → SQLAlchemy
        ↓
MySQL 8.4
```

Phase 6 没有增加数据库表或 Alembic migration，也没有改变 Phase 1–5 的事务和权限边界。

## 自动化验证

- `next build`：通过；
- TypeScript 严格类型检查：通过；
- Next.js 共生成 28 个路由节点，其中动态商品、用户订单、商家商品编辑和商家订单详情按需渲染；
- 前端核心页面 HTTP 检查：通过；
- Ruff：通过；
- pytest：36 项通过；
- Docker Compose 中 `mysql`、`backend`、`frontend` 均为 healthy；
- 后端就绪检查确认 MySQL 可连接。

唯一测试警告来自 Starlette TestClient 对 AnyIO 旧别名的上游弃用提示，不影响运行。

## 已知边界

- 真实演示账号、分类、商品和历史订单将在 Phase 7 由 seed data 提供；
- 当前为本地 Docker 演示应用，不包含公网部署、真实支付和图片上传；
- Phase 7 将完成最终 QA、CI、EXPLAIN 优化案例、seed data、完整 README 和演示脚本。
