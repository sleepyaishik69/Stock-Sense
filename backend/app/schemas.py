from datetime import date
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    workspace_name: str = Field(min_length=2, max_length=160)
    store_name: str = Field(min_length=2, max_length=160)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=240)
    category: str = "Uncategorized"
    unit_price: Decimal = Field(ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    stock_on_hand: int | None = Field(default=None, ge=0)
    reorder_threshold: int = Field(default=5, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0)


class ProductPatch(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=240)
    category: str | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    stock_on_hand: int | None = Field(default=None, ge=0)
    reorder_threshold: int | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0)


class StoreIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class StockMovementIn(BaseModel):
    product_id: int = Field(gt=0)
    movement_type: str = Field(pattern="^(count|receive|damage|correction)$")
    quantity: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=500)


class InsightItem(BaseModel):
    title: str
    explanation: str
    supporting_metrics: list[str] = []
    recommended_action: str
    priority: str
    confidence: str
    assumptions: list[str] = []


class InsightResponse(BaseModel):
    summary: str
    insights: list[InsightItem] = []
    data_gaps: list[str] = []
    limitations: list[str] = []
