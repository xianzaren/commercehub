# Phase 2 完成报告

## 完成内容

- CUSTOMER 注册，邮箱规范化和数据库唯一性冲突处理。
- Argon2id 密码哈希与参数升级检测；密码从不明文存储。
- 统一错误凭据响应，并使用 dummy hash 减少邮箱存在性的计时差异。
- JWT access token，包含 sub、role、jti、iat、exp、issuer 和 audience。
- HttpOnly/SameSite cookie 与 Authorization Bearer 双认证入口。
- 每个请求回查 users.status 和 role，冻结或角色变化立即生效。
- CUSTOMER、MERCHANT、ADMIN 角色依赖。
- 商家端额外校验 merchants.status=ACTIVE。
- Register/Login/Me/Logout 和三类角色验证端点。
- API 使用说明与自动化测试。

## 测试结果

```text
Phase 1 regression                                  PASS
Ruff                                                PASS
pytest                                              25 passed
Argon2 hash / correct and wrong password            PASS
JWT round trip / tamper / expiration                PASS
register / duplicate email / login / me / logout    PASS
CUSTOMER -> ADMIN                                   403
suspended user with existing token                  403
ACTIVE merchant -> merchant endpoint                200
PENDING merchant -> merchant endpoint               403
ADMIN -> admin endpoint                              200
Alembic schema drift                                none
backend runtime health                              healthy
```

pytest 仍有一条 Starlette/AnyIO 上游弃用警告，不影响测试结果。

## Schema

Phase 2 没有修改数据库结构，因此没有新增 migration。`alembic check` 返回 `No new upgrade operations detected`。

## 下一阶段

Phase 3 将实现商家申请/审批、店铺、商品 CRUD、软删除、上下架、调价历史、进货、库存调整、库存流水与资源所有权测试。
