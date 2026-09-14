# CommerceHub

[English](README.md) | **简体中文**

CommerceHub 是一个可在本地完整运行的多角色购物平台，包含普通用户、商家和管理员三套操作界面。项目内置中文商城页面、演示商品和演示账号，适合用于功能体验、课程展示和简历项目演示。

## 技术栈

| 层级 | 技术 | 职责 |
|---|---|---|
| 前端 | Next.js 16、React 19、TypeScript | 商城页面及用户、商家、管理员工作流 |
| 后端 | FastAPI、SQLAlchemy 2、Pydantic | REST API、业务服务、认证与 RBAC |
| 数据库 | MySQL 8、Alembic | 事务数据、迁移、库存、订单和审计记录 |
| 交付 | Docker、Docker Compose | 可复现的本地全栈环境及工具 profiles |
| 质量 | pytest、Ruff、GitHub Actions | 后端测试、覆盖率门禁、代码检查、类型检查和生产构建 |

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

## 项目结构

```text
.
├── backend/              # FastAPI、数据库模型、Alembic 迁移和后端测试
├── frontend/             # Next.js 商城及各角色操作界面
├── docker/               # MySQL 容器配置
├── scripts/              # 演示数据初始化和查询计划检查工具
├── docs/                 # 架构、API、数据库、测试及演示文档
├── docker-compose.yml    # 本地全栈、测试和工具服务编排
└── .env.example          # 环境变量模板
```

后端依赖位于 `backend/pyproject.toml`，前端依赖位于 `frontend/package.json`。
[PROJECT_SPEC.md](PROJECT_SPEC.md) 保留完整需求、数据模型和设计依据；本 README
作为运行和审阅已实现系统的快速入口。

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

这些凭据只为本地演示环境初始化，禁止部署到公开或生产环境，也不要在其他服务中
复用其密码。所有演示账号的密码均为 `Demo1234!`。

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
