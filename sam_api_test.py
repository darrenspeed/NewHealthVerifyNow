import requests
import json
import os
import sys
import time
from datetime import datetime

# Backend URL from frontend .env
BACKEND_URL = "https://5604b1c7-af2d-4c2d-865a-51fe8d939149.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"
SAM_API_KEY = "l43DgBt7jj7fuKwpOI90jKMX8MsXSgrTKMPgfqI2"

class SAMAPITester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.employee_id = None
        self.test_results = {
            "backend_health": False,
            "sam_api_key_valid": False,
            "sam_api_direct_access": False,
            "sam_integration_working": False,
            "employee_verification_with_sam": False
        }
        
    def test_backend_health(self):
        """Test if the backend API is accessible"""
        print("\n=== Testing Backend API Health ===")
        
        try:
            response = requests.get(f"{API_URL}/")
            
            if response.status_code == 200:
                print("✅ Backend API is accessible")
                self.test_results["backend_health"] = True
                return True
            else:
                print(f"❌ Backend API returned status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error accessing backend API: {str(e)}")
            return False
    
    def test_sam_api_key_valid(self):
        """Test if the SAM API key is valid with v4 API"""
        print("\n=== Testing SAM API Key Validity with v4 API ===")
        
        try:
            # Test the SAM API key directly with SAM.gov API v4
            headers = {
                "Accept": "application/json"
            }
            
            # Use the SAM.gov API v4 exclusions endpoint
            url = "https://api.sam.gov/exclusions/v4"
            params = {
                "api_key": SAM_API_KEY,
                "recordStatus": "Active",
                "limit": 1  # Just get one record to verify key works
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                print("✅ SAM API key is valid for v4 API")
                self.test_results["sam_api_key_valid"] = True
                return True
            elif response.status_code == 401 or response.status_code == 403:
                print(f"❌ SAM API key is invalid or expired for v4 API: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
            else:
                print(f"❌ SAM API v4 returned unexpected status code: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing SAM API v4 key: {str(e)}")
            return False
    
    def test_sam_api_direct_access(self):
        """Test direct access to SAM API v4 with a sample query"""
        print("\n=== Testing Direct SAM API v4 Access ===")
        
        try:
            # Test the SAM API v4 with a sample query
            headers = {
                "Accept": "application/json"
            }
            
            # Use the SAM.gov API v4 exclusions endpoint with a sample name
            url = "https://api.sam.gov/exclusions/v4"
            params = {
                "api_key": SAM_API_KEY,
                "exclusionName": "John Smith",
                "recordStatus": "Active"
            }
            
            print(f"Calling SAM.gov API v4 endpoint: {url}")
            print(f"Parameters: exclusionName={params['exclusionName']}, recordStatus={params['recordStatus']}")
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                total_records = data.get('totalRecords', 0)
                exclusion_details = data.get('exclusionDetails', [])
                
                print(f"✅ Successfully queried SAM API v4")
                print(f"  Query: exclusionName={params['exclusionName']}")
                print(f"  Total records found: {total_records}")
                print(f"  Exclusion details count: {len(exclusion_details)}")
                
                # Check the response format to ensure it matches what the code expects
                if 'totalRecords' in data and 'exclusionDetails' in data:
                    print("✅ SAM API v4 response format matches expected structure")
                    print("\nSample response structure:")
                    print(json.dumps(data, indent=2)[:1000] + "...\n" if len(json.dumps(data)) > 1000 else json.dumps(data, indent=2))
                    self.test_results["sam_api_direct_access"] = True
                    return True, data
                else:
                    print("❌ SAM API v4 response format does not match expected structure")
                    print(f"Expected keys: 'totalRecords', 'exclusionDetails'")
                    print(f"Actual keys: {', '.join(data.keys())}")
                    return False, data
            else:
                print(f"❌ SAM API v4 query failed: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error querying SAM API v4: {str(e)}")
            return False, {}
    
    def login(self):
        """Login to get authentication token"""
        print("\n=== Logging in to Health Verify Now ===")
        
        try:
            # Use default test credentials
            email = "test@example.com"
            password = "TestPassword123!"
            
            login_data = {
                "email": email,
                "password": password
            }
            
            response = requests.post(f"{API_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                self.user_id = data.get('user_id')
                
                print(f"✅ Login successful: {email}")
                return True
            else:
                print(f"❌ Login failed: HTTP {response.status_code}")
                
                # Try registration if login fails
                print("Attempting to register a new test user...")
                
                # Generate a random email
                timestamp = int(time.time())
                email = f"test_{timestamp}@example.com"
                
                register_data = {
                    "email": email,
                    "password": password,
                    "first_name": "Test",
                    "last_name": "User",
                    "company_name": "Test Company"
                }
                
                reg_response = requests.post(f"{API_URL}/auth/register", json=register_data)
                
                if reg_response.status_code == 201:
                    print(f"✅ Registration successful: {email}")
                    
                    # Now try login again
                    login_response = requests.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
                    
                    if login_response.status_code == 200:
                        login_data = login_response.json()
                        self.token = login_data.get('token')
                        self.user_id = login_data.get('user_id')
                        
                        print(f"✅ Login successful after registration: {email}")
                        return True
                    else:
                        print(f"❌ Login failed after registration: HTTP {login_response.status_code}")
                        return False
                else:
                    print(f"❌ Registration failed: HTTP {reg_response.status_code}")
                    return False
                
        except Exception as e:
            print(f"❌ Error during login: {str(e)}")
            return False
    
    def create_test_employee(self):
        """Create a test employee for verification"""
        print("\n=== Creating Test Employee ===")
        
        if not self.token:
            print("❌ Cannot create employee: No authentication token")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Create a subscription first if needed
            subscription_response = requests.get(f"{API_URL}/subscriptions/current", headers=headers)
            
            if subscription_response.status_code != 200 or not subscription_response.json().get('id'):
                print("No active subscription found, creating one...")
                
                # Get pricing tiers
                pricing_response = requests.get(f"{API_URL}/pricing")
                pricing_tiers = pricing_response.json().get('pricing_tiers', [])
                
                if pricing_tiers:
                    # Select the first tier
                    tier_id = pricing_tiers[0].get('id')
                    
                    subscription_data = {
                        "tier_id": tier_id,
                        "employee_count": 5,
                        "payment_method": "paypal"
                    }
                    
                    sub_create_response = requests.post(
                        f"{API_URL}/subscriptions", 
                        json=subscription_data, 
                        headers=headers
                    )
                    
                    if sub_create_response.status_code == 201:
                        print("✅ Created test subscription")
                    else:
                        print(f"❌ Failed to create subscription: HTTP {sub_create_response.status_code}")
                        # Continue anyway, as some test environments might not require subscription
            
            # Now create the employee
            employee_data = {
                "first_name": "John",
                "last_name": "Smith",
                "middle_name": "M",
                "ssn": "123-45-6789",
                "date_of_birth": "1980-01-01",
                "email": "john.smith@example.com",
                "license_number": "MD12345",
                "license_type": "MD",
                "license_state": "CA"
            }
            
            response = requests.post(f"{API_URL}/employees", json=employee_data, headers=headers)
            
            if response.status_code == 201:
                data = response.json()
                self.employee_id = data.get('id')
                
                print(f"✅ Created test employee: {employee_data['first_name']} {employee_data['last_name']}")
                print(f"  Employee ID: {self.employee_id}")
                return True
            else:
                print(f"❌ Failed to create employee: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating test employee: {str(e)}")
            return False
    
    def test_sam_integration(self):
        """Test the SAM integration in the backend"""
        print("\n=== Testing SAM Integration ===")
        
        try:
            # Check if the backend has a verification-system-status endpoint
            response = requests.get(f"{API_URL}/verification-system-status")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check SAM database status
                federal_exclusions = data.get('federal_exclusions', {})
                sam_db = federal_exclusions.get('sam_database', {})
                
                sam_loaded = sam_db.get('loaded', False)
                sam_count = sam_db.get('exclusions_count', 0)
                sam_status = sam_db.get('status', 'Unknown')
                
                print(f"SAM Database Status:")
                print(f"  Loaded: {sam_loaded}")
                print(f"  Exclusions Count: {sam_count}")
                print(f"  Status: {sam_status}")
                
                if sam_loaded and sam_count > 0 and sam_status == "Active":
                    print("✅ SAM integration is working properly")
                    self.test_results["sam_integration_working"] = True
                    return True
                else:
                    print("❌ SAM integration is not working properly")
                    if not sam_loaded:
                        print("  - SAM database is not loaded")
                    if sam_count == 0:
                        print("  - No exclusions found in SAM database")
                    if sam_status != "Active":
                        print(f"  - SAM database status is {sam_status}, expected 'Active'")
                    return False
            else:
                print(f"❌ Failed to check verification system status: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing SAM integration: {str(e)}")
            return False
    
    def test_employee_verification_with_sam(self):
        """Test employee verification with SAM"""
        print("\n=== Testing Employee Verification with SAM ===")
        
        if not self.token or not self.employee_id:
            print("❌ Cannot test verification: No authentication token or employee ID")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Verify employee with SAM only
            verification_types = ['sam']
            
            response = requests.post(
                f"{API_URL}/employees/{self.employee_id}/verify", 
                json=verification_types, 
                headers=headers
            )
            
            if response.status_code == 202:
                print("✅ SAM verification initiated successfully")
                
                # Wait for verification to complete
                print("  Waiting for verification to complete...")
                time.sleep(3)
                
                # Check verification results
                results_response = requests.get(
                    f"{API_URL}/verification-results?employee_id={self.employee_id}", 
                    headers=headers
                )
                
                if results_response.status_code == 200:
                    results = results_response.json()
                    
                    # Filter for SAM results only
                    sam_results = [r for r in results if r.get('verification_type') == 'sam']
                    
                    if sam_results:
                        sam_result = sam_results[0]
                        status = sam_result.get('status')
                        
                        print(f"  SAM verification status: {status}")
                        
                        if status in ['passed', 'failed']:
                            print("✅ SAM verification completed successfully")
                            
                            # Check result details
                            results_data = sam_result.get('results', {})
                            database_info = results_data.get('database_info', {})
                            
                            print(f"  Database info:")
                            print(f"    Total exclusions: {database_info.get('total_exclusions_in_database', 0)}")
                            print(f"    Source: {database_info.get('source', 'Unknown')}")
                            print(f"    Method: {database_info.get('verification_method', 'Unknown')}")
                            
                            self.test_results["employee_verification_with_sam"] = True
                            return True
                        elif status == 'error':
                            error_message = sam_result.get('error_message', 'Unknown error')
                            print(f"❌ SAM verification failed with error: {error_message}")
                            return False
                        else:
                            print(f"❌ Unexpected SAM verification status: {status}")
                            return False
                    else:
                        print("❌ No SAM verification results found")
                        return False
                else:
                    print(f"❌ Failed to retrieve verification results: HTTP {results_response.status_code}")
                    print(f"Response: {results_response.text[:500]}")
                    return False
            else:
                print(f"❌ Failed to initiate SAM verification: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing SAM verification: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all SAM API tests"""
        print("=== Starting SAM API Integration Tests ===")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"SAM API Key: {SAM_API_KEY[:5]}...{SAM_API_KEY[-5:]}")
        
        # Test backend health
        self.test_backend_health()
        
        # Test SAM API key validity
        self.test_sam_api_key_valid()
        
        # Test direct SAM API access
        self.test_sam_api_direct_access()
        
        # Test SAM integration in backend
        self.test_sam_integration()
        
        # Login and create test employee for verification
        if self.login():
            if self.create_test_employee():
                # Test employee verification with SAM
                self.test_employee_verification_with_sam()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print a summary of test results"""
        print("\n=== SAM API Integration Test Summary ===")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name.replace('_', ' ').title()}")
        
        print("\nConclusion:")
        if self.test_results["sam_api_key_valid"] and self.test_results["sam_api_direct_access"]:
            print("✅ SAM API key is valid and direct API access is working")
        else:
            print("❌ Issues with SAM API key or direct API access")
        
        if self.test_results["sam_integration_working"] and self.test_results["employee_verification_with_sam"]:
            print("✅ SAM integration in the backend is working properly")
        else:
            print("❌ Issues with SAM integration in the backend")
        
        if passed_tests >= total_tests * 0.8:  # 80% pass threshold
            print("\nOverall: SAM API integration is working correctly")
        else:
            print("\nOverall: SAM API integration has issues that need to be addressed")

def main():
    tester = SAMAPITester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()