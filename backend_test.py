import requests
import time
import json
from datetime import datetime

class HealthVerifyTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_employees = []
        self.auth_token = None
        self.user_data = None
        self.subscription_data = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, auth=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Add authorization header if needed and token is available
        if auth and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_api_root(self):
        """Test the API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "api",
            200
        )
        if success:
            print(f"API Version: {response.get('version')}")
            print(f"API Status: {response.get('status')}")
        return success
    
    # Authentication Tests
    def test_register(self, email, password, company_name, first_name, last_name):
        """Test user registration"""
        user_data = {
            "email": email,
            "password": password,
            "company_name": company_name,
            "first_name": first_name,
            "last_name": last_name
        }
        
        success, response = self.run_test(
            f"Register User: {email}",
            "POST",
            "api/auth/register",
            200,
            data=user_data
        )
        
        if success and response.get('access_token'):
            self.auth_token = response.get('access_token')
            self.user_data = response.get('user')
            print(f"Registered user with email: {email}")
            print(f"Auth token received: {self.auth_token[:10]}...")
        return success, response
    
    def test_login(self, email, password):
        """Test user login"""
        login_data = {
            "email": email,
            "password": password
        }
        
        success, response = self.run_test(
            f"Login User: {email}",
            "POST",
            "api/auth/login",
            200,
            data=login_data
        )
        
        if success and response.get('access_token'):
            self.auth_token = response.get('access_token')
            self.user_data = response.get('user')
            print(f"Logged in user with email: {email}")
            print(f"Auth token received: {self.auth_token[:10]}...")
        return success, response
    
    def test_get_current_user(self):
        """Test getting current user info"""
        success, response = self.run_test(
            "Get Current User Info",
            "GET",
            "api/auth/me",
            200,
            auth=True
        )
        
        if success:
            print(f"Retrieved user info: {response.get('email')}")
            print(f"Company: {response.get('company_name')}")
            if response.get('current_plan'):
                print(f"Current plan: {response.get('current_plan')}")
                print(f"Employee count: {response.get('employee_count')}")
                print(f"Monthly cost: ${response.get('monthly_cost')}")
        return success, response
    
    # Payment Tests
    def test_get_pricing(self):
        """Test getting pricing information"""
        success, response = self.run_test(
            "Get Pricing Information",
            "GET",
            "api/pricing",
            200
        )
        
        if success and response.get('pricing_tiers'):
            print(f"Retrieved {len(response.get('pricing_tiers'))} pricing tiers:")
            for tier in response.get('pricing_tiers'):
                print(f"  - {tier.get('name')}: ${tier.get('price_per_employee')}/employee/month")
                print(f"    Min: {tier.get('min_employees')} employees, Max: {tier.get('max_employees') or 'Unlimited'}")
        return success, response
    
    def test_create_subscription(self, employee_count):
        """Test creating a subscription"""
        subscription_data = {
            "employee_count": employee_count
        }
        
        success, response = self.run_test(
            f"Create Subscription for {employee_count} employees",
            "POST",
            "api/payment/create-subscription",
            200,
            data=subscription_data,
            auth=True
        )
        
        if success:
            self.subscription_data = response
            print(f"Created subscription with ID: {response.get('subscription_id')}")
            print(f"PayPal subscription ID: {response.get('paypal_subscription_id')}")
            print(f"Plan: {response.get('plan_name')}")
            print(f"Monthly cost: ${response.get('monthly_cost')}")
            print(f"Status: {response.get('status')}")
            print(f"Approval URL: {response.get('approval_url')}")
        return success, response
    
    def test_get_subscription(self):
        """Test getting current subscription"""
        success, response = self.run_test(
            "Get Current Subscription",
            "GET",
            "api/payment/subscription",
            200,
            auth=True
        )
        
        if success and response.get('subscription'):
            subscription = response.get('subscription')
            print(f"Retrieved subscription: {subscription.get('id')}")
            print(f"Plan: {subscription.get('plan_name')}")
            print(f"Employee count: {subscription.get('employee_count')}")
            print(f"Monthly cost: ${subscription.get('monthly_cost')}")
            print(f"Status: {subscription.get('status')}")
        return success, response
    
    def test_update_subscription(self, new_employee_count):
        """Test updating subscription employee count"""
        update_data = {
            "employee_count": new_employee_count
        }
        
        success, response = self.run_test(
            f"Update Subscription to {new_employee_count} employees",
            "PATCH",
            "api/payment/subscription",
            200,
            data=update_data,
            auth=True
        )
        
        if success:
            print(f"Updated subscription to {new_employee_count} employees")
            print(f"New plan: {response.get('plan_name')}")
            print(f"New monthly cost: ${response.get('monthly_cost')}")
        return success, response

    def test_create_employee(self, first_name, last_name, middle_name=None, should_pass=True):
        """Test creating an employee"""
        employee_data = {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "ssn": "123-45-6789",
            "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
            "date_of_birth": "1990-01-01",
            "license_number": "ABC123" if should_pass else None
        }
        
        success, response = self.run_test(
            f"Create Employee: {first_name} {middle_name or ''} {last_name}",
            "POST",
            "api/employees",
            200 if should_pass else 400,
            data=employee_data,
            auth=True
        )
        
        if success and should_pass:
            print(f"Created employee with ID: {response.get('id')}")
            self.created_employees.append(response)
            return response.get('id')
        return None

    def test_get_employees(self):
        """Test getting all employees"""
        success, response = self.run_test(
            "Get All Employees",
            "GET",
            "api/employees",
            200,
            auth=True
        )
        if success:
            print(f"Retrieved {len(response)} employees")
        return success

    def test_verify_employee(self, employee_id, verification_types):
        """Test verifying an employee"""
        success, response = self.run_test(
            f"Verify Employee: {employee_id} with {verification_types}",
            "POST",
            f"api/employees/{employee_id}/verify",
            200,
            data=verification_types,
            auth=True
        )
        if success:
            print(f"Verification results: {json.dumps(response, indent=2)}")
        return success, response

    def test_batch_verification(self, employee_ids, verification_types):
        """Test batch verification"""
        data = {
            "employee_ids": employee_ids,
            "verification_types": verification_types
        }
        
        success, response = self.run_test(
            "Batch Verification",
            "POST",
            "api/verify-batch",
            200,
            data=data,
            auth=True
        )
        if success:
            print(f"Batch verification started for {len(employee_ids)} employees")
        return success

    def test_get_verification_results(self):
        """Test getting verification results"""
        success, response = self.run_test(
            "Get Verification Results",
            "GET",
            "api/verification-results",
            200,
            auth=True
        )
        if success:
            print(f"Retrieved {len(response)} verification results")
        return success, response
    
    def test_get_employee_verification_results(self, employee_id):
        """Test getting verification results for a specific employee"""
        success, response = self.run_test(
            f"Get Verification Results for Employee {employee_id}",
            "GET",
            f"api/employees/{employee_id}/verification-results",
            200,
            auth=True
        )
        if success:
            print(f"Retrieved {len(response)} verification results for employee {employee_id}")
        return success, response

def test_sam_api_endpoint(tester):
    """Test the SAM API test endpoint with new bulk download integration"""
    print("\n=== Testing SAM API Test Endpoint ===")
    success, response = tester.run_test(
        "SAM API Test Endpoint",
        "GET",
        "api/test-sam",
        200
    )
    
    if success:
        print("\nSAM API Test Results:")
        
        # Check verification system status
        verification_status = response.get('verification_system_status', {})
        
        # Check OIG database status
        oig_db = verification_status.get('oig_database', {})
        print(f"\nOIG Database Status:")
        print(f"  Loaded: {oig_db.get('loaded', False)}")
        print(f"  Exclusions Count: {oig_db.get('exclusions_count', 0)}")
        print(f"  Source: {oig_db.get('source', 'Unknown')}")
        print(f"  Method: {oig_db.get('method', 'Unknown')}")
        
        # Check SAM database status
        sam_db = verification_status.get('sam_database', {})
        print(f"\nSAM Database Status:")
        print(f"  Loaded: {sam_db.get('loaded', False)}")
        print(f"  Exclusions Count: {sam_db.get('exclusions_count', 0)}")
        print(f"  Source: {sam_db.get('source', 'Unknown')}")
        print(f"  Method: {sam_db.get('method', 'Unknown')}")
        
        # Check SAM API info
        sam_api_info = response.get('sam_api_info', {})
        print(f"\nSAM API Information:")
        print(f"  API Key Configured: {sam_api_info.get('api_key_configured', False)}")
        print(f"  API Key Partial: {sam_api_info.get('api_key_partial', 'None')}")
        print(f"  Bulk Download Capability: {sam_api_info.get('bulk_download_capability', 'Unknown')}")
        print(f"  Real-time Search: {sam_api_info.get('real_time_search', 'Unknown')}")
        
        # Check system capabilities
        capabilities = response.get('system_capabilities', {})
        print(f"\nSystem Capabilities:")
        print(f"  OIG Verification: {capabilities.get('oig_verification', 'Unknown')}")
        print(f"  SAM Verification: {capabilities.get('sam_verification', 'Unknown')}")
        print(f"  Batch Verification: {capabilities.get('batch_verification', 'Unknown')}")
        
        # Check recommendations
        recommendations = response.get('recommendations', {})
        if recommendations:
            print(f"\nRecommendations:")
            for key, value in recommendations.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
    
    return success, response

def main():
    # Get the backend URL from the frontend .env file
    backend_url = "https://5604b1c7-af2d-4c2d-865a-51fe8d939149.preview.emergentagent.com"
    
    print(f"Testing Health Verify Now API at: {backend_url}")
    tester = HealthVerifyTester(backend_url)
    
    # Test API root
    if not tester.test_api_root():
        print("❌ API root test failed, stopping tests")
        return 1
    
    # Test SAM API endpoint first to check current system status
    print("\n=== Testing Current System Status ===")
    test_sam_api_endpoint(tester)
    
    # Test user registration or login
    print("\n=== Testing User Authentication ===")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_email = f"test{timestamp}@example.com"
    test_password = "test123"
    test_company = "Test Healthcare"
    
    success, _ = tester.test_register(
        email=test_email,
        password=test_password,
        company_name=test_company,
        first_name="Test",
        last_name="User"
    )
    
    if not success:
        print("❌ Registration failed, trying login instead...")
        # Try login with the test credentials
        success, _ = tester.test_login(test_email, test_password)
        if not success:
            print("❌ Login failed, stopping tests")
            return 1
    
    # Test getting current user info
    print("\n=== Testing Current User Info ===")
    tester.test_get_current_user()
    
    # Test creating a subscription if needed
    print("\n=== Testing Subscription Status ===")
    success, subscription_response = tester.test_get_subscription()
    
    if not success or not subscription_response.get('subscription'):
        print("No active subscription found, creating one...")
        employee_count = 5
        success, subscription = tester.test_create_subscription(employee_count)
        
        if success:
            print("\n=== PayPal Subscription Created ===")
            print(f"To complete the subscription, visit: {subscription.get('approval_url')}")
            print("This would normally redirect the user to PayPal for payment approval")
    else:
        print("Active subscription found, proceeding with tests")
    
    # Create a test employee
    print("\n=== Creating Test Employee ===")
    employee_id = tester.test_create_employee("Test", "Employee")
    
    if not employee_id:
        print("❌ Failed to create test employee, stopping tests")
        return 1
    
    # Test individual verification with SAM
    print("\n=== Testing Individual Employee Verification with SAM ===")
    success, results = tester.test_verify_employee(employee_id, ["sam"])
    
    if success:
        print(f"SAM verification initiated for employee ID: {employee_id}")
        
        # Wait for verification to complete
        print("Waiting for SAM verification to complete...")
        time.sleep(3)
        
        # Check verification results
        success, results = tester.test_get_employee_verification_results(employee_id)
        if success:
            sam_results = [r for r in results if r.get('verification_type') == 'sam']
            
            if sam_results:
                for result in sam_results:
                    status = result.get('status')
                    print(f"\nSAM Verification Status: {status.upper()}")
                    
                    # Check for error message
                    error_message = result.get('error_message')
                    if error_message:
                        print(f"Error Message: {error_message}")
                    
                    # Check for detailed results
                    results_data = result.get('results', {})
                    
                    # Check if SAM attempted to download data
                    database_info = results_data.get('database_info', {})
                    if database_info:
                        print(f"\nDatabase Info:")
                        print(f"  Total Exclusions: {database_info.get('total_exclusions_in_database', 0)}")
                        print(f"  Last Updated: {database_info.get('last_updated', 'Unknown')}")
                        print(f"  Source: {database_info.get('source', 'Unknown')}")
                        print(f"  Verification Method: {database_info.get('verification_method', 'Unknown')}")
                    
                    # Check for match details
                    match_details = results_data.get('match_details', [])
                    if match_details:
                        print(f"\nMatch Details Found: {len(match_details)}")
                        for i, match in enumerate(match_details, 1):
                            print(f"  Match #{i}:")
                            for key, value in match.items():
                                print(f"    {key}: {value}")
            else:
                print(f"No SAM verification results found for employee ID: {employee_id}")
    
    # Test individual verification with OIG
    print("\n=== Testing Individual Employee Verification with OIG ===")
    success, results = tester.test_verify_employee(employee_id, ["oig"])
    
    if success:
        print(f"OIG verification initiated for employee ID: {employee_id}")
        
        # Wait for verification to complete
        print("Waiting for OIG verification to complete...")
        time.sleep(3)
        
        # Check verification results
        success, results = tester.test_get_employee_verification_results(employee_id)
        if success:
            oig_results = [r for r in results if r.get('verification_type') == 'oig']
            
            if oig_results:
                for result in oig_results:
                    status = result.get('status')
                    print(f"\nOIG Verification Status: {status.upper()}")
                    
                    # Check for error message
                    error_message = result.get('error_message')
                    if error_message:
                        print(f"Error Message: {error_message}")
                    
                    # Check for detailed results
                    results_data = result.get('results', {})
                    
                    # Check database info
                    database_info = results_data.get('database_info', {})
                    if database_info:
                        print(f"\nDatabase Info:")
                        print(f"  Total Exclusions: {database_info.get('total_exclusions_in_database', 0)}")
                        print(f"  Last Updated: {database_info.get('last_updated', 'Unknown')}")
                        print(f"  Source: {database_info.get('source', 'Unknown')}")
            else:
                print(f"No OIG verification results found for employee ID: {employee_id}")
    
    # Test batch verification with both OIG and SAM
    print("\n=== Testing Batch Verification with OIG and SAM ===")
    
    # Create a few more test employees for batch testing
    batch_employee_ids = [employee_id]
    for i in range(2):
        batch_id = tester.test_create_employee(f"Batch{i}", "Employee")
        if batch_id:
            batch_employee_ids.append(batch_id)
    
    # Run batch verification
    tester.test_batch_verification(batch_employee_ids, ["oig", "sam"])
    
    # Wait for batch verification to complete
    print("\nWaiting for batch verification to complete...")
    time.sleep(5)
    
    # Get all verification results
    print("\n=== Summary of All Verification Results ===")
    success, all_results = tester.test_get_verification_results()
    
    if success:
        # Separate OIG and SAM results
        oig_results = [r for r in all_results if r.get('verification_type') == 'oig']
        sam_results = [r for r in all_results if r.get('verification_type') == 'sam']
        
        # Count OIG results by status
        oig_status_counts = {}
        for result in oig_results:
            status = result.get('status')
            oig_status_counts[status] = oig_status_counts.get(status, 0) + 1
        
        print("\nOIG Verification Results Summary:")
        for status, count in oig_status_counts.items():
            print(f"  - {status.upper()}: {count}")
        
        # Count SAM results by status
        sam_status_counts = {}
        for result in sam_results:
            status = result.get('status')
            sam_status_counts[status] = sam_status_counts.get(status, 0) + 1
        
        print("\nSAM Verification Results Summary:")
        for status, count in sam_status_counts.items():
            print(f"  - {status.upper()}: {count}")
        
        # Check for error messages in SAM results
        sam_error_messages = [r.get('error_message') for r in sam_results if r.get('error_message')]
        if sam_error_messages:
            print("\nSAM Error Messages:")
            for msg in set(sam_error_messages):
                count = sam_error_messages.count(msg)
                print(f"  - {msg} ({count} occurrences)")
    
    # Check system status again after tests
    print("\n=== Checking System Status After Tests ===")
    test_sam_api_endpoint(tester)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    main()
