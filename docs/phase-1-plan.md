# Phase 1 实施清单

目标：从空目录得到可由 `docker compose up --build` 启动、可由 Alembic 从空 MySQL 数据库迁移至最新 schema 的项目骨架。Phase 1 不实现完整认证或业务流程。

## 1. 仓库与配置

- 初始化 Git 仓库和主分支。
- 添加 Python、Node、Docker、IDE 和环境变量对应的 `.gitignore`。
- 创建 `.env.example`，包含数据库名、应用账户、JWT secret 占位和前端 API URL。
- 运行时 `.env` 由本地生成且不提交。
- 根 README 增加启动、停止、迁移和测试命令。

验收：`git status` 不出现 `.env`、缓存、数据库 volume 或 node_modules。

## 2. Backend skeleton

- 创建 `backend/pyproject.toml` 并锁定兼容版本范围。
- 创建 FastAPI app factory/main、`/health/live` 和 `/health/ready`。
- 建立 config、logging、errors、database session 和 declarative base。
- 创建 Router/Service/Repository/Schema/Model 包边界。
- 添加 Ruff/pytest 基础配置。

验收：应用导入成功；live health 不依赖 DB；ready health 能区分数据库可用与不可用。

## 3. SQLAlchemy models

- 实现 Phase 0 定义的 15 张表。
- 添加命名约定，使 Alembic 约束名稳定。
- 实现 UTC timestamp mixin，但避免把不适用字段强塞进所有表。
- 使用 Python Enum + VARCHAR/CHECK。
- 实现 carts.active_user_id 和 payments.paid_order_id 生成列。
- 为金额和索引定义写 model-level 测试。

验收：metadata 中表、FK、唯一约束、CHECK 和索引与 schema 文档一致。

## 4. Alembic

- 初始化 Alembic，连接串来自环境变量。
- 导入完整 model metadata。
- 生成并人工检查 initial schema migration。
- 处理 MySQL 生成列、CHECK、索引和 FK 删除策略。
- 提供 upgrade/downgrade；downgrade 仅用于开发测试库。

验收：全新数据库执行 `alembic upgrade head` 成功，`alembic current` 指向 head。

## 5. Docker Compose

- mysql：MySQL 8 固定镜像、健康检查、命名 volume、utf8mb4 配置。
- backend：固定 Python 基础镜像、非 root 用户、健康检查、等待 MySQL healthy。
- frontend：Phase 1 只创建可启动占位骨架或 profile，不开展 Phase 6 页面开发。
- 网络和端口使用 Compose 默认网络；数据库端口仅为本地调试暴露。
- secret 只通过 `.env` 注入。

验收：`docker compose config` 成功；`docker compose up --build` 后 MySQL 与 backend healthy。

## 6. Repository baseline

- 提供通用分页数据结构，不创建万能 Generic CRUD Repository。
- 为 User、Product、Inventory 提供最小专用 Repository 接口示例。
- Repository 不 commit；事务提交权属于 Service/request transaction manager。

验收：集成测试能写入并读取最小关联实体；Repository 不泄露 HTTP 异常。

## 7. Migration 与数据库测试

- 空库升级到 head。
- downgrade base 后再次 upgrade head。
- 验证 email、store SKU、cart item 等唯一约束。
- 验证库存非负和金额正数 CHECK。
- 验证生成列条件唯一性。
- 验证关键 FK 的 RESTRICT/CASCADE 行为。

所有数据库行为测试使用 MySQL，不能用 SQLite 替代。

## 8. Phase 1 完成条件

```text
docker compose config                         PASS
docker compose up --build                     PASS
docker compose exec backend alembic upgrade head  PASS
pytest tests/unit                             PASS
pytest tests/integration                      PASS
curl /health/live                             200
curl /health/ready                            200
```

交付报告包含：完成内容、主要文件、准确测试命令与结果、已知问题。按照用户要求，Phase 1 完成后自动继续 Phase 2，不等待人工 Gate。
