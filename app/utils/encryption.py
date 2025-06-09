from cryptography.fernet import Fernet
import base64
import hashlib

# Placeholder key - In a real app, this MUST be securely managed and not hardcoded!
ENCRYPTION_KEY_PASSWORD = 'this-is-a-super-secret-password-for-fernet-key-derivation'

def generate_key_from_password(password: str) -> bytes:
    hashed_key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(hashed_key)

ENCRYPTION_KEY = generate_key_from_password(ENCRYPTION_KEY_PASSWORD)

def encrypt_data(data: bytes, key: bytes) -> str:
    f = Fernet(key)
    encrypted_data = f.encrypt(data)
    return encrypted_data.decode()

def decrypt_data(encrypted_data_str: str, key: bytes) -> bytes:
    f = Fernet(key)
    encrypted_data_bytes = encrypted_data_str.encode()
    decrypted_data = f.decrypt(encrypted_data_bytes)
    return decrypted_data
