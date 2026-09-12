# Phase 1 完成报告

## 完成内容

- 建立 FastAPI、SQLAlchemy 2.x、Alembic 和分层目录骨架。
- 建立 Next.js 16 + React 19 + TypeScript 7 的可运行生产构建骨架。
- 建立 MySQL 8.4、backend、frontend 三服务 Docker Compose。
- 通过 SQLAlchemy 与初始 migration 实现 15 张领域表。
- 实现主外键、删除策略、CHECK、唯一约束、组合索引与两项生成列唯一约束。
- 建立 User、Product、Inventory 专用 Repository 基线和分页 schema。
- 提供 live/ready 健康检查，ready 会真实查询数据库。
- 提供独立 MySQL 测试库和 backend-test Compose profile。
- 镜像使用已验证的官方 digest，运行容器使用非 root 用户。

## 验证结果

```text
docker compose config --quiet                         PASS
docker compose build                                  PASS
Next.js production build                              PASS
Ruff app tests                                        PASS
pytest                                                14 passed
Alembic downgrade base -> upgrade head                PASS
Alembic current                                       d748e43f1680 (head)
MySQL domain tables                                   15
GET /health/live                                      200
GET /health/ready                                     200 / database reachable
GET http://localhost:3000                             200
mysql/backend/frontend health                         healthy/healthy/healthy
```

MySQL information_schema 显示 16 张表，其中 15 张为领域表，另 1 张为 Alembic 版本表。

## 集成过程中发现并修正

1. MySQL 8.4 默认 caching_sha2_password 需要 cryptography；已加入依赖，没有降级认证方式。
2. `DATETIME` 配合 `CURRENT_TIMESTAMP(6)` 被 MySQL 拒绝；所有时间字段统一为 `DATETIME(6)`。
3. Alembic 自动 downgrade 先删除外键依赖索引会失败；已改为按依赖顺序直接删表。
4. 测试容器可能优先读取已安装 wheel；已固定 `PYTHONPATH=/app`，确保测试当前挂载源码。

## 主要文件

- `docker-compose.yml`、`.env.example`、`.gitignore`
- `backend/app/main.py`、`backend/app/core/`、`backend/app/db/`
- `backend/app/models/`、`backend/app/repositories/`
- `backend/alembic/versions/d748e43f1680_initial_schema.py`
- `backend/tests/unit/`、`backend/tests/integration/`
- `frontend/app/`、`frontend/Dockerfile`、`frontend/package-lock.json`

## 已知事项

- 本机直接通过 PyPI 安装依赖时网络 TLS 不稳定；Docker 构建网络正常，因此标准开发与测试流程统一使用容器。
- pytest 输出一条 Starlette/AnyIO 上游弃用警告，不影响行为；升级 FastAPI/Starlette 时再处理。
- Phase 1 前端仅为健康占位页，三角色交互页面属于 Phase 6。

## 下一阶段

Phase 2 将实现注册、登录、Argon2 密码哈希、JWT cookie/Bearer、角色依赖、账户冻结即时生效和相应 API/数据库测试。
