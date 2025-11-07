#!/usr/bin/env python3
"""
Comprehensive security testing script for Secret Vault
Tests input validation, rate limiting, and security features
"""

import requests
import json
import time
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

# Configuration
API_BASE_URL = "http://localhost:8000"

class SecurityTester:
    def __init__(self):
        self.test_results = []
        self.session = requests.Session()
    
    def log_test(self, test_name, status, details=""):
        """Log test results"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
    
    def test_api_health(self):
        """Test API health"""
        try:
            response = self.session.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                self.log_test("API Health Check", "PASS", "API is running")
                return True
            else:
                self.log_test("API Health Check", "FAIL", f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", "FAIL", f"Connection error: {e}")
            return False
    
    def test_input_validation(self):
        """Test input validation"""
        print("\n🧪 Testing Input Validation...")
        
        # Test invalid email formats
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user..name@domain.com",
            "",
            "a" * 300  # Too long
        ]
        
        for email in invalid_emails:
            try:
                response = self.session.post(f"{API_BASE_URL}/auth/login", json={
                    "email": email,
                    "password": "TestPass123!"
                }, timeout=5)
                
                if response.status_code == 400:
                    self.log_test(f"Invalid Email Rejection: {email[:20]}...", "PASS")
                else:
                    self.log_test(f"Invalid Email Rejection: {email[:20]}...", "FAIL", 
                                f"Expected 400, got {response.status_code}")
            except Exception as e:
                self.log_test(f"Invalid Email Rejection: {email[:20]}...", "FAIL", str(e))
        
        # Test weak passwords
        weak_passwords = [
            "123456",
            "password",
            "abc",
            "Password",  # No numbers
            "password123",  # No uppercase
            "PASSWORD123",  # No lowercase
        ]
        
        for password in weak_passwords:
            try:
                response = self.session.post(f"{API_BASE_URL}/auth/signup", json={
                    "email": f"test{int(time.time())}@example.com",
                    "username": f"testuser{int(time.time())}",
                    "full_name": "Test User",
                    "password": password
                }, timeout=5)
                
                if response.status_code == 400:
                    self.log_test(f"Weak Password Rejection: {password}", "PASS")
                else:
                    self.log_test(f"Weak Password Rejection: {password}", "FAIL", 
                                f"Expected 400, got {response.status_code}")
            except Exception as e:
                self.log_test(f"Weak Password Rejection: {password}", "FAIL", str(e))
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        print("\n🚦 Testing Rate Limiting...")
        
        # Test rapid login attempts
        failed_attempts = 0
        rate_limited = False
        
        for i in range(10):
            try:
                response = self.session.post(f"{API_BASE_URL}/auth/login", json={
                    "email": "nonexistent@example.com",
                    "password": "wrongpassword"
                }, timeout=5)
                
                if response.status_code == 401:
                    failed_attempts += 1
                elif response.status_code == 429:
                    rate_limited = True
                    break
                    
                time.sleep(0.1)  # Small delay
            except Exception as e:
                pass
        
        if rate_limited:
            self.log_test("Rate Limiting", "PASS", f"Rate limited after {failed_attempts} attempts")
        else:
            self.log_test("Rate Limiting", "FAIL", "No rate limiting detected")
    
    def test_sql_injection(self):
        """Test SQL injection protection"""
        print("\n💉 Testing SQL Injection Protection...")
        
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for payload in sql_payloads:
            try:
                response = self.session.post(f"{API_BASE_URL}/auth/login", json={
                    "email": payload,
                    "password": "test"
                }, timeout=5)
                
                if response.status_code in [400, 401]:
                    self.log_test(f"SQL Injection Protection: {payload[:20]}...", "PASS")
                else:
                    self.log_test(f"SQL Injection Protection: {payload[:20]}...", "FAIL", 
                                f"Status code: {response.status_code}")
            except Exception as e:
                self.log_test(f"SQL Injection Protection: {payload[:20]}...", "FAIL", str(e))
    
    def test_xss_protection(self):
        """Test XSS protection"""
        print("\n🛡️ Testing XSS Protection...")
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            try:
                response = self.session.post(f"{API_BASE_URL}/auth/signup", json={
                    "email": f"test{int(time.time())}@example.com",
                    "username": payload,
                    "full_name": "Test User",
                    "password": "TestPass123!"
                }, timeout=5)
                
                # Check if payload is sanitized in response
                if payload in response.text:
                    self.log_test(f"XSS Protection: {payload[:20]}...", "FAIL", "Payload not sanitized")
                else:
                    self.log_test(f"XSS Protection: {payload[:20]}...", "PASS")
            except Exception as e:
                self.log_test(f"XSS Protection: {payload[:20]}...", "FAIL", str(e))
    
    def test_authentication_security(self):
        """Test authentication security"""
        print("\n🔐 Testing Authentication Security...")
        
        # Test with valid credentials (should work)
        try:
            response = self.session.post(f"{API_BASE_URL}/auth/login", json={
                "email": "testadmin@example.com",
                "password": "TestAdmin123!"
            }, timeout=5)
            
            if response.status_code == 200:
                token_data = response.json()
                if "access_token" in token_data:
                    self.log_test("Valid Login", "PASS", "Authentication successful")
                    
                    # Test token validation
                    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                    protected_response = self.session.get(f"{API_BASE_URL}/credentials", headers=headers, timeout=5)
                    
                    if protected_response.status_code == 200:
                        self.log_test("Token Validation", "PASS", "Protected endpoint accessible")
                    else:
                        self.log_test("Token Validation", "FAIL", f"Status code: {protected_response.status_code}")
                else:
                    self.log_test("Valid Login", "FAIL", "No access token in response")
            else:
                self.log_test("Valid Login", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Valid Login", "FAIL", str(e))
        
        # Test with invalid credentials
        try:
            response = self.session.post(f"{API_BASE_URL}/auth/login", json={
                "email": "testadmin@example.com",
                "password": "wrongpassword"
            }, timeout=5)
            
            if response.status_code == 401:
                self.log_test("Invalid Login Rejection", "PASS", "Invalid credentials rejected")
            else:
                self.log_test("Invalid Login Rejection", "FAIL", f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Login Rejection", "FAIL", str(e))
    
    def test_concurrent_requests(self):
        """Test concurrent request handling"""
        print("\n⚡ Testing Concurrent Request Handling...")
        
        def make_login_request():
            try:
                response = requests.post(f"{API_BASE_URL}/auth/login", json={
                    "email": "nonexistent@example.com",
                    "password": "wrongpassword"
                }, timeout=5)
                return response.status_code
            except:
                return None
        
        # Make 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_login_request) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # Check if all requests were handled properly
        valid_responses = [r for r in results if r in [401, 429]]
        if len(valid_responses) == 10:
            self.log_test("Concurrent Request Handling", "PASS", "All requests handled properly")
        else:
            self.log_test("Concurrent Request Handling", "FAIL", 
                        f"Only {len(valid_responses)}/10 requests handled properly")
    
    def test_google_oauth_security(self):
        """Test Google OAuth security"""
        print("\n🔗 Testing Google OAuth Security...")
        
        # Test with invalid OAuth data
        invalid_oauth_data = [
            {"email": "", "name": "Test User", "google_id": "123"},
            {"email": "test@example.com", "name": "", "google_id": "123"},
            {"email": "test@example.com", "name": "Test User", "google_id": ""},
            {"email": "invalid-email", "name": "Test User", "google_id": "123"}
        ]
        
        for data in invalid_oauth_data:
            try:
                response = self.session.post(f"{API_BASE_URL}/auth/google", json=data, timeout=5)
                
                if response.status_code == 400:
                    self.log_test(f"Invalid OAuth Data Rejection: {data['email'][:20]}...", "PASS")
                else:
                    self.log_test(f"Invalid OAuth Data Rejection: {data['email'][:20]}...", "FAIL", 
                                f"Expected 400, got {response.status_code}")
            except Exception as e:
                self.log_test(f"Invalid OAuth Data Rejection: {data['email'][:20]}...", "FAIL", str(e))
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🔒 Secret Vault Security Testing Suite")
        print("=" * 60)
        print(f"Testing against: {API_BASE_URL}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run tests
        if not self.test_api_health():
            print("❌ API is not running. Please start the backend first:")
            print("   python main.py")
            return
        
        self.test_input_validation()
        self.test_rate_limiting()
        self.test_sql_injection()
        self.test_xss_protection()
        self.test_authentication_security()
        self.test_concurrent_requests()
        self.test_google_oauth_security()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate security test report"""
        print("\n" + "=" * 60)
        print("📊 SECURITY TEST REPORT")
        print("=" * 60)
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  • {result['test']}: {result['details']}")
        
        print(f"\n🏁 Security testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Save report to file
        report_file = f"security_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed/total)*100
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved to: {report_file}")

def main():
    """Main function"""
    tester = SecurityTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
