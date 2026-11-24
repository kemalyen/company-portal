from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import Account, AccountType, Category, Product

SAMPLE_CATEGORIES = [
    "Peripherals",
    "Monitors & Stands",
    "Audio",
    "Storage & Cables",
    "Accessories",
]

# (name, qty, price, category_name)
SAMPLE_PRODUCTS = [
    ("Wireless Mouse", 45, 24.99, "Peripherals"),
    ("Mechanical Keyboard", 30, 89.99, "Peripherals"),
    ("USB-C Hub", 60, 34.50, "Storage & Cables"),
    ("27-inch 4K Monitor", 12, 349.00, "Monitors & Stands"),
    ("Laptop Stand", 50, 29.99, "Monitors & Stands"),
    ("Noise-Canceling Headphones", 18, 199.99, "Audio"),
    ("Webcam 1080p", 25, 59.99, "Peripherals"),
    ("Desk Lamp LED", 40, 32.00, "Accessories"),
    ("Ergonomic Chair", 8, 279.00, "Accessories"),
    ("HDMI 2.1 Cable", 100, 14.99, "Storage & Cables"),
    ("External SSD 1TB", 22, 109.99, "Storage & Cables"),
    ("Portable Power Bank", 55, 39.99, "Accessories"),
    ("Bluetooth Speaker", 33, 49.50, "Audio"),
    ("Gaming Mousepad XL", 70, 19.99, "Accessories"),
    ("USB-C Charging Cable", 120, 11.99, "Storage & Cables"),
    ("Microphone Condenser", 15, 79.99, "Audio"),
    ("Monitor Arm Mount", 20, 64.99, "Monitors & Stands"),
    ("Laptop Sleeve 15-inch", 42, 22.99, "Accessories"),
    ("Smart Plug Wi-Fi", 65, 16.99, "Accessories"),
    ("Ethernet Cable Cat6 5m", 90, 9.99, "Storage & Cables"),
    ("Wireless Charger Pad", 48, 25.00, "Accessories"),
    ("Mechanical Keycap Set", 27, 35.99, "Peripherals"),
    ("Screen Cleaning Kit", 80, 12.50, "Accessories"),
    ("Card Reader SD/MicroSD", 52, 15.99, "Storage & Cables"),
    ("Surge Protector 6-Outlet", 36, 27.99, "Accessories"),
    ("Graphics Drawing Tablet", 14, 74.99, "Peripherals"),
    ("Portable Laptop Desk", 19, 44.99, "Monitors & Stands"),
    ("Noise Isolating Earbuds", 60, 29.00, "Audio"),
    ("DisplayPort to HDMI Adapter", 75, 13.99, "Storage & Cables"),
    ("Smart LED Light Strip", 44, 24.50, "Accessories"),
    ("Desk Cable Organizer", 95, 14.00, "Accessories"),
    ("Vertical Ergonomic Mouse", 28, 38.99, "Peripherals"),
    ("USB Flash Drive 128GB", 85, 17.99, "Storage & Cables"),
    ("Mini Tripod Stand", 38, 21.50, "Monitors & Stands"),
    ("Bluetooth Keyboard Compact", 26, 54.99, "Peripherals"),
    ("Laptop Cooling Pad", 31, 28.99, "Accessories"),
    ("Webcam Privacy Cover 3-Pack", 150, 6.99, "Accessories"),
    ("Acoustic Foam Panels 12-Pack", 24, 39.00, "Audio"),
    ("USB-C to Ethernet Adapter", 47, 19.50, "Storage & Cables"),
    ("Dual Monitor Stand", 11, 94.99, "Monitors & Stands"),
    ("Wrist Rest Memory Foam", 58, 16.50, "Accessories"),
    ("Smart Desk Clock", 29, 31.99, "Accessories"),
    ("Ring Light 10-inch", 21, 36.00, "Accessories"),
    ("Thunderbolt 4 Cable", 34, 29.99, "Storage & Cables"),
    ("Headphone Stand Aluminum", 41, 23.99, "Audio"),
]


def seed_products(db: Session) -> int:
    existing_count = db.scalar(select(func.count(Product.id))) or 0
    if existing_count > 0:
        return 0

    categories_by_name: dict[str, Category] = {}
    for cat_name in SAMPLE_CATEGORIES:
        cat = db.scalar(select(Category).where(Category.name == cat_name))
        if not cat:
            cat = Category(name=cat_name)
            db.add(cat)
            db.flush()
        categories_by_name[cat_name] = cat

    products = [
        Product(
            name=name,
            qty=qty,
            price=price,
            category_id=categories_by_name[cat_name].id,
        )
        for name, qty, price, cat_name in SAMPLE_PRODUCTS
    ]
    db.add_all(products)
    db.commit()

    if (db.scalar(select(func.count(Account.id))) or 0) == 0:
        tech_supply = Account(name="TechSupply Co.", type=AccountType.SUPPLIER)
        global_parts = Account(name="Global Parts Ltd.", type=AccountType.SUPPLIER)
        city_retail = Account(name="City Electronics", type=AccountType.VENDOR)
        online_mart = Account(name="OnlineMart", type=AccountType.VENDOR)

        tech_supply.products.extend(products[:5])
        global_parts.products.extend(products[3:8])
        city_retail.products.extend(products[:3])
        online_mart.products.extend(products[5:10])

        db.add_all([tech_supply, global_parts, city_retail, online_mart])
        db.commit()

    return len(products)


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        inserted = seed_products(session)
        print(f"Seeded {inserted} products.")
