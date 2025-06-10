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
    
    # Test creating employees specifically for SAM verification
    print("\n=== Testing Employee Creation for SAM Verification ===")
    # Test with a normal name
    alice_id = tester.test_create_employee("Alice", "Johnson")
    
    # Test with a common name that might have more potential matches
    john_id = tester.test_create_employee("John", "Smith")
    
    # Test SAM verification with the updated API key
    print("\n=== Testing SAM Verification with Updated API Key ===")
    if alice_id:
        print("\n--- Testing SAM verification for Alice Johnson ---")
        success, alice_results = tester.test_verify_employee(alice_id, ["sam"])
        
        # Check if the verification was successful (not an error)
        if success:
            for result in alice_results.get('results', []):
                if result.get('verification_type') == 'sam':
                    status = result.get('status')
                    if status == 'error':
                        print("❌ SAM verification failed with error status")
                        print(f"Error message: {result.get('error_message')}")
                    else:
                        print(f"✅ SAM verification completed with status: {status}")
                        print(f"This indicates the API key is working correctly!")
    
    # Test with a common name (more likely to have potential matches)
    if john_id:
        print("\n--- Testing SAM verification for John Smith ---")
        success, john_results = tester.test_verify_employee(john_id, ["sam"])
        
        # Check if the verification was successful (not an error)
        if success:
            for result in john_results.get('results', []):
                if result.get('verification_type') == 'sam':
                    status = result.get('status')
                    if status == 'error':
                        print("❌ SAM verification failed with error status")
                        print(f"Error message: {result.get('error_message')}")
                    else:
                        print(f"✅ SAM verification completed with status: {status}")
                        print(f"This indicates the API key is working correctly!")
    
    # Wait a bit for any background tasks to complete
    print("\nWaiting for background tasks to complete...")
    time.sleep(3)
    
    # Test getting verification results to check for SAM results
    print("\n=== Testing Verification Results for SAM Checks ===")
    success, results = tester.test_get_verification_results()
    
    if success:
        # Check specifically for SAM verification results
        sam_results_found = False
        sam_errors_found = False
        
        for result in results:
            if result.get('verification_type') == 'sam':
                sam_results_found = True
                status = result.get('status')
                employee_id = result.get('employee_id')
                
                if status == 'error':
                    sam_errors_found = True
                    error_msg = result.get('error_message', 'No error message')
                    print(f"❌ SAM verification error for employee {employee_id}: {error_msg}")
                else:
                    print(f"✅ SAM verification for employee {employee_id} completed with status: {status}")
                    
                # Check for API response details
                api_response = result.get('results', {}).get('api_response_summary', {})
                if api_response:
                    status_code = api_response.get('status_code')
                    print(f"   API Status Code: {status_code}")
                    if status_code == 200:
                        print("   ✅ SAM API returned successful status code 200")
                    else:
                        print(f"   ❌ SAM API returned non-200 status code: {status_code}")
        
        if not sam_results_found:
            print("❌ No SAM verification results were found")
        elif not sam_errors_found:
            print("✅ No SAM API errors were found - the API key appears to be working correctly!")
        else:
            print("❌ SAM API errors were found - the API key may not be working correctly")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    main()
