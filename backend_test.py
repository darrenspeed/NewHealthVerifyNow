import requests
import time
import json
import random
import string
from datetime import datetime

# Backend URL from frontend .env
BACKEND_URL = "https://5604b1c7-af2d-4c2d-865a-51fe8d939149.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

class HealthVerifyTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.test_results = {
            "verification_system_status": False,
            "pricing_tiers": False,
            "user_registration": False,
            "user_login": False,
            "subscription_creation": False,
            "employee_creation": False,
            "employee_verification": False,
            "batch_verification": False,
            "verification_results": False
        }
        self.employee_id = None
        self.verification_types = []
        
    def generate_random_email(self):
        """Generate a random email for testing"""
        timestamp = int(time.time())
        random_str = ''.join(random.choices(string.ascii_lowercase, k=5))
        return f"test_{random_str}_{timestamp}@example.com"
    
    def test_verification_system_status(self):
        """Test the verification system status endpoint"""
        print("\n=== Testing Verification System Status ===")
        
        try:
            response = requests.get(f"{API_URL}/verification-system-status")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Verification System Status API is working")
                
                # System Overview
                system_overview = data.get('system_overview', {})
                print(f"\nSystem Overview:")
                print(f"  Platform: {system_overview.get('platform', 'Unknown')}")
                print(f"  Version: {system_overview.get('version', 'Unknown')}")
                print(f"  Capabilities: {system_overview.get('capabilities', 'Unknown')}")
                
                # Federal Exclusions
                federal_exclusions = data.get('federal_exclusions', {})
                print(f"\nFederal Exclusions:")
                
                oig_db = federal_exclusions.get('oig_database', {})
                print(f"  OIG Database:")
                print(f"    Loaded: {oig_db.get('loaded', False)}")
                print(f"    Exclusions Count: {oig_db.get('exclusions_count', 0)}")
                print(f"    Status: {oig_db.get('status', 'Unknown')}")
                
                sam_db = federal_exclusions.get('sam_database', {})
                print(f"  SAM Database:")
                print(f"    Loaded: {sam_db.get('loaded', False)}")
                print(f"    Exclusions Count: {sam_db.get('exclusions_count', 0)}")
                print(f"    Status: {sam_db.get('status', 'Unknown')}")
                
                # State Medicaid
                state_medicaid = data.get('state_medicaid', {})
                print(f"\nState Medicaid:")
                print(f"  Databases Available: {state_medicaid.get('databases_available', 0)}")
                print(f"  Databases Loaded: {state_medicaid.get('databases_loaded', 0)}")
                print(f"  Total Exclusions: {state_medicaid.get('total_exclusions', 0)}")
                print(f"  States Supported: {', '.join(state_medicaid.get('states_supported', []))}")
                print(f"  Status: {state_medicaid.get('status', 'Unknown')}")
                
                # License Verification
                license_verification = data.get('license_verification', {})
                print(f"\nLicense Verification:")
                
                npi_registry = license_verification.get('npi_registry', {})
                print(f"  NPI Registry:")
                print(f"    Loaded: {npi_registry.get('loaded', False)}")
                print(f"    Providers Count: {npi_registry.get('providers_count', 0)}")
                print(f"    Status: {npi_registry.get('status', 'Unknown')}")
                
                state_medical_boards = license_verification.get('state_medical_boards', {})
                print(f"  State Medical Boards:")
                print(f"    States Supported: {', '.join(state_medical_boards.get('states_supported', []))}")
                print(f"    License Types: {', '.join(state_medical_boards.get('license_types', []))}")
                print(f"    Status: {state_medical_boards.get('status', 'Unknown')}")
                
                # Criminal Background
                criminal_background = data.get('criminal_background', {})
                print(f"\nCriminal Background:")
                
                nsopw = criminal_background.get('nsopw_national', {})
                print(f"  NSOPW National:")
                print(f"    Loaded: {nsopw.get('loaded', False)}")
                print(f"    Records Count: {nsopw.get('records_count', 0)}")
                print(f"    Status: {nsopw.get('status', 'Unknown')}")
                
                fbi_wanted = criminal_background.get('fbi_wanted', {})
                print(f"  FBI Most Wanted:")
                print(f"    Loaded: {fbi_wanted.get('loaded', False)}")
                print(f"    Records Count: {fbi_wanted.get('records_count', 0)}")
                print(f"    Status: {fbi_wanted.get('status', 'Unknown')}")
                
                # HIPAA Compliance
                hipaa_compliance = data.get('hipaa_compliance', {})
                print(f"\nHIPAA Compliance:")
                print(f"  Enabled: {hipaa_compliance.get('enabled', False)}")
                print(f"  Data Encryption: {hipaa_compliance.get('data_encryption', 'Unknown')}")
                print(f"  Multi-Factor Auth: {hipaa_compliance.get('multi_factor_auth', 'Unknown')}")
                print(f"  Audit Logging: {hipaa_compliance.get('audit_logging', 'Unknown')}")
                print(f"  Status: {hipaa_compliance.get('status', 'Unknown')}")
                
                # Verification Capabilities
                verification_capabilities = data.get('verification_capabilities', {})
                print(f"\nVerification Capabilities:")
                print(f"  Total Verification Types: {verification_capabilities.get('total_verification_types', 0)}")
                print(f"  Federal Exclusions: {verification_capabilities.get('federal_exclusions', 0)}")
                print(f"  State Medicaid: {verification_capabilities.get('state_medicaid', 0)}")
                print(f"  License Verification: {verification_capabilities.get('license_verification', 0)}")
                print(f"  Criminal Background: {verification_capabilities.get('criminal_background', 0)}")
                print(f"  Comprehensive Check: {verification_capabilities.get('comprehensive_check', 'Unknown')}")
                
                # Check if we have at least 11 verification types
                total_types = verification_capabilities.get('total_verification_types', 0)
                if total_types >= 11:
                    print(f"✅ System has {total_types} verification types (required: 11+)")
                    self.test_results["verification_system_status"] = True
                else:
                    print(f"❌ System only has {total_types} verification types (required: 11+)")
                
                # Store verification types for later tests
                self.verification_types = data.get('available_verification_types', [])
                return True, data
            else:
                print(f"❌ Failed to get verification system status: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error testing verification system status: {str(e)}")
            return False, {}
    
    def test_pricing_tiers(self):
        """Test the pricing tiers endpoint"""
        print("\n=== Testing Pricing Tiers ===")
        
        try:
            response = requests.get(f"{API_URL}/pricing")
            
            if response.status_code == 200:
                data = response.json()
                pricing_tiers = data.get('pricing_tiers', [])
                
                print(f"✅ Pricing API is working, found {len(pricing_tiers)} tiers")
                
                # Check if we have the expected pricing tiers
                expected_tiers = [
                    {"name": "Basic Exclusions", "price": 29},
                    {"name": "Professional Credentialing", "price": 89},
                    {"name": "Complete Background", "price": 149},
                    {"name": "Enterprise", "price": 249},
                    {"name": "Healthcare System", "price": 399}
                ]
                
                found_tiers = []
                for tier in pricing_tiers:
                    tier_name = tier.get('name', '')
                    tier_price = tier.get('price_per_employee', 0)
                    print(f"  {tier_name}: ${tier_price}/employee")
                    
                    # Check if this tier matches any expected tier
                    for expected in expected_tiers:
                        if expected["name"].lower() in tier_name.lower() and expected["price"] == tier_price:
                            found_tiers.append(expected["name"])
                
                # Check if we found all expected tiers
                if len(found_tiers) == len(expected_tiers):
                    print("✅ All expected pricing tiers found")
                    self.test_results["pricing_tiers"] = True
                else:
                    missing = [t["name"] for t in expected_tiers if t["name"] not in found_tiers]
                    print(f"❌ Missing pricing tiers: {', '.join(missing)}")
                
                return True, data
            else:
                print(f"❌ Failed to get pricing tiers: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error testing pricing tiers: {str(e)}")
            return False, {}
    
    def test_user_registration(self):
        """Test user registration"""
        print("\n=== Testing User Registration ===")
        
        try:
            email = self.generate_random_email()
            password = "TestPassword123!"
            
            user_data = {
                "email": email,
                "password": password,
                "first_name": "Test",
                "last_name": "User",
                "company_name": "Test Company"
            }
            
            response = requests.post(f"{API_URL}/auth/register", json=user_data)
            
            if response.status_code == 201:
                data = response.json()
                print(f"✅ User registration successful: {email}")
                self.test_results["user_registration"] = True
                return True, data, email, password
            else:
                print(f"❌ Failed to register user: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}, email, password
                
        except Exception as e:
            print(f"❌ Error testing user registration: {str(e)}")
            return False, {}, None, None
    
    def test_user_login(self, email=None, password=None):
        """Test user login"""
        print("\n=== Testing User Login ===")
        
        if not email or not password:
            # Use default test credentials if not provided
            email = "test@example.com"
            password = "TestPassword123!"
        
        try:
            login_data = {
                "email": email,
                "password": password
            }
            
            response = requests.post(f"{API_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                self.user_id = data.get('user_id')
                
                print(f"✅ User login successful: {email}")
                print(f"  User ID: {self.user_id}")
                print(f"  Token received: {self.token[:10]}...")
                
                self.test_results["user_login"] = True
                return True, data
            else:
                print(f"❌ Failed to login: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error testing user login: {str(e)}")
            return False, {}
    
    def test_subscription_creation(self):
        """Test subscription creation"""
        print("\n=== Testing Subscription Creation ===")
        
        if not self.token:
            print("❌ Cannot test subscription creation: No authentication token")
            return False, {}
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Get pricing tiers first
            pricing_response = requests.get(f"{API_URL}/pricing")
            pricing_tiers = pricing_response.json().get('pricing_tiers', [])
            
            if not pricing_tiers:
                print("❌ Cannot test subscription creation: No pricing tiers available")
                return False, {}
            
            # Select the first tier
            selected_tier = pricing_tiers[0]
            tier_id = selected_tier.get('id')
            
            subscription_data = {
                "tier_id": tier_id,
                "employee_count": 5,
                "payment_method": "paypal"
            }
            
            response = requests.post(f"{API_URL}/subscriptions", json=subscription_data, headers=headers)
            
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Subscription creation successful")
                print(f"  Tier: {selected_tier.get('name')}")
                print(f"  Employee Count: 5")
                print(f"  Monthly Cost: ${selected_tier.get('price_per_employee', 0) * 5}")
                
                self.test_results["subscription_creation"] = True
                return True, data
            else:
                print(f"❌ Failed to create subscription: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error testing subscription creation: {str(e)}")
            return False, {}
    
    def test_employee_creation(self):
        """Test employee creation"""
        print("\n=== Testing Employee Creation ===")
        
        if not self.token:
            print("❌ Cannot test employee creation: No authentication token")
            return False, {}
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            employee_data = {
                "first_name": "John",
                "last_name": "Doe",
                "middle_name": "M",
                "ssn": "123-45-6789",
                "date_of_birth": "1980-01-01",
                "email": "john.doe@example.com",
                "phone": "555-123-4567",
                "license_number": "MD12345",
                "license_type": "MD",
                "license_state": "CA"
            }
            
            response = requests.post(f"{API_URL}/employees", json=employee_data, headers=headers)
            
            if response.status_code == 201:
                data = response.json()
                self.employee_id = data.get('id')
                
                print(f"✅ Employee creation successful")
                print(f"  Employee ID: {self.employee_id}")
                print(f"  Name: {employee_data['first_name']} {employee_data['last_name']}")
                print(f"  License: {employee_data['license_type']} {employee_data['license_number']} ({employee_data['license_state']})")
                
                self.test_results["employee_creation"] = True
                return True, data
            else:
                print(f"❌ Failed to create employee: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error testing employee creation: {str(e)}")
            return False, {}
    
    def test_employee_verification(self):
        """Test individual employee verification"""
        print("\n=== Testing Individual Employee Verification ===")
        
        if not self.token or not self.employee_id:
            print("❌ Cannot test employee verification: No authentication token or employee ID")
            return False, {}
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Use all verification types for comprehensive check
            verification_types = [
                'oig', 'sam',                    # Federal exclusions
                'npi',                           # License verification
                'license_md_ca', 'license_rn_ca', # California licenses  
                'nsopw_national', 'fbi_wanted',  # Criminal background
                'medicaid_ca', 'medicaid_tx'     # State Medicaid
            ]
            
            response = requests.post(
                f"{API_URL}/employees/{self.employee_id}/verify", 
                json=verification_types, 
                headers=headers
            )
            
            if response.status_code == 202:
                data = response.json()
                print(f"✅ Employee verification initiated successfully")
                print(f"  Verification types: {', '.join(verification_types)}")
                
                # Wait for verification to complete
                print("  Waiting for verification to complete...")
                time.sleep(3)
                
                # Check verification results
                results_response = requests.get(
                    f"{API_URL}/verification-results?employee_id={self.employee_id}", 
                    headers=headers
                )
                
                if results_response.status_code == 200:
                    results_data = results_response.json()
                    result_count = len(results_data)
                    
                    print(f"  Retrieved {result_count} verification results")
                    
                    if result_count > 0:
                        # Check if we have results for different verification types
                        types_found = set(r.get('verification_type') for r in results_data)
                        print(f"  Verification types found: {', '.join(types_found)}")
                        
                        # Check if we have license and criminal background results
                        has_license = any('license' in t for t in types_found)
                        has_criminal = any(t in ('nsopw_national', 'fbi_wanted') for t in types_found)
                        
                        if has_license and has_criminal:
                            print("✅ Verification results include license and criminal background checks")
                            self.test_results["employee_verification"] = True
                        else:
                            missing = []
                            if not has_license:
                                missing.append("license verification")
                            if not has_criminal:
                                missing.append("criminal background")
                            
                            print(f"❌ Verification results missing: {', '.join(missing)}")
                    else:
                        print("❌ No verification results found")
                else:
                    print(f"❌ Failed to retrieve verification results: HTTP {results_response.status_code}")
                
                return True, data
            else:
                print(f"❌ Failed to initiate employee verification: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error testing employee verification: {str(e)}")
            return False, {}
    
    def test_batch_verification(self):
        """Test batch verification"""
        print("\n=== Testing Batch Verification ===")
        
        if not self.token or not self.employee_id:
            print("❌ Cannot test batch verification: No authentication token or employee ID")
            return False, {}
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Create a second test employee
            employee_data = {
                "first_name": "Jane",
                "last_name": "Smith",
                "ssn": "987-65-4321",
                "license_number": "RN54321",
                "license_type": "RN",
                "license_state": "TX"
            }
            
            response = requests.post(f"{API_URL}/employees", json=employee_data, headers=headers)
            
            if response.status_code == 201:
                second_employee_id = response.json().get('id')
                print(f"✅ Created second test employee: {second_employee_id}")
                
                # Now test batch verification
                batch_data = {
                    "employee_ids": [self.employee_id, second_employee_id],
                    "verification_types": [
                        'oig', 'sam',           # Federal exclusions
                        'npi',                  # License verification
                        'nsopw_national',       # Criminal background
                        'medicaid_ca'           # State Medicaid
                    ]
                }
                
                batch_response = requests.post(f"{API_URL}/verify-batch", json=batch_data, headers=headers)
                
                if batch_response.status_code == 202:
                    print(f"✅ Batch verification initiated successfully")
                    print(f"  Employees: {len(batch_data['employee_ids'])}")
                    print(f"  Verification types: {', '.join(batch_data['verification_types'])}")
                    
                    # Wait for verification to complete
                    print("  Waiting for batch verification to complete...")
                    time.sleep(5)
                    
                    # Check verification results
                    results_response = requests.get(f"{API_URL}/verification-results", headers=headers)
                    
                    if results_response.status_code == 200:
                        results_data = results_response.json()
                        
                        # Filter results for our batch employees
                        batch_results = [r for r in results_data if r.get('employee_id') in batch_data['employee_ids']]
                        
                        print(f"  Retrieved {len(batch_results)} batch verification results")
                        
                        if len(batch_results) > 0:
                            self.test_results["batch_verification"] = True
                            return True, batch_results
                        else:
                            print("❌ No batch verification results found")
                    else:
                        print(f"❌ Failed to retrieve batch results: HTTP {results_response.status_code}")
                else:
                    print(f"❌ Failed to initiate batch verification: HTTP {batch_response.status_code}")
                    print(f"Response: {batch_response.text}")
            else:
                print(f"❌ Failed to create second employee: HTTP {response.status_code}")
            
            return False, {}
                
        except Exception as e:
            print(f"❌ Error testing batch verification: {str(e)}")
            return False, {}
    
    def test_verification_results(self):
        """Test verification results retrieval"""
        print("\n=== Testing Verification Results ===")
        
        if not self.token:
            print("❌ Cannot test verification results: No authentication token")
            return False, {}
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = requests.get(f"{API_URL}/verification-results", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                result_count = len(data)
                
                print(f"✅ Retrieved {result_count} verification results")
                
                if result_count > 0:
                    # Check if we have results for different verification types
                    types_found = set(r.get('verification_type') for r in data)
                    print(f"  Verification types found: {', '.join(types_found)}")
                    
                    # Check if we have license and criminal background results
                    has_license = any('license' in t for t in types_found)
                    has_criminal = any(t in ('nsopw_national', 'fbi_wanted') for t in types_found)
                    
                    if has_license and has_criminal:
                        print("✅ Verification results include license and criminal background checks")
                        self.test_results["verification_results"] = True
                    else:
                        missing = []
                        if not has_license:
                            missing.append("license verification")
                        if not has_criminal:
                            missing.append("criminal background")
                        
                        print(f"❌ Verification results missing: {', '.join(missing)}")
                else:
                    print("❌ No verification results found")
                
                return True, data
            else:
                print(f"❌ Failed to retrieve verification results: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Error testing verification results: {str(e)}")
            return False, {}
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=== Starting Health Verify Now API Tests ===")
        
        # Test verification system status
        self.test_verification_system_status()
        
        # Test pricing tiers
        self.test_pricing_tiers()
        
        # Test user registration and login
        reg_success, _, email, password = self.test_user_registration()
        
        if reg_success:
            # Login with the newly created user
            self.test_user_login(email, password)
        else:
            # Try login with default credentials
            self.test_user_login()
        
        # If we have a token, continue with other tests
        if self.token:
            self.test_subscription_creation()
            self.test_employee_creation()
            
            if self.employee_id:
                self.test_employee_verification()
                self.test_batch_verification()
            
            self.test_verification_results()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print a summary of test results"""
        print("\n=== Health Verify Now API Test Summary ===")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name.replace('_', ' ').title()}")
        
        print("\nVerification Capabilities:")
        if self.test_results["verification_system_status"]:
            print("✅ System shows 11+ verification types")
        else:
            print("❌ System does not show 11+ verification types")
        
        if self.test_results["pricing_tiers"]:
            print("✅ Pricing reflects new comprehensive capabilities ($29-$399/employee)")
        else:
            print("❌ Pricing does not reflect new comprehensive capabilities")
        
        if self.test_results["verification_results"]:
            print("✅ Verification results include license and criminal background checks")
        else:
            print("❌ Verification results do not include license and criminal background checks")
        
        print("\nConclusion:")
        if passed_tests >= total_tests * 0.7:  # 70% pass threshold
            print("Health Verify Now is a functional, comprehensive credentialing platform")
            print("with enterprise-level pricing that reflects its expanded capabilities.")
        else:
            print("Health Verify Now has some issues that need to be addressed before")
            print("it can be considered a fully functional credentialing platform.")

def main():
    tester = HealthVerifyTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()