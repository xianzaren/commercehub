# CommerceHub 最终演示流程

## 准备

```bash
docker compose up -d --build
docker compose --profile tools run --rm seed
```

打开：

- Web：http://localhost:3000
- Swagger：http://localhost:8000/docs

所有演示账号密码均为 `Demo1234!`：

| 角色 | 账号 |
|---|---|
| ADMIN | `admin@commercehub.example.com` |
| MERCHANT | `merchant1@commercehub.example.com` |
| MERCHANT | `merchant2@commercehub.example.com` |
| CUSTOMER | `customer1@commercehub.example.com` |
| CUSTOMER | `customer2@commercehub.example.com` |

这些只是假数据凭据，禁止用于真实环境。

## 浏览器演示

1. 使用 CUSTOMER 登录，在商品市场搜索“机械键盘”。
2. 进入详情并加入购物车；在地址簿确认演示地址。
3. Checkout 创建订单并进行模拟支付。
4. 退出后使用对应店铺的 MERCHANT 登录。
5. 在订单处理中将新订单从 PAID 更新为 PROCESSING，再更新为 SHIPPED。
6. 在商品管理中查看库存减少，并展示库存中心的可追溯库存数据。
7. 在经营概览查看订单量、销售额、热门商品和低库存提醒。
8. 退出后使用 ADMIN 登录，查看平台统计、订单与审计日志。
9. 如需演示商家入驻，注册一个新 CUSTOMER，提交申请，再由 ADMIN 审批；该账号重新登录后会进入商家工作台。

## 数据库工程证据

运行完整 MySQL 测试和覆盖率门槛：

```bash
docker compose --profile test run --rm backend-test pytest -q --cov=app --cov-report=term-missing --cov-fail-under=75
```

重点展示：

- checkout 失败时订单、订单项、支付、库存和流水整体 rollback；
- 两个用户并发抢最后一件商品，仅一方成功；
- 调价后历史订单仍保留原成交价；
- 取消订单恢复库存并写 RETURN 流水；
- E2E 测试贯穿 Customer、Merchant、Admin 三角色。

运行真实查询计划：

```bash
docker compose --profile tools run --rm explain
```

说明 `ix_products_browse` 如何消除商品筛选后的 filesort，以及 `ix_orders_store_status_created` 如何支持商家订单队列。

## 演示恢复

Seed 是幂等的，可重复执行。它只恢复固定演示账号和演示业务记录，不删除用户自行创建的数据：

```bash
docker compose --profile tools run --rm seed
```
