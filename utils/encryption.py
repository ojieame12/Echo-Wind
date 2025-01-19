from passlib.context import CryptContext
from cryptography.fernet import Fernet
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Credential encryption
class CredentialEncryption:
    def __init__(self):
        self.key = os.getenv("ENCRYPTION_KEY", Fernet.generate_key()).encode()
        self.cipher_suite = Fernet(self.key)
    
    def encrypt_credentials(self, credentials: dict) -> str:
        """Encrypt credentials dictionary"""
        credentials_str = json.dumps(credentials)
        encrypted_data = self.cipher_suite.encrypt(credentials_str.encode())
        return encrypted_data.decode()
    
    def decrypt_credentials(self, encrypted_credentials: str) -> dict:
        """Decrypt credentials back to dictionary"""
        decrypted_data = self.cipher_suite.decrypt(encrypted_credentials.encode())
        return json.loads(decrypted_data.decode())
