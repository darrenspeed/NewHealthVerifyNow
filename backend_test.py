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

def main():
    # Get the backend URL from the frontend .env file
    backend_url = "https://5604b1c7-af2d-4c2d-865a-51fe8d939149.preview.emergentagent.com"
    
    print(f"Testing Health Verify Now API at: {backend_url}")
    tester = HealthVerifyTester(backend_url)
    
    # Test API root
    if not tester.test_api_root():
        print("❌ API root test failed, stopping tests")
        return 1
    
    # Test creating employees with common names that might be in the OIG database
    print("\n=== Testing Employee Creation with Common Names ===")
    
    # Create test employees with common names
    common_names = [
        ("John", "Smith"),
        ("Michael", "Johnson"),
        ("Sarah", "Davis"),
        ("Robert", "Williams"),
        ("James", "Brown")
    ]
    
    employee_ids = []
    for first_name, last_name in common_names:
        employee_id = tester.test_create_employee(first_name, last_name)
        if employee_id:
            employee_ids.append(employee_id)
    
    # Create a test employee that should definitely pass
    clean_employee_id = tester.test_create_employee("Test", "Employee")
    if clean_employee_id:
        employee_ids.append(clean_employee_id)
    
    # Test OIG verification for each employee
    print("\n=== Testing OIG Verification with Real Data ===")
    
    verification_results = {}
    for employee_id in employee_ids:
        success, results = tester.test_verify_employee(employee_id, ["oig"])
        if success:
            verification_results[employee_id] = results
    
    # Wait for background tasks to complete
    print("\nWaiting for background tasks to complete...")
    time.sleep(3)
    
    # Check verification results for each employee
    print("\n=== Analyzing OIG Verification Results ===")
    
    for employee_id in employee_ids:
        success, results = tester.test_get_employee_verification_results(employee_id)
        
        if success:
            oig_results = [r for r in results if r.get('verification_type') == 'oig']
            
            if oig_results:
                for result in oig_results:
                    employee_name = next((f"{emp['first_name']} {emp['last_name']}" 
                                         for emp in tester.created_employees 
                                         if emp['id'] == employee_id), "Unknown")
                    
                    status = result.get('status')
                    print(f"\nEmployee: {employee_name} (ID: {employee_id})")
                    print(f"OIG Verification Status: {status.upper()}")
                    
                    # Check for detailed match information
                    results_data = result.get('results', {})
                    excluded = results_data.get('excluded', False)
                    
                    if excluded:
                        print("⚠️ EXCLUSION FOUND - Employee is on the OIG exclusion list!")
                        
                        # Print match details
                        match_details = results_data.get('match_details', [])
                        if match_details:
                            print("\nMatch Details:")
                            for i, match in enumerate(match_details, 1):
                                print(f"  Match #{i}:")
                                print(f"  - Name: {match.get('name', 'N/A')}")
                                print(f"  - Exclusion Type: {match.get('exclusion_type', 'N/A')}")
                                print(f"  - Exclusion Date: {match.get('exclusion_date', 'N/A')}")
                                print(f"  - Address: {match.get('address', 'N/A')}")
                                print(f"  - Match Score: {match.get('match_score', 'N/A')}")
                                if match.get('business_name'):
                                    print(f"  - Business Name: {match.get('business_name', 'N/A')}")
                                if match.get('specialty'):
                                    print(f"  - Specialty: {match.get('specialty', 'N/A')}")
                                if match.get('npi'):
                                    print(f"  - NPI: {match.get('npi', 'N/A')}")
                        
                        # Print database info
                        db_info = results_data.get('database_info', {})
                        if db_info:
                            print(f"\nDatabase Information:")
                            print(f"  - Total Exclusions: {db_info.get('total_exclusions_in_database', 'N/A')}")
                            print(f"  - Source: {db_info.get('source', 'N/A')}")
                    else:
                        print("✅ No exclusions found - Employee passed OIG verification")
                        
                        # Print search criteria
                        search_criteria = results_data.get('search_criteria', {})
                        if search_criteria:
                            print(f"\nSearch Criteria:")
                            print(f"  - First Name: {search_criteria.get('first_name', 'N/A')}")
                            print(f"  - Last Name: {search_criteria.get('last_name', 'N/A')}")
                            if search_criteria.get('middle_name'):
                                print(f"  - Middle Name: {search_criteria.get('middle_name', 'N/A')}")
                        
                        # Print database info
                        db_info = results_data.get('database_info', {})
                        if db_info:
                            print(f"\nDatabase Information:")
                            print(f"  - Total Exclusions: {db_info.get('total_exclusions_in_database', 'N/A')}")
                            print(f"  - Source: {db_info.get('source', 'N/A')}")
            else:
                print(f"No OIG verification results found for employee ID: {employee_id}")
    
    # Test batch verification
    print("\n=== Testing Batch OIG Verification ===")
    tester.test_batch_verification(employee_ids, ["oig"])
    
    # Wait for batch verification to complete
    print("\nWaiting for batch verification to complete...")
    time.sleep(5)
    
    # Get all verification results
    print("\n=== Summary of All Verification Results ===")
    success, all_results = tester.test_get_verification_results()
    
    if success:
        oig_results = [r for r in all_results if r.get('verification_type') == 'oig']
        
        # Count results by status
        status_counts = {}
        for result in oig_results:
            status = result.get('status')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nOIG Verification Results Summary:")
        for status, count in status_counts.items():
            print(f"  - {status.upper()}: {count}")
        
        # Count exclusions found
        exclusions_found = sum(1 for r in oig_results if r.get('results', {}).get('excluded', False))
        print(f"\nTotal OIG Exclusions Found: {exclusions_found}")
        
        # Check database size
        if oig_results:
            db_size = oig_results[0].get('results', {}).get('database_info', {}).get('total_exclusions_in_database', 'Unknown')
            print(f"OIG Database Size: {db_size} exclusions")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    main()
