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
from app.models.catalog import (
    Category,
    Inventory,
    InventoryTransaction,
    Product,
    ProductImage,
    ProductPrice,
    ProductVariant,
)
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
    tags: list[str],
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
            tags=tags,
            current_price=price,
            status=status,
        )
        session.add(product)
        session.flush()
    else:
        product.category_id = category.id
        product.name = name
        product.description = description
        product.tags = tags
        product.current_price = price
        product.status = status
        product.deleted_at = None
    return product


def ensure_product_image(session: Session, product: Product, url: str) -> None:
    image = session.scalar(
        select(ProductImage).where(
            ProductImage.product_id == product.id,
            ProductImage.sort_order == 0,
        )
    )
    if image is None:
        image = ProductImage(
            product_id=product.id,
            url=url,
            alt_text=f"{product.name}商品展示图",
            sort_order=0,
            is_primary=True,
        )
        session.add(image)
    else:
        image.url = url
        image.alt_text = f"{product.name}商品展示图"
        image.is_primary = True


def ensure_product_variants(
    session: Session,
    product: Product,
    variants: list[tuple[str, str, dict[str, str], Decimal]],
) -> None:
    for sort_order, (sku_suffix, name, attributes, price) in enumerate(variants):
        sku = f"{product.sku}-{sku_suffix}"
        variant = session.scalar(
            select(ProductVariant).where(
                ProductVariant.product_id == product.id,
                ProductVariant.sku == sku,
            )
        )
        if variant is None:
            variant = ProductVariant(product_id=product.id, sku=sku)
            session.add(variant)
        variant.name = name
        variant.attributes = attributes
        variant.price = price
        variant.status = "ACTIVE"
        variant.sort_order = sort_order


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

            admin = get_or_create_user(session, "admin@commercehub.example.com", UserRole.ADMIN)
            customers = [
                get_or_create_user(session, "customer1@commercehub.example.com", UserRole.CUSTOMER),
                get_or_create_user(session, "customer2@commercehub.example.com", UserRole.CUSTOMER),
            ]
            merchant_users = [
                get_or_create_user(session, "merchant1@commercehub.example.com", UserRole.MERCHANT),
                get_or_create_user(session, "merchant2@commercehub.example.com", UserRole.MERCHANT),
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
                ("服饰鞋包", "fashion-bags"),
                ("家用电器", "home-appliances"),
                ("母婴用品", "mother-baby"),
                ("宠物生活", "pet-supplies"),
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
                (
                    0,
                    0,
                    "NEB-BAND-013",
                    "轻量智能手环",
                    "睡眠监测与十四天续航",
                    "199.00",
                    32,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-CHARGE-014",
                    "65W 氮化镓充电器",
                    "双 USB-C 接口便携快充",
                    "169.00",
                    26,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-SPEAKER-015",
                    "桌面蓝牙音箱",
                    "立体声与氛围灯效",
                    "259.00",
                    14,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-POWER-016",
                    "磁吸无线充电宝",
                    "10000mAh 双向快充",
                    "189.00",
                    19,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-ROUTER-017",
                    "Wi-Fi 6 千兆路由器",
                    "双频覆盖与游戏加速",
                    "299.00",
                    10,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    7,
                    "SEA-JUICER-013",
                    "便携榨汁杯",
                    "六叶刀头与随行杯设计",
                    "129.00",
                    23,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    7,
                    "SEA-FAN-014",
                    "空气循环扇",
                    "四档风速与低噪送风",
                    "239.00",
                    13,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    7,
                    "SEA-KETTLE-015",
                    "恒温电热水壶",
                    "五档温控与食品级内胆",
                    "179.00",
                    18,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    7,
                    "SEA-HUMID-016",
                    "桌面加湿器",
                    "静音雾化与缺水断电",
                    "89.00",
                    27,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-NUT-017",
                    "每日坚果组合 30 袋",
                    "独立包装与低温烘焙",
                    "119.00",
                    40,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-OAT-018",
                    "无糖燕麦饼干",
                    "全谷物烘焙 600g",
                    "39.90",
                    35,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-HONEY-019",
                    "蜂蜜柚子茶",
                    "清新果香 500g",
                    "49.90",
                    21,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-SAUCE-020",
                    "意式番茄肉酱",
                    "加热即食 200g×3",
                    "56.00",
                    16,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    5,
                    "SEA-MASK-021",
                    "玻尿酸保湿面膜",
                    "清爽补水 20 片",
                    "69.00",
                    31,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    5,
                    "SEA-TOOTH-022",
                    "便携电动牙刷",
                    "声波清洁与旅行收纳",
                    "149.00",
                    12,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    5,
                    "SEA-HAND-023",
                    "香氛护手霜礼盒",
                    "三种香型滋润不粘腻",
                    "79.00",
                    24,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    6,
                    "SEA-TSHIRT-024",
                    "纯棉基础款 T 恤",
                    "宽松剪裁与柔软亲肤面料",
                    "79.00",
                    38,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    6,
                    "SEA-TOTE-025",
                    "通勤帆布托特包",
                    "多分区收纳与加固肩带",
                    "99.00",
                    29,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    6,
                    "SEA-SHOES-026",
                    "轻量缓震跑步鞋",
                    "透气网面与耐磨鞋底",
                    "269.00",
                    20,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    8,
                    "SEA-TISSUE-027",
                    "婴儿棉柔巾 6 包",
                    "干湿两用无香配方",
                    "59.00",
                    45,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    8,
                    "SEA-LUNCH-028",
                    "儿童保温餐盒",
                    "分格密封与便携提手",
                    "139.00",
                    15,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    9,
                    "SEA-CATLIT-029",
                    "低尘膨润土猫砂",
                    "快速结团 10kg",
                    "49.00",
                    34,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    9,
                    "SEA-FOUNTAIN-030",
                    "宠物智能饮水机",
                    "循环过滤与低水位提醒",
                    "159.00",
                    11,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-STAND-018",
                    "折叠磁吸手机支架",
                    "多角度调节与稳固磁吸",
                    "69.00",
                    36,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-MONITOR-019",
                    "27 英寸 4K 显示器",
                    "IPS 广色域与升降旋转支架",
                    "1699.00",
                    9,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    0,
                    "NEB-COMBO-020",
                    "便携无线键鼠套装",
                    "轻薄静音与双模连接",
                    "159.00",
                    22,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    1,
                    "SEA-BEDDING-031",
                    "水洗棉四件套",
                    "柔软亲肤，适合四季使用",
                    "299.00",
                    17,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    1,
                    "SEA-LAMP-032",
                    "原木落地阅读灯",
                    "无频闪暖光与脚踏开关",
                    "269.00",
                    12,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    1,
                    "SEA-RACK-033",
                    "免打孔厨房置物架",
                    "加厚碳钢与灵活分层收纳",
                    "89.00",
                    28,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    2,
                    "SEA-BAND-034",
                    "五档健身弹力带",
                    "居家塑形与便携收纳",
                    "49.00",
                    42,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    2,
                    "SEA-PICNIC-035",
                    "防潮加厚野餐垫",
                    "可折叠提手与防水底层",
                    "109.00",
                    25,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    2,
                    "SEA-CAMP-036",
                    "充电式露营灯",
                    "三档调光与应急充电",
                    "129.00",
                    18,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-STRAW-037",
                    "冻干草莓脆 6 袋",
                    "无添加蔗糖，保留自然果香",
                    "45.90",
                    33,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-CHOCO-038",
                    "黑巧克力礼盒",
                    "72% 可可含量，独立包装",
                    "69.00",
                    27,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    3,
                    "SEA-OOLONG-039",
                    "桂花乌龙茶 20 包",
                    "原叶三角茶包，清香回甘",
                    "58.00",
                    31,
                    ProductStatus.ACTIVE,
                ),
                (
                    0,
                    4,
                    "NEB-PYBOOK-021",
                    "Python 数据分析实战",
                    "从数据清洗到可视化的项目案例",
                    "99.00",
                    16,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    4,
                    "SEA-JOURNAL-040",
                    "城市旅行手账",
                    "地图页与行程记录模板",
                    "49.00",
                    24,
                    ProductStatus.ACTIVE,
                ),
                (
                    1,
                    9,
                    "SEA-SCRATCH-041",
                    "瓦楞纸猫抓板",
                    "加厚耐抓与猫薄荷夹层",
                    "39.90",
                    39,
                    ProductStatus.ACTIVE,
                ),
            ]
            product_tags = {
                "NEB-KB-001": ["热卖", "三模连接", "包邮"],
                "NEB-MS-002": ["静音", "人体工学"],
                "NEB-HUB-003": ["办公必备", "多接口"],
                "NEB-HD-004": ["降噪", "沉浸音质", "包邮"],
                "NEB-SSD-005": ["高速传输", "大容量"],
                "NEB-BAND-013": ["新品", "健康监测", "长续航"],
                "NEB-CHARGE-014": ["快充", "小巧便携", "包邮"],
                "NEB-SPEAKER-015": ["氛围灯", "立体声"],
                "NEB-POWER-016": ["磁吸", "大容量", "快充"],
                "NEB-ROUTER-017": ["Wi-Fi 6", "全屋覆盖"],
                "SEA-COFFEE-005": ["热卖", "独立包装", "包邮"],
                "SEA-TEA-006": ["无糖", "冷泡即饮"],
                "SEA-JUICER-013": ["新品", "便携", "易清洗"],
                "SEA-FAN-014": ["低噪", "节能"],
                "SEA-KETTLE-015": ["恒温", "食品级内胆"],
                "SEA-HUMID-016": ["静音", "缺水断电"],
                "SEA-NUT-017": ["热卖", "每日营养", "独立包装"],
                "SEA-OAT-018": ["无糖", "全谷物", "轻食"],
                "SEA-HONEY-019": ["果香", "冲泡方便"],
                "SEA-SAUCE-020": ["加热即食", "家庭装"],
                "SEA-MASK-021": ["补水", "温和配方", "热卖"],
                "SEA-TOOTH-022": ["声波清洁", "旅行装"],
                "SEA-HAND-023": ["礼盒", "滋润", "三种香型"],
                "SEA-TSHIRT-024": ["纯棉", "基础百搭", "包邮"],
                "SEA-TOTE-025": ["通勤", "大容量", "多分区"],
                "SEA-SHOES-026": ["缓震", "透气", "轻量"],
                "SEA-TISSUE-027": ["母婴适用", "无香", "干湿两用"],
                "SEA-LUNCH-028": ["保温", "分格密封"],
                "SEA-CATLIT-029": ["低尘", "快速结团", "实惠装"],
                "SEA-FOUNTAIN-030": ["循环过滤", "静音", "智能提醒"],
                "NEB-STAND-018": ["磁吸", "折叠便携", "桌面好物"],
                "NEB-MONITOR-019": ["4K 高清", "广色域", "升降旋转"],
                "NEB-COMBO-020": ["静音", "双模连接", "轻薄便携"],
                "SEA-BEDDING-031": ["水洗棉", "四季适用", "亲肤"],
                "SEA-LAMP-032": ["无频闪", "原木风", "暖光阅读"],
                "SEA-RACK-033": ["免打孔", "分层收纳", "加厚碳钢"],
                "SEA-BAND-034": ["五档阻力", "居家健身", "便携"],
                "SEA-PICNIC-035": ["防潮", "可折叠", "户外出游"],
                "SEA-CAMP-036": ["三档调光", "可充电", "应急照明"],
                "SEA-STRAW-037": ["无添加蔗糖", "酥脆", "独立包装"],
                "SEA-CHOCO-038": ["72% 可可", "礼盒", "独立包装"],
                "SEA-OOLONG-039": ["原叶茶包", "桂花香", "冷泡热泡"],
                "NEB-PYBOOK-021": ["项目实战", "数据分析", "案例丰富"],
                "SEA-JOURNAL-040": ["旅行记录", "地图页", "文艺礼物"],
                "SEA-SCRATCH-041": ["加厚耐抓", "猫薄荷", "宠物玩具"],
            }
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
                    product_tags.get(sku, ["品质精选", "现货速发"]),
                    Decimal(price),
                    product_status,
                )
                products_with_stock.append((product, stock))

            category_image_names = [
                "digital",
                "home",
                "sport",
                "food",
                "books",
                "care",
                "fashion",
                "appliance",
                "baby",
                "pet",
            ]
            for index, (product, _) in enumerate(products_with_stock):
                category_index = product_specs[index][1]
                ensure_product_image(
                    session,
                    product,
                    f"/images/products/{category_image_names[category_index]}.webp",
                )

            variant_specs = {
                "NEB-KB-001": [
                    (
                        "CORAL",
                        "珊瑚橙轴",
                        {"颜色": "暖白珊瑚", "轴体": "线性轴"},
                        Decimal("399.00"),
                    ),
                    (
                        "CREAM",
                        "奶油白茶轴",
                        {"颜色": "奶油白", "轴体": "段落轴"},
                        Decimal("419.00"),
                    ),
                ],
                "NEB-MS-002": [
                    ("WHITE", "云朵白", {"颜色": "云朵白"}, Decimal("129.00")),
                    ("PINK", "柔雾粉", {"颜色": "柔雾粉"}, Decimal("139.00")),
                ],
                "NEB-SSD-005": [
                    ("1TB", "1TB 标准版", {"容量": "1TB"}, Decimal("599.00")),
                    ("2TB", "2TB 大容量版", {"容量": "2TB"}, Decimal("999.00")),
                ],
                "NEB-MONITOR-019": [
                    (
                        "27-4K",
                        "27 英寸 4K",
                        {"尺寸": "27 英寸", "分辨率": "4K"},
                        Decimal("1699.00"),
                    ),
                    (
                        "32-4K",
                        "32 英寸 4K",
                        {"尺寸": "32 英寸", "分辨率": "4K"},
                        Decimal("2199.00"),
                    ),
                ],
                "SEA-CUP-001": [
                    (
                        "CREAM",
                        "奶油白 500ml",
                        {"颜色": "奶油白", "容量": "500ml"},
                        Decimal("159.00"),
                    ),
                    (
                        "CORAL",
                        "珊瑚橙 500ml",
                        {"颜色": "珊瑚橙", "容量": "500ml"},
                        Decimal("159.00"),
                    ),
                ],
                "SEA-PILLOW-002": [
                    ("LOW", "低枕 8cm", {"高度": "8cm"}, Decimal("209.00")),
                    ("HIGH", "高枕 11cm", {"高度": "11cm"}, Decimal("219.00")),
                ],
                "SEA-BAG-003": [
                    ("GREEN", "苔藓绿 28L", {"颜色": "苔藓绿", "容量": "28L"}, Decimal("359.00")),
                    ("BLACK", "曜石黑 28L", {"颜色": "曜石黑", "容量": "28L"}, Decimal("359.00")),
                ],
                "SEA-COFFEE-005": [
                    ("NUT", "坚果风味", {"风味": "坚果可可"}, Decimal("68.00")),
                    ("FRUIT", "花果风味", {"风味": "柑橘花香"}, Decimal("72.00")),
                ],
                "SEA-MASK-021": [
                    ("10", "10 片体验装", {"数量": "10 片"}, Decimal("39.00")),
                    ("20", "20 片家庭装", {"数量": "20 片"}, Decimal("69.00")),
                ],
                "SEA-TSHIRT-024": [
                    ("M", "暖白 M 码", {"颜色": "暖白", "尺码": "M"}, Decimal("79.00")),
                    ("L", "暖白 L 码", {"颜色": "暖白", "尺码": "L"}, Decimal("79.00")),
                    ("XL", "珊瑚橙 XL 码", {"颜色": "珊瑚橙", "尺码": "XL"}, Decimal("85.00")),
                ],
                "SEA-SHOES-026": [
                    ("39", "米白 39 码", {"颜色": "米白", "尺码": "39"}, Decimal("269.00")),
                    ("41", "米白 41 码", {"颜色": "米白", "尺码": "41"}, Decimal("269.00")),
                    ("43", "珊瑚橙 43 码", {"颜色": "珊瑚橙", "尺码": "43"}, Decimal("279.00")),
                ],
                "SEA-CATLIT-029": [
                    ("5KG", "5kg 轻量装", {"重量": "5kg"}, Decimal("29.00")),
                    ("10KG", "10kg 实惠装", {"重量": "10kg"}, Decimal("49.00")),
                ],
            }
            for product, _ in products_with_stock:
                if product.sku in variant_specs:
                    ensure_product_variants(session, product, variant_specs[product.sku])

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
                        after_data={"products": len(product_specs), "orders": 8},
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
