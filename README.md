# CommerceHub

**English** | [简体中文](README_CN.md)

CommerceHub is a locally runnable, multi-role shopping platform with dedicated interfaces for customers, merchants, and administrators. It includes a Chinese storefront, demo products, and demo accounts for functional evaluation, coursework demonstrations, and portfolio use.

## Features

### Customers

- Register, sign in, and sign out.
- Browse categories, tags, stores, inventory, and sales counts.
- Receive search suggestions and rank submitted search results by relevance.
- View product images, details, and SKU options, then add a selected SKU to the cart.
- Save favorite products and review recently viewed items.
- Manage delivery addresses, place orders, and complete simulated payments.
- View order details and payment status, and cancel eligible orders.
- Submit a merchant application.

### Merchants

- Maintain store information.
- Create, edit, publish, unpublish, and delete products.
- Manage product tags and prices and inspect price-change history.
- Receive stock, adjust inventory, and inspect inventory movements.
- Process store orders.
- Review revenue, order volume, popular products, and low-stock alerts.

### Administrators

- Review merchant applications.
- Manage user, merchant, and store status.
- Review and manage platform products.
- Inspect platform orders and the operational overview.
- Review administrator audit records.

## Included demo data

- 10 product categories.
- 62 product records, including 60 active listings.
- Product cards with images, tags, store names, inventory status, and order-based sales counts.
- 12 representative products with 26 color, capacity, size, or model SKUs.
- Two demonstration stores.
- A complete order, simulated payment, merchant fulfilment, and completion workflow.

## Project structure

```text
.
├── backend/              # API, database models, migrations, and backend tests
├── frontend/             # Next.js storefront and role-specific interfaces
├── docker/               # MySQL container configuration
├── docs/                 # Architecture, API, database, testing, and demo guides
├── scripts/              # Seed data and query-inspection utilities
├── docker-compose.yml
└── .env.example
```

Backend dependencies are declared in `backend/pyproject.toml`; frontend dependencies are declared in `frontend/package.json`.

## Start the application

Install and start Docker Desktop first.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose --profile tools run --rm seed
```

macOS or Linux:

```bash
cp .env.example .env
docker compose up -d --build
docker compose --profile tools run --rm seed
```

After startup, open:

- Storefront: <http://localhost:3000>
- API documentation: <http://localhost:8000/docs>

Stop the application with:

```bash
docker compose down
```

A normal shutdown does not erase persisted data.

## Demo accounts

All demo accounts use the password `Demo1234!`.

| Role | Account |
|---|---|
| Customer | `customer1@commercehub.example.com` |
| Customer | `customer2@commercehub.example.com` |
| Merchant | `merchant1@commercehub.example.com` |
| Merchant | `merchant2@commercehub.example.com` |
| Administrator | `admin@commercehub.example.com` |

## Suggested demo workflow

1. Sign in as a customer, search for a product, and add it to the cart.
2. Select a delivery address, place the order, and complete the simulated payment.
3. Switch to the corresponding merchant account and fulfil the order.
4. Return to the customer account to review order progress.
5. Sign in as the administrator to inspect platform orders, merchants, and audit records.

See the [demo guide](docs/demo-guide.md) for detailed instructions.

## Notes

Payments, products, stores, and accounts are local demonstration data and do not create real transactions. Running the seed command again fills in missing demo records without deleting content created by users.
