from pydantic import BaseModel, Field, EmailStr
from typing import Optional
import uuid
from datetime import datetime

# User Authentication Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    company_name: str
    first_name: str
    last_name: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    company_name: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # Payment info
    paypal_subscription_id: Optional[str] = None
    current_plan: Optional[str] = None
    employee_count: int = 0
    monthly_cost: float = 0.0
    next_billing_date: Optional[datetime] = None

class UserResponse(BaseModel):
    id: str
    email: str
    company_name: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    # Payment info
    current_plan: Optional[str] = None
    employee_count: int = 0
    monthly_cost: float = 0.0
    next_billing_date: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Subscription Models
class SubscriptionPlan(BaseModel):
    plan_id: str
    name: str
    price_per_employee: float
    min_employees: int
    max_employees: Optional[int] = None
    features: list[str]

class SubscriptionCreate(BaseModel):
    employee_count: int

class SubscriptionUpdate(BaseModel):
    employee_count: int

class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    paypal_subscription_id: str
    plan_name: str
    employee_count: int
    monthly_cost: float
    status: str  # active, cancelled, past_due, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    next_billing_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None

# Payment Models
class PayPalCreateOrder(BaseModel):
    employee_count: int

class PayPalOrderResponse(BaseModel):
    order_id: str
    approval_url: str

class PayPalCaptureOrder(BaseModel):
    order_id: str
