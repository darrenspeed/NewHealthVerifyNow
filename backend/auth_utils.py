from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from typing import Optional

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "default-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None

# Subscription pricing logic
PRICING_TIERS = [
    {
        "name": "Starter",
        "min_employees": 1,
        "max_employees": 25,
        "price_per_employee": 1.95
    },
    {
        "name": "Professional", 
        "min_employees": 26,
        "max_employees": 100,
        "price_per_employee": 1.75
    },
    {
        "name": "Enterprise",
        "min_employees": 101,
        "max_employees": 500,
        "price_per_employee": 1.25
    },
    {
        "name": "Enterprise+",
        "min_employees": 501,
        "max_employees": None,
        "price_per_employee": 1.00
    }
]

def calculate_monthly_cost(employee_count: int) -> tuple[str, float]:
    """Calculate monthly cost and plan name based on employee count"""
    for tier in PRICING_TIERS:
        if employee_count >= tier["min_employees"]:
            if tier["max_employees"] is None or employee_count <= tier["max_employees"]:
                plan_name = tier["name"]
                monthly_cost = employee_count * tier["price_per_employee"]
                return plan_name, monthly_cost
    
    # Default to starter plan
    return "Starter", employee_count * 4.95

def get_pricing_tiers():
    """Get pricing tiers for Health Verify Now - Complete Credentialing Platform"""
    return [
        {
            "name": "Basic Exclusions",
            "description": "Federal exclusion checks only (OIG + SAM)",
            "price_per_employee": 29,
            "min_employees": 1,
            "max_employees": 50,
            "features": [
                "OIG Exclusion Verification",
                "SAM Exclusion Verification", 
                "Basic Reporting",
                "Email Support"
            ],
            "verification_types": ["oig", "sam"],
            "recommended": False
        },
        {
            "name": "Professional Credentialing", 
            "description": "Exclusions + License Verification",
            "price_per_employee": 89,
            "min_employees": 1,
            "max_employees": 100,
            "features": [
                "All Basic Exclusions",
                "NPI Registry Verification",
                "State Medical License Verification",
                "State Nursing License Verification", 
                "Professional Reporting",
                "Priority Email Support"
            ],
            "verification_types": ["oig", "sam", "npi", "license_md_ca", "license_rn_ca"],
            "recommended": True,
            "badge": "Most Popular"
        },
        {
            "name": "Complete Background Check",
            "description": "Exclusions + Licenses + Criminal Background",
            "price_per_employee": 149,
            "min_employees": 1,
            "max_employees": 200,
            "features": [
                "All Professional Credentialing",
                "National Sex Offender Registry",
                "FBI Most Wanted Database",
                "State Criminal Records",
                "Comprehensive Reporting",
                "Phone & Email Support"
            ],
            "verification_types": ["oig", "sam", "npi", "license_md_ca", "license_rn_ca", "nsopw_national", "fbi_wanted"],
            "recommended": False
        },
        {
            "name": "Enterprise Credentialing",
            "description": "Complete credentialing + State Medicaid + HIPAA",
            "price_per_employee": 249,
            "min_employees": 51,
            "max_employees": 1000,
            "features": [
                "All Complete Background Check",
                "State Medicaid Exclusion Checks",
                "Multi-State License Verification",
                "HIPAA-Compliant Reporting",
                "Audit Trail & Compliance",
                "Dedicated Account Manager",
                "API Access",
                "Custom Integrations"
            ],
            "verification_types": ["oig", "sam", "npi", "license_md_ca", "license_md_tx", "license_rn_ca", "license_rn_tx", "nsopw_national", "fbi_wanted", "medicaid_ca", "medicaid_tx"],
            "recommended": False,
            "badge": "Enterprise"
        },
        {
            "name": "Healthcare System",
            "description": "Complete platform for large healthcare organizations",
            "price_per_employee": 399,
            "min_employees": 201,
            "max_employees": None,
            "features": [
                "All Enterprise Features",
                "All State License Verifications",
                "All State Medicaid Checks", 
                "Real-time API Access",
                "Custom Reporting Dashboard",
                "White-label Options",
                "24/7 Priority Support",
                "On-site Training",
                "Custom Compliance Reporting"
            ],
            "verification_types": "all",
            "recommended": False,
            "badge": "Complete Solution"
        }
    ]
