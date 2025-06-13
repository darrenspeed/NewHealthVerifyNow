"""
HIPAA-Compliant Encryption Module for Health Verify Now
Implements field-level encryption for PHI data
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class PHIEncryption:
    """HIPAA-compliant encryption for PHI data"""
    
    def __init__(self):
        self.master_key = os.environ.get('PHI_MASTER_KEY')
        if not self.master_key:
            raise ValueError("PHI_MASTER_KEY environment variable not set")
        
        # Generate encryption key from master key
        self.key = self._derive_key(self.master_key.encode())
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: bytes) -> bytes:
        """Derive encryption key from master password"""
        # Use a fixed salt for consistency (in production, use per-customer salts)
        salt = b'health_verify_now_salt_2025'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_field(self, data: str) -> str:
        """Encrypt a single field of PHI data"""
        if not data:
            return data
        
        try:
            encrypted = self.cipher.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_field(self, encrypted_data: str) -> str:
        """Decrypt a single field of PHI data"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_employee_phi(self, employee_data: dict) -> dict:
        """Encrypt PHI fields in employee data"""
        phi_fields = ['ssn', 'date_of_birth', 'phone', 'email']
        encrypted_data = employee_data.copy()
        
        for field in phi_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt_field(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_employee_phi(self, encrypted_data: dict) -> dict:
        """Decrypt PHI fields in employee data"""
        phi_fields = ['ssn', 'date_of_birth', 'phone', 'email']
        decrypted_data = encrypted_data.copy()
        
        for field in phi_fields:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_data[field] = self.decrypt_field(encrypted_data[field])
        
        return decrypted_data

# Global encryption instance
phi_encryption = PHIEncryption()