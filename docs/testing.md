# 测试策略与质量门槛

## 分层

| 层级 | 关注点 |
|---|---|
| Unit | 密码/JWT、分页、schema 元数据、健康检查 |
| Integration | Alembic、约束、Repository、RBAC、交易与管理 API |
| Concurrency | 两个独立 Session 竞争最后库存，验证 InnoDB 行锁 |
| E2E | 商家申请到审批、上架、购买、支付、发货和审计的完整闭环 |

测试数据库固定使用 MySQL，不以 SQLite 替代事务、约束或行锁行为。

## 本地质量门槛

```bash
docker compose --profile test run --rm --no-deps --entrypoint ruff backend-test check app tests scripts
docker compose --profile test run --rm backend-test pytest -q --cov=app --cov-report=term-missing --cov-fail-under=75
docker compose build frontend
```

Phase 7 本机结果：

- Ruff：通过；
- pytest：37 项通过；
- 后端语句覆盖率：88.08%；
- Next.js production build 与 TypeScript：通过；
- MySQL、backend、frontend 健康检查：通过。

唯一警告来自 Starlette TestClient 使用 AnyIO 已弃用别名的上游提示，不属于应用失败。

## CI

`.github/workflows/quality.yml` 在 push 与 pull request 时并行执行：

- Backend：MySQL 8.4 service、Alembic、Ruff、pytest、75% coverage gate；
- Frontend：Node 24、`npm ci`、TypeScript、Next.js production build。

任何一个 job 失败，Quality Gate 即失败。
