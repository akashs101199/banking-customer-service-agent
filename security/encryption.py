"""
Data Encryption and Decryption Utilities
Handles encryption of sensitive data like card numbers, CVV, PII
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import logging

from config import settings

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, encryption_key: str = None):
        """
        Initialize encryption manager
        
        Args:
            encryption_key: Base encryption key (from settings if not provided)
        """
        key = encryption_key or settings.encryption_key
        self.cipher = self._create_cipher(key)
    
    def _create_cipher(self, key: str) -> Fernet:
        """Create Fernet cipher from encryption key"""
        # Derive a proper key from the provided key string
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'banking_ai_salt',  # In production, use unique salt per installation
            iterations=100000,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(derived_key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Encrypted data as string
        """
        try:
            if not data:
                return data
            
            encrypted_bytes = self.cipher.encrypt(data.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Encrypted data string
            
        Returns:
            Decrypted plain text
        """
        try:
            if not encrypted_data:
                return encrypted_data
            
            decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def encrypt_card_number(self, card_number: str) -> str:
        """Encrypt card number"""
        return self.encrypt(card_number)
    
    def decrypt_card_number(self, encrypted_card: str) -> str:
        """Decrypt card number"""
        return self.decrypt(encrypted_card)
    
    def mask_card_number(self, card_number: str) -> str:
        """
        Mask card number for display (show last 4 digits)
        
        Args:
            card_number: Full card number
            
        Returns:
            Masked card number (e.g., **** **** **** 1234)
        """
        if not card_number or len(card_number) < 4:
            return "****"
        
        return f"**** **** **** {card_number[-4:]}"
    
    def encrypt_cvv(self, cvv: str) -> str:
        """Encrypt CVV"""
        return self.encrypt(cvv)
    
    def decrypt_cvv(self, encrypted_cvv: str) -> str:
        """Decrypt CVV"""
        return self.decrypt(encrypted_cvv)
    
    def encrypt_ssn(self, ssn: str) -> str:
        """Encrypt SSN or national ID"""
        return self.encrypt(ssn)
    
    def decrypt_ssn(self, encrypted_ssn: str) -> str:
        """Decrypt SSN or national ID"""
        return self.decrypt(encrypted_ssn)
    
    def mask_ssn(self, ssn: str) -> str:
        """
        Mask SSN for display
        
        Args:
            ssn: Full SSN
            
        Returns:
            Masked SSN (e.g., ***-**-1234)
        """
        if not ssn or len(ssn) < 4:
            return "***-**-****"
        
        return f"***-**-{ssn[-4:]}"


# Global encryption manager instance
encryption_manager = EncryptionManager()


def encrypt_data(data: str) -> str:
    """Convenience function to encrypt data"""
    return encryption_manager.encrypt(data)


def decrypt_data(encrypted_data: str) -> str:
    """Convenience function to decrypt data"""
    return encryption_manager.decrypt(encrypted_data)


def mask_sensitive_data(data: str, data_type: str = "card") -> str:
    """
    Mask sensitive data for display
    
    Args:
        data: Sensitive data to mask
        data_type: Type of data (card, ssn, etc.)
        
    Returns:
        Masked data
    """
    if data_type == "card":
        return encryption_manager.mask_card_number(data)
    elif data_type == "ssn":
        return encryption_manager.mask_ssn(data)
    else:
        # Generic masking
        if len(data) <= 4:
            return "****"
        return f"****{data[-4:]}"
