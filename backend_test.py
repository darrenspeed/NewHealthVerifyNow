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

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
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

    def test_create_employee(self, first_name, last_name, should_pass=True):
        """Test creating an employee"""
        employee_data = {
            "first_name": first_name,
            "last_name": last_name,
            "ssn": "123-45-6789",
            "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
            "date_of_birth": "1990-01-01",
            "license_number": "ABC123" if should_pass else None
        }
        
        success, response = self.run_test(
            f"Create Employee: {first_name} {last_name}",
            "POST",
            "api/employees",
            200 if should_pass else 400,
            data=employee_data
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
            200
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
            data=verification_types
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
            data=data
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
            200
        )
        if success:
            print(f"Retrieved {len(response)} verification results")
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
    
    # Test creating employees
    print("\n=== Testing Employee Creation ===")
    # Test with employees that should pass
    alice_id = tester.test_create_employee("Alice", "Johnson")
    bob_id = tester.test_create_employee("Bob", "Wilson")
    
    # Test with employees that should trigger exclusions
    john_id = tester.test_create_employee("John", "Doe")
    jane_id = tester.test_create_employee("Jane", "Smith")
    
    # Test getting employees
    print("\n=== Testing Employee Retrieval ===")
    tester.test_get_employees()
    
    # Test OIG verification
    print("\n=== Testing OIG Verification ===")
    if alice_id:
        tester.test_verify_employee(alice_id, ["oig"])
    
    # Test SAM verification
    print("\n=== Testing SAM Verification ===")
    if bob_id:
        tester.test_verify_employee(bob_id, ["sam"])
    
    # Test both verifications on an employee that should trigger exclusions
    print("\n=== Testing Verification with Exclusions ===")
    if john_id:
        tester.test_verify_employee(john_id, ["oig", "sam"])
    
    # Test batch verification
    print("\n=== Testing Batch Verification ===")
    employee_ids = [id for id in [alice_id, bob_id, john_id, jane_id] if id]
    if employee_ids:
        tester.test_batch_verification(employee_ids, ["oig", "sam"])
    
    # Wait a bit for background tasks to complete
    print("\nWaiting for background tasks to complete...")
    time.sleep(3)
    
    # Test getting verification results
    print("\n=== Testing Verification Results Retrieval ===")
    success, results = tester.test_get_verification_results()
    
    if success:
        # Check for expected results
        exclusions_found = False
        for result in results:
            if result.get('status') == 'failed':
                exclusions_found = True
                employee_id = result.get('employee_id')
                verification_type = result.get('verification_type')
                print(f"Found exclusion for employee {employee_id} in {verification_type} check")
        
        if not exclusions_found and john_id:
            print("❌ Expected to find exclusions for John Doe but none were found")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    main()
