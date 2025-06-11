#!/usr/bin/env python3

import httpx
import base64
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

async def test_paypal_auth():
    client_id = os.environ.get("PAYPAL_CLIENT_ID")
    client_secret = os.environ.get("PAYPAL_CLIENT_SECRET")
    
    print(f"Testing PayPal Authentication...")
    print(f"Client ID: {client_id[:20]}... (truncated)")
    print(f"Client Secret: {client_secret[:20]}... (truncated)")
    
    # Create auth string
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_b64}'
    }
    
    data = "grant_type=client_credentials"
    
    # Test against PayPal Live API
    url = "https://api-m.paypal.com/v1/oauth2/token"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, content=data)
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                print("✅ PayPal Authentication SUCCESS!")
                return True
            else:
                print("❌ PayPal Authentication FAILED!")
                return False
                
        except Exception as e:
            print(f"❌ Request Error: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(test_paypal_auth())