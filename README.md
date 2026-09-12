# CommerceHub

CommerceHub 是一个面向简历展示的多角色电商交易与库存管理平台。它不是静态商城 Demo：Customer、Merchant、Admin 三种角色通过真实 FastAPI 接口操作 MySQL，核心交易由事务、行锁、约束、历史快照和自动化测试保证。

当前状态：**Phase 0–7 MVP 已完成**。

## 项目亮点

- FastAPI Router → Service → Repository → SQLAlchemy 分层；
- JWT HttpOnly Cookie/Bearer 双入口、Argon2 密码哈希、RBAC 与资源所有权隔离；
- MySQL 8.4 InnoDB `SELECT ... FOR UPDATE` 防止并发超卖；
- Checkout 原子写入订单、成交快照、库存扣减、库存流水和待支付记录；
- 支付幂等、取消返库、价格历史和管理员审计；
- 商家销售统计、热门商品、低库存和平台指标；
- Next.js 16 + React 19 + TypeScript 三角色响应式工作台；
- 37 项真实 MySQL 测试、88.08% 后端覆盖率和 GitHub Actions Quality Gate；
- 可重复 seed 与可复现 `EXPLAIN ANALYZE` 优化案例。

## 架构

```text
Browser / Next.js
        ↓ HTTP/JSON + JWT Cookie
FastAPI Router + RBAC
        ↓
Service（业务规则与事务边界）
        ↓
Repository → SQLAlchemy 2.x
        ↓
MySQL 8.4 / InnoDB
```

前端不会直连数据库。Router 不直接操作 ORM，跨表业务规则集中在 Service，Repository 负责查询、锁和持久化。

## 快速启动

要求：Docker Desktop 已启动。

PowerShell：

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose --profile tools run --rm seed
```

macOS/Linux：

```bash
cp .env.example .env
docker compose up -d --build
docker compose --profile tools run --rm seed
```

访问地址：

- Web 应用：http://localhost:3000
- Swagger：http://localhost:8000/docs
- 就绪检查：http://localhost:8000/health/ready

停止服务：

```bash
docker compose down
```

MySQL 数据保存在 Docker volume 中，普通 `docker compose down` 不会删除数据。

## 演示账号

所有账号密码均为 `Demo1234!`。

| 角色 | 账号 |
|---|---|
| ADMIN | `admin@commercehub.example.com` |
| MERCHANT | `merchant1@commercehub.example.com` |
| MERCHANT | `merchant2@commercehub.example.com` |
| CUSTOMER | `customer1@commercehub.example.com` |
| CUSTOMER | `customer2@commercehub.example.com` |

这些凭据只用于本地假数据。Seed 可重复执行，不会删除用户自行创建的数据。

完整操作步骤见 [最终演示流程](docs/demo-guide.md)。

## 三角色功能

Customer：

- 注册登录、商品搜索/筛选/详情；
- 购物车、地址、Checkout、模拟支付；
- 订单快照、订单详情和取消返库；
- 商家入驻申请。

Merchant：

- 店铺和商品 CRUD、调价历史、上下架；
- 进货、库存调整与库存流水；
- 店铺订单处理与状态机；
- 销售额、订单量、热门商品和低库存统计。

Admin：

- 商家审批和状态管理；
- 用户状态、商品强制下架；
- 平台订单、统计和审计日志。

## 测试与质量检查

```bash
docker compose --profile test run --rm --no-deps --entrypoint ruff backend-test check app tests scripts
docker compose --profile test run --rm backend-test pytest -q --cov=app --cov-report=term-missing --cov-fail-under=75
docker compose build frontend
```

关键测试不仅检查 HTTP 状态，还断言 MySQL 最终状态，包括：

- Checkout 中途异常全部 rollback；
- 两用户竞争最后一件库存只允许一方成功；
- 库存与 SALE/RETURN 流水一致；
- 历史订单价格不受后续调价影响；
- 商家所有权与三角色权限隔离；
- 商家申请、审批、上架、下单、支付、发货和审计的完整 E2E 闭环。

详见 [测试策略](docs/testing.md)。

## 查询优化

```bash
docker compose --profile tools run --rm explain
```

商品浏览查询使用 `(status, category_id, created_at, id)` 复合索引，商家订单队列使用 `(store_id, status, created_at, id)`。Phase 7 的 MySQL 8.4 实测中，商品索引消除了额外排序，估算扫描行由 10 降至 3。详见 [EXPLAIN 优化案例](docs/query-optimization.md)。

## 数据库与工程决策

- 金额：`DECIMAL(12,2)`，应用层使用 `Decimal`；
- 时间：数据库保存 UTC `DATETIME(6)`；
- 订单：MVP 采用单店购物车/单店订单，避免跨商家状态歧义；
- 库存：稳定按 product ID 顺序加锁，降低死锁概率；
- 追溯：商品价格、库存变更、订单成交内容和管理员动作保留历史；
- Migration：Alembic 可从空库升级到 `d748e43f1680`。

查看迁移：

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

## 目录

```text
backend/                    FastAPI、业务服务、Repository、ORM、Alembic、pytest
frontend/                   Next.js App Router 三角色界面
scripts/seed_data.py        幂等演示数据
scripts/explain_queries.py  MySQL 查询计划工具
docs/                       架构、ERD、API、测试、优化和阶段报告
.github/workflows/          Backend/Frontend CI Quality Gate
docker-compose.yml          MySQL、backend、frontend、test 和 tools
```

## 文档

- [架构设计](docs/architecture.md)
- [ERD](docs/erd.md)
- [数据库结构](docs/database-schema.md)
- [数据库决策](docs/database-decisions.md)
- [API 文档](docs/api.md)
- [测试策略](docs/testing.md)
- [查询优化](docs/query-optimization.md)
- [最终演示流程](docs/demo-guide.md)
- [Phase 7 完成报告](docs/phase-7-report.md)
- [原始项目规范](PROJECT_SPEC.md)

## MVP 边界

项目不包含真实支付、微服务、消息队列、Redis 强依赖、复杂物流、优惠券、退款结算、图片上传或推荐系统。它聚焦关系型数据库建模、事务一致性、权限、可追溯业务和可验证的完整交易闭环。
