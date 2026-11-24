from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, noload, selectinload

from database import Base, SessionLocal, engine, get_db
from models import Account, AccountType, Category, Product
from schemas import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    AccountWithProductsOut,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    PaginatedProducts,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from seed import seed_products


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_products(db)
    yield


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")


@app.get("/")
def read_root():
    return {"Hello": "World"}


@api_router.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


# --- Category Routes ---


@api_router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.id)).all()


@api_router.get("/categories/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@api_router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Category).where(Category.name == payload.name))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")
    category = Category(name=payload.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@api_router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if payload.name is not None:
        category.name = payload.name
    db.commit()
    db.refresh(category)
    return category


@api_router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    db.delete(category)
    db.commit()


# --- Product Routes ---


@api_router.get(
    "/products",
    response_model=PaginatedProducts,
    response_model_exclude_none=True,
)
def list_products(
    search: str | None = Query(default=None, description="Filter products by name"),
    include: str | None = Query(default=None, description="Relations to include, e.g. 'category'"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    includes = {part.strip().lower() for part in include.split(",")} if include else set()
    load_option = selectinload(Product.category) if "category" in includes else noload(Product.category)

    stmt = select(Product).options(load_option)
    count_stmt = select(func.count(Product.id))

    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(Product.name.ilike(pattern))
        count_stmt = count_stmt.where(Product.name.ilike(pattern))

    total = db.scalar(count_stmt) or 0
    offset = (page - 1) * page_size
    items = db.scalars(stmt.order_by(Product.id).offset(offset).limit(page_size)).all()

    return PaginatedProducts(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@api_router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    stmt = select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
    product = db.scalar(stmt)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@api_router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    if not db.get(Category, payload.category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    product = Product(
        name=payload.name,
        qty=payload.qty,
        price=payload.price,
        category_id=payload.category_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@api_router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)
    if "category_id" in updates and not db.get(Category, updates["category_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for field, value in updates.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@api_router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    db.delete(product)
    db.commit()


# --- Account Routes (Many-to-Many with Products & Enum filtering) ---


@api_router.get("/accounts", response_model=list[AccountOut])
def list_accounts(
    type: AccountType | None = Query(default=None, description="Filter by VENDOR or SUPPLIER"),
    db: Session = Depends(get_db),
):
    stmt = select(Account).order_by(Account.id)
    if type is not None:
        stmt = stmt.where(Account.type == type)
    return db.scalars(stmt).all()


@api_router.get("/accounts/{account_id}", response_model=AccountWithProductsOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(Account)
        .options(selectinload(Account.products).selectinload(Product.category))
        .where(Account.id == account_id)
    )
    account = db.scalar(stmt)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


@api_router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Account).where(Account.name == payload.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    account = Account(name=payload.name, type=payload.type)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@api_router.patch("/accounts/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@api_router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    db.delete(account)
    db.commit()


@api_router.post("/accounts/{account_id}/products/{product_id}", response_model=AccountWithProductsOut)
def assign_product_to_account(account_id: int, product_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(Account)
        .options(selectinload(Account.products).selectinload(Product.category))
        .where(Account.id == account_id)
    )
    account = db.scalar(stmt)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product not in account.products:
        account.products.append(product)
        db.commit()
        db.refresh(account)
    return account


@api_router.delete("/accounts/{account_id}/products/{product_id}", response_model=AccountWithProductsOut)
def unassign_product_from_account(account_id: int, product_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(Account)
        .options(selectinload(Account.products).selectinload(Product.category))
        .where(Account.id == account_id)
    )
    account = db.scalar(stmt)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product in account.products:
        account.products.remove(product)
        db.commit()
        db.refresh(account)
    return account


app.include_router(api_router)
