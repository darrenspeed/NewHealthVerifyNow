import httpx
import os
import json
import base64
from typing import Dict, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PayPalClient:
    def __init__(self):
        self.client_id = os.environ.get("PAYPAL_CLIENT_ID")
        self.client_secret = os.environ.get("PAYPAL_CLIENT_SECRET")
        # PRODUCTION URLs for live payments
        self.base_url = "https://api-m.paypal.com"  # LIVE PRODUCTION
        # self.base_url = "https://api-m.sandbox.paypal.com"  # Sandbox for testing
        self.access_token = None
        self.token_expires_at = None

    async def get_access_token(self) -> str:
        """Get PayPal access token"""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token

        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {auth_b64}'
        }

        data = "grant_type=client_credentials"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                headers=headers,
                content=data
            )

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                return self.access_token
            else:
                logger.error(f"Failed to get PayPal access token: {response.text}")
                raise Exception("Failed to authenticate with PayPal")

    async def create_product(self, name: str, description: str) -> str:
        """Create a PayPal product for subscriptions"""
        access_token = await self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'PayPal-Request-Id': f'PRODUCT-{datetime.utcnow().timestamp()}'
        }

        product_data = {
            "name": name,
            "description": description,
            "type": "SERVICE",
            "category": "SOFTWARE"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/catalogs/products",
                headers=headers,
                json=product_data
            )

            if response.status_code == 201:
                return response.json()['id']
            else:
                logger.error(f"Failed to create PayPal product: {response.text}")
                raise Exception("Failed to create PayPal product")

    async def create_subscription_plan(self, product_id: str, plan_name: str, price_per_employee: float) -> str:
        """Create a PayPal subscription plan"""
        access_token = await self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'PayPal-Request-Id': f'PLAN-{datetime.utcnow().timestamp()}'
        }

        plan_data = {
            "product_id": product_id,
            "name": f"Health Verify Now - {plan_name}",
            "description": f"Monthly subscription for healthcare compliance verification - {plan_name} plan",
            "status": "ACTIVE",
            "billing_cycles": [
                {
                    "frequency": {
                        "interval_unit": "MONTH",
                        "interval_count": 1
                    },
                    "tenure_type": "REGULAR",
                    "sequence": 1,
                    "total_cycles": 0,  # Infinite
                    "pricing_scheme": {
                        "fixed_price": {
                            "value": str(price_per_employee),
                            "currency_code": "USD"
                        }
                    }
                }
            ],
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee": {
                    "value": "0",
                    "currency_code": "USD"
                },
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/billing/plans",
                headers=headers,
                json=plan_data
            )

            if response.status_code == 201:
                return response.json()['id']
            else:
                logger.error(f"Failed to create PayPal subscription plan: {response.text}")
                raise Exception("Failed to create PayPal subscription plan")

    async def create_subscription(self, plan_id: str, employee_count: int, monthly_cost: float, user_email: str) -> Dict:
        """Create a PayPal subscription"""
        access_token = await self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'PayPal-Request-Id': f'SUB-{datetime.utcnow().timestamp()}'
        }

        subscription_data = {
            "plan_id": plan_id,
            "start_time": (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z",
            "quantity": str(employee_count),
            "shipping_amount": {
                "currency_code": "USD",
                "value": "0.00"
            },
            "subscriber": {
                "email_address": user_email
            },
            "application_context": {
                "brand_name": "Health Verify Now",
                "locale": "en-US",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "SUBSCRIBE_NOW",
                "payment_method": {
                    "payer_selected": "PAYPAL",
                    "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED"
                },
                "return_url": "https://your-domain.com/subscription/success",
                "cancel_url": "https://your-domain.com/subscription/cancel"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/billing/subscriptions",
                headers=headers,
                json=subscription_data
            )

            if response.status_code == 201:
                subscription = response.json()
                # Find approval URL
                approval_url = None
                for link in subscription.get('links', []):
                    if link.get('rel') == 'approve':
                        approval_url = link.get('href')
                        break
                
                return {
                    'subscription_id': subscription['id'],
                    'approval_url': approval_url,
                    'status': subscription.get('status')
                }
            else:
                logger.error(f"Failed to create PayPal subscription: {response.text}")
                raise Exception("Failed to create PayPal subscription")

    async def get_subscription(self, subscription_id: str) -> Dict:
        """Get PayPal subscription details"""
        access_token = await self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/billing/subscriptions/{subscription_id}",
                headers=headers
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get PayPal subscription: {response.text}")
                return {}

    async def cancel_subscription(self, subscription_id: str, reason: str = "Customer requested cancellation") -> bool:
        """Cancel a PayPal subscription"""
        access_token = await self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        cancel_data = {
            "reason": reason
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/billing/subscriptions/{subscription_id}/cancel",
                headers=headers,
                json=cancel_data
            )

            return response.status_code == 204

    async def update_subscription_quantity(self, subscription_id: str, new_employee_count: int) -> bool:
        """Update subscription quantity (employee count)"""
        access_token = await self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        update_data = {
            "quantity": str(new_employee_count)
        }

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/v1/billing/subscriptions/{subscription_id}",
                headers=headers,
                json=update_data
            )

            return response.status_code == 200

# Global PayPal client instance
paypal_client = PayPalClient()
