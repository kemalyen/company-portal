from pydantic import BaseModel, ConfigDict, Field, computed_field

from models import AccountType


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    qty: int = Field(ge=0, default=0)
    price: float = Field(gt=0)
    category_id: int


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    qty: int | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, gt=0)
    category_id: int | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str = Field(validation_alias="name")
    qty: int
    price: float
    category: CategoryOut | None = None

    @computed_field
    @property
    def total_value(self) -> float:
        return round(self.qty * self.price, 2)


class PaginatedProducts(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: AccountType


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: AccountType | None = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: AccountType


class AccountWithProductsOut(AccountOut):
    products: list[ProductOut] = []


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class AdminUserCreate(UserCreate):
    is_active: bool = True
    roles: list[str] = []


class AdminUserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=120)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None
    roles: list[str] | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    role_names: set[str]
    permission_names: set[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
