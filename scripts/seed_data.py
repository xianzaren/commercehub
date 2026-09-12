"""Create deterministic local demo data without deleting user-created records."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import build_engine
from app.models.audit import AuditLog
from app.models.catalog import Category, Inventory, InventoryTransaction, Product, ProductPrice
from app.models.enums import (
    CategoryStatus,
    InventoryTransactionType,
    MerchantStatus,
    OrderPaymentStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ProductStatus,
    StoreStatus,
    UserRole,
    UserStatus,
)
from app.models.order import Address, Order, OrderItem, Payment
from app.models.user import Merchant, Store, User

DEMO_PASSWORD = "Demo1234!"
NOW = datetime.now(UTC).replace(tzinfo=None)


def get_or_create_user(session: Session, email: str, role: UserRole) -> User:
    user = session.scalar(select(User).where(User.email == email))
    password_hash = hash_password(DEMO_PASSWORD)
    if user is None:
        user = User(
            email=email,
            password_hash=password_hash,
            role=role,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        session.flush()
    else:
        user.password_hash = password_hash
        user.role = role
        user.status = UserStatus.ACTIVE
    return user


def get_or_create_category(session: Session, name: str, slug: str) -> Category:
    category = session.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        category = Category(name=name, slug=slug, status=CategoryStatus.ACTIVE)
        session.add(category)
        session.flush()
    else:
        category.name = name
        category.status = CategoryStatus.ACTIVE
    return category


def get_or_create_merchant(session: Session, user: User, name: str, admin: User) -> Merchant:
    merchant = session.scalar(select(Merchant).where(Merchant.user_id == user.id))
    if merchant is None:
        merchant = Merchant(user_id=user.id, business_name=name)
        session.add(merchant)
        session.flush()
    merchant.business_name = name
    merchant.status = MerchantStatus.ACTIVE
    merchant.approved_at = NOW - timedelta(days=90)
    merchant.approved_by = admin.id
    return merchant


def get_or_create_store(session: Session, merchant: Merchant, name: str, description: str) -> Store:
    store = session.scalar(select(Store).where(Store.merchant_id == merchant.id))
    if store is None:
        store = Store(merchant_id=merchant.id, name=name, description=description)
        session.add(store)
        session.flush()
    store.name = name
    store.description = description
    store.status = StoreStatus.ACTIVE
    return store


def get_or_create_product(
    session: Session,
    store: Store,
    category: Category,
    sku: str,
    name: str,
    description: str,
    price: Decimal,
    status: ProductStatus,
) -> Product:
    product = session.scalar(
        select(Product).where(Product.store_id == store.id, Product.sku == sku)
    )
    if product is None:
        product = Product(
            store_id=store.id,
            category_id=category.id,
            sku=sku,
            name=name,
            description=description,
            current_price=price,
            status=status,
        )
        session.add(product)
        session.flush()
    else:
        product.category_id = category.id
        product.name = name
        product.description = description
        product.current_price = price
        product.status = status
        product.deleted_at = None
    return product


def ensure_address(session: Session, user: User, recipient: str, phone: str) -> Address:
    address = session.scalar(select(Address).where(Address.user_id == user.id))
    if address is None:
        address = Address(
            user_id=user.id,
            recipient_name=recipient,
            phone=phone,
            province="上海市",
            city="上海市",
            district="浦东新区",
            detail="张江路 88 号 CommerceHub 演示地址",
            postal_code="201210",
            is_default=True,
        )
        session.add(address)
        session.flush()
    return address


def ensure_order(
    session: Session,
    sequence: int,
    customer: User,
    store: Store,
    product: Product,
    quantity: int,
    status: OrderStatus,
    days_ago: int,
) -> Order:
    order_no = f"DEMO-202609-{sequence:04d}"
    order = session.scalar(select(Order).where(Order.order_no == order_no))
    if order is not None:
        return order

    created_at = NOW - timedelta(days=days_ago)
    total = product.current_price * quantity
    paid = status in {
        OrderStatus.PAID,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.COMPLETED,
    }
    order = Order(
        order_no=order_no,
        user_id=customer.id,
        store_id=store.id,
        address_snapshot={
            "recipient_name": "演示用户",
            "phone": "13800138000",
            "province": "上海市",
            "city": "上海市",
            "district": "浦东新区",
            "detail": "张江路 88 号",
            "postal_code": "201210",
        },
        status=status,
        subtotal=total,
        total_amount=total,
        payment_status=OrderPaymentStatus.PAID if paid else OrderPaymentStatus.UNPAID,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(order)
    session.flush()
    session.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            store_id=store.id,
            product_name_snapshot=product.name,
            sku_snapshot=product.sku,
            unit_price=product.current_price,
            quantity=quantity,
            subtotal=total,
        )
    )
    payment_status = (
        PaymentStatus.PAID
        if paid
        else (PaymentStatus.FAILED if status == OrderStatus.CANCELLED else PaymentStatus.PENDING)
    )
    session.add(
        Payment(
            order_id=order.id,
            payment_no=f"DEMO-PAY-{sequence:04d}",
            idempotency_key=f"demo-payment-{sequence:04d}",
            method=PaymentMethod.MOCK_CARD if sequence % 2 else PaymentMethod.MOCK_WALLET,
            amount=total,
            status=payment_status,
            paid_at=created_at + timedelta(minutes=3) if paid else None,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    return order


def ensure_inventory_history(
    session: Session,
    products: list[tuple[Product, int]],
    seeded_orders: list[Order],
) -> None:
    order_items = {
        item.order_id: item
        for item in session.scalars(
            select(OrderItem).where(OrderItem.order_id.in_([order.id for order in seeded_orders]))
        )
    }
    deductions: dict[int, int] = defaultdict(int)
    for order in seeded_orders:
        if order.status != OrderStatus.CANCELLED:
            deductions[order_items[order.id].product_id] += order_items[order.id].quantity

    for product, target in products:
        inventory = session.get(Inventory, product.id)
        if inventory is None:
            inventory = Inventory(product_id=product.id, quantity=target, version=1, updated_at=NOW)
            session.add(inventory)
        else:
            inventory.quantity = target
            inventory.updated_at = NOW

        initial_quantity = target + deductions[product.id]
        initial_exists = session.scalar(
            select(InventoryTransaction.id).where(
                InventoryTransaction.product_id == product.id,
                InventoryTransaction.reference_type == "SEED_INIT",
            )
        )
        if initial_exists is None and initial_quantity > 0:
            session.add(
                InventoryTransaction(
                    product_id=product.id,
                    type=InventoryTransactionType.RESTOCK,
                    quantity_change=initial_quantity,
                    quantity_before=0,
                    quantity_after=initial_quantity,
                    reference_type="SEED_INIT",
                    reference_id=product.id,
                    reason="Phase 7 deterministic demo inventory",
                    created_by=None,
                    created_at=NOW - timedelta(days=45),
                )
            )

    running = {product.id: target + deductions[product.id] for product, target in products}
    for order in sorted(seeded_orders, key=lambda value: value.created_at):
        item = order_items[order.id]
        sale_exists = session.scalar(
            select(InventoryTransaction.id).where(
                InventoryTransaction.reference_type == "ORDER",
                InventoryTransaction.reference_id == order.id,
                InventoryTransaction.type == InventoryTransactionType.SALE,
            )
        )
        if sale_exists is None:
            before = running[item.product_id]
            after = before - item.quantity
            session.add(
                InventoryTransaction(
                    product_id=item.product_id,
                    type=InventoryTransactionType.SALE,
                    quantity_change=-item.quantity,
                    quantity_before=before,
                    quantity_after=after,
                    reference_type="ORDER",
                    reference_id=order.id,
                    reason="Phase 7 demo order",
                    created_by=order.user_id,
                    created_at=order.created_at,
                )
            )
            running[item.product_id] = after
        if order.status == OrderStatus.CANCELLED:
            return_exists = session.scalar(
                select(InventoryTransaction.id).where(
                    InventoryTransaction.reference_type == "ORDER",
                    InventoryTransaction.reference_id == order.id,
                    InventoryTransaction.type == InventoryTransactionType.RETURN,
                )
            )
            if return_exists is None:
                before = running[item.product_id]
                after = before + item.quantity
                session.add(
                    InventoryTransaction(
                        product_id=item.product_id,
                        type=InventoryTransactionType.RETURN,
                        quantity_change=item.quantity,
                        quantity_before=before,
                        quantity_after=after,
                        reference_type="ORDER",
                        reference_id=order.id,
                        reason="Phase 7 cancelled demo order",
                        created_by=order.user_id,
                        created_at=order.created_at + timedelta(minutes=10),
                    )
                )
                running[item.product_id] = after


def seed() -> dict[str, int]:
    engine = build_engine(get_settings().database_url)
    try:
        with Session(engine) as session, session.begin():
            legacy_domains = ["admin", "customer1", "customer2", "merchant1", "merchant2"]
            for account in legacy_domains:
                old_email = f"{account}@commercehub.local"
                new_email = f"{account}@commercehub.example.com"
                legacy_user = session.scalar(select(User).where(User.email == old_email))
                current_user = session.scalar(select(User).where(User.email == new_email))
                if legacy_user is not None and current_user is None:
                    legacy_user.email = new_email

            admin = get_or_create_user(
                session, "admin@commercehub.example.com", UserRole.ADMIN
            )
            customers = [
                get_or_create_user(
                    session, "customer1@commercehub.example.com", UserRole.CUSTOMER
                ),
                get_or_create_user(
                    session, "customer2@commercehub.example.com", UserRole.CUSTOMER
                ),
            ]
            merchant_users = [
                get_or_create_user(
                    session, "merchant1@commercehub.example.com", UserRole.MERCHANT
                ),
                get_or_create_user(
                    session, "merchant2@commercehub.example.com", UserRole.MERCHANT
                ),
            ]
            ensure_address(session, customers[0], "陈晨", "13800138000")
            ensure_address(session, customers[1], "林晓", "13900139000")

            category_specs = [
                ("数码办公", "digital-office"),
                ("居家生活", "home-living"),
                ("运动户外", "sports-outdoor"),
                ("食品饮品", "food-drink"),
                ("图书文创", "books-creative"),
                ("个人护理", "personal-care"),
            ]
            categories = [get_or_create_category(session, *spec) for spec in category_specs]
            merchants = [
                get_or_create_merchant(session, merchant_users[0], "星云数码", admin),
                get_or_create_merchant(session, merchant_users[1], "山海生活", admin),
            ]
            stores = [
                get_or_create_store(
                    session, merchants[0], "星云数码旗舰店", "精选效率工具与数码配件"
                ),
                get_or_create_store(
                    session, merchants[1], "山海生活研究所", "可靠、耐用的日常生活好物"
                ),
            ]

            product_specs = [
                (
                    0,
                    0,
                    "NEB-KB-001",
                    "机械键盘 K87",
                    "热插拔轴体与三模连接",
                    "399.00",
                    18,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-MS-002",
                    "静音无线鼠标",
                    "轻量人体工学设计",
                    "129.00",
                    3,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-HUB-003",
                    "九合一扩展坞",
                    "支持 4K HDMI 与千兆网口",
                    "269.00",
                    0,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-HD-004",
                    "降噪头戴耳机",
                    "通勤与专注场景双模式",
                    "699.00",
                    12,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-SSD-005",
                    "移动固态硬盘 1TB",
                    "高速便携存储",
                    "599.00",
                    7,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    4,
                    "NEB-NOTE-006",
                    "效率手账套装",
                    "项目规划与周复盘模板",
                    "59.90",
                    25,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    4,
                    "NEB-BOOK-007",
                    "数据库设计实践",
                    "关系建模与查询优化案例",
                    "89.00",
                    4,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-CAM-008",
                    "1080P 视频会议摄像头",
                    "自动曝光与双麦克风",
                    "239.00",
                    9,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-STAND-009",
                    "铝合金笔记本支架",
                    "六档高度调节",
                    "119.00",
                    2,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-LAMP-010",
                    "屏幕挂灯 Pro",
                    "非对称光源减少眩光",
                    "329.00",
                    15,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-PAD-011",
                    "羊毛毡桌垫",
                    "桌面收纳与防滑",
                    "79.00",
                    20,
                    ProductStatus.INACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-CABLE-012",
                    "编织数据线套装",
                    "三种长度 USB-C 快充线",
                    "49.90",
                    30,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    1,
                    "SEA-CUP-001",
                    "真空保温杯",
                    "316 不锈钢内胆",
                    "159.00",
                    16,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    1,
                    "SEA-PILLOW-002",
                    "记忆棉护颈枕",
                    "分区承托可拆洗",
                    "219.00",
                    5,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    2,
                    "SEA-BAG-003",
                    "轻量徒步背包 28L",
                    "透气背负与防泼水面料",
                    "359.00",
                    8,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    2,
                    "SEA-BOTTLE-004",
                    "运动水壶 1L",
                    "刻度提醒与防漏锁扣",
                    "89.00",
                    1,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-COFFEE-005",
                    "精品挂耳咖啡 10 包",
                    "中度烘焙坚果风味",
                    "68.00",
                    22,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-TEA-006",
                    "冷泡茶组合",
                    "四种无糖原叶茶",
                    "52.00",
                    0,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    5,
                    "SEA-TOWEL-007",
                    "速干运动毛巾",
                    "抗菌纤维便携收纳",
                    "45.00",
                    14,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    5,
                    "SEA-WASH-008",
                    "氨基酸洁面",
                    "温和清洁 120ml",
                    "79.00",
                    11,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    1,
                    "SEA-BOX-009",
                    "模块化收纳盒",
                    "抽屉式组合设计",
                    "99.00",
                    6,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    2,
                    "SEA-MAT-010",
                    "防滑瑜伽垫",
                    "高密度缓震材质",
                    "139.00",
                    17,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    4,
                    "SEA-POSTER-011",
                    "城市建筑海报",
                    "环保纸张四色印刷",
                    "39.00",
                    28,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    1,
                    "SEA-AROMA-012",
                    "木质香薰蜡烛",
                    "雪松与无花果香调",
                    "109.00",
                    4,
                    ProductStatus.DRAFT,
                ),
            ]
            products_with_stock: list[tuple[Product, int]] = []
            for (
                store_index,
                category_index,
                sku,
                name,
                description,
                price,
                stock,
                product_status,
            ) in product_specs:
                product = get_or_create_product(
                    session,
                    stores[store_index],
                    categories[category_index],
                    sku,
                    name,
                    description,
                    Decimal(price),
                    product_status,
                )
                products_with_stock.append((product, stock))

            for product, _ in products_with_stock[:6]:
                history = session.scalar(
                    select(ProductPrice.id).where(ProductPrice.product_id == product.id)
                )
                if history is None:
                    session.add(
                        ProductPrice(
                            product_id=product.id,
                            old_price=product.current_price + Decimal("20.00"),
                            new_price=product.current_price,
                            changed_by=merchant_users[0].id,
                            changed_at=NOW - timedelta(days=20),
                        )
                    )

            order_specs = [
                (1, 0, 0, 2, OrderStatus.COMPLETED, 28),
                (2, 1, 12, 1, OrderStatus.COMPLETED, 21),
                (3, 0, 1, 2, OrderStatus.SHIPPED, 12),
                (4, 1, 14, 1, OrderStatus.PROCESSING, 8),
                (5, 0, 4, 1, OrderStatus.PAID, 4),
                (6, 1, 16, 3, OrderStatus.PAID, 2),
                (7, 0, 6, 1, OrderStatus.PENDING_PAYMENT, 1),
                (8, 1, 18, 2, OrderStatus.CANCELLED, 3),
            ]
            seeded_orders = []
            for (
                sequence,
                customer_index,
                product_index,
                quantity,
                order_status,
                days_ago,
            ) in order_specs:
                store_index = product_specs[product_index][0]
                seeded_orders.append(
                    ensure_order(
                        session,
                        sequence,
                        customers[customer_index],
                        stores[store_index],
                        products_with_stock[product_index][0],
                        quantity,
                        order_status,
                        days_ago,
                    )
                )
            session.flush()
            ensure_inventory_history(session, products_with_stock, seeded_orders)

            audit_exists = session.scalar(
                select(AuditLog.id).where(AuditLog.action == "DEMO_DATA_SEEDED")
            )
            if audit_exists is None:
                session.add(
                    AuditLog(
                        actor_user_id=admin.id,
                        actor_role=UserRole.ADMIN,
                        action="DEMO_DATA_SEEDED",
                        entity_type="SYSTEM",
                        entity_id=1,
                        before_data=None,
                        after_data={"products": 24, "orders": 8},
                        created_at=NOW,
                    )
                )

            counts = {
                "users": int(session.scalar(select(func.count(User.id))) or 0),
                "categories": int(session.scalar(select(func.count(Category.id))) or 0),
                "stores": int(session.scalar(select(func.count(Store.id))) or 0),
                "products": int(session.scalar(select(func.count(Product.id))) or 0),
                "orders": int(session.scalar(select(func.count(Order.id))) or 0),
            }
        return counts
    finally:
        engine.dispose()


if __name__ == "__main__":
    result = seed()
    print(
        "CommerceHub demo data is ready:",
        ", ".join(f"{key}={value}" for key, value in result.items()),
    )
    print("Demo password for all accounts:", DEMO_PASSWORD)
