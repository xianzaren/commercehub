# CommerceHub

CommerceHub 是一个可在本地完整运行的多角色购物平台，包含普通用户、商家和管理员三套操作界面。项目内置中文商城页面、演示商品和演示账号，适合用于功能体验、课程展示和简历项目演示。

## 应用功能

### 普通用户

- 注册、登录和退出账号；
- 浏览商品分类、标签、店铺、库存和销量；
- 输入关键词获得搜索建议，按 Enter 搜索后结果按匹配程度排序；
- 查看商品图片、详情和 SKU 规格，并将选定规格加入购物车；
- 收藏喜欢的商品，并查看最近浏览记录；
- 管理收货地址、提交订单和模拟支付；
- 查看订单详情、支付状态和取消订单；
- 提交商家入驻申请。

### 商家

- 维护店铺资料；
- 新建、编辑、上下架和删除商品；
- 设置商品标签和价格，查看调价记录；
- 进货、调整库存并查看库存流水；
- 处理店铺订单；
- 查看销售额、订单量、热门商品和低库存提醒。

### 管理员

- 审核商家入驻申请；
- 管理用户、商家和店铺状态；
- 查看并处理平台商品；
- 查看平台订单和经营概览；
- 查看管理员操作记录。

## 当前演示内容

- 10 个商品分类；
- 62 条商品数据，其中 60 件正在销售；
- 商品卡片显示图片、标签、店铺名称、库存状态和真实订单销量；
- 12 件代表商品提供 26 个颜色、容量、尺寸或型号 SKU；
- 两家演示店铺；
- 完整的下单、支付、商家发货和订单完成流程。

## 启动应用

请先安装并启动 Docker Desktop。

Windows PowerShell：

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose --profile tools run --rm seed
```

macOS 或 Linux：

```bash
cp .env.example .env
docker compose up -d --build
docker compose --profile tools run --rm seed
```

启动完成后访问：

- 商城页面：http://localhost:3000
- 接口说明：http://localhost:8000/docs

关闭应用：

```bash
docker compose down
```

普通关闭不会清除已经保存的数据。

## 演示账号

所有演示账号的密码均为 `Demo1234!`。

| 身份 | 账号 |
|---|---|
| 普通用户 | `customer1@commercehub.example.com` |
| 普通用户 | `customer2@commercehub.example.com` |
| 商家 | `merchant1@commercehub.example.com` |
| 商家 | `merchant2@commercehub.example.com` |
| 管理员 | `admin@commercehub.example.com` |

## 推荐体验流程

1. 使用普通用户账号登录，搜索商品并加入购物车；
2. 选择收货地址，提交订单并完成模拟支付；
3. 切换到对应商家账号，处理并发货；
4. 返回普通用户账号查看订单进度；
5. 使用管理员账号查看平台订单、商家和操作记录。

更详细的操作步骤可查看 [演示指南](docs/demo-guide.md)。

## 说明

项目中的支付、商品、店铺和账号均为本地演示数据，不会产生真实交易。重新运行 Seed 命令可以补全演示数据，并且不会删除用户自行创建的内容。
