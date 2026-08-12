import os
import base64
import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

KEYCHAIN_USER = "local_vault_master"
FALLBACK_KEY_PATH = settings.STORAGE_DIR / ".vault_master.key"

def get_or_create_master_key() -> bytes:
    """
    Fetches the 256-bit AES key from the OS Keychain / Credential Locker.
    Falls back to a securely permissioned local file if the OS Keystore is unavailable.
    """
    key_b64 = None
    use_fallback = False
    
    # Try accessing the OS Keystore
    try:
        key_b64 = keyring.get_password(settings.SERVICE_NAME, KEYCHAIN_USER)
    except Exception as e:
        print(f"[SECURITY] OS Keystore unavailable ({e}). Using local fallback.")
        use_fallback = True

    # Handle Headless/WSL Linux Environments
    if use_fallback:
        if FALLBACK_KEY_PATH.exists():
            print("[SECURITY] Loaded existing Master Key from local fallback file.")
            key_b64 = FALLBACK_KEY_PATH.read_text().strip()
        else:
            raw_key = AESGCM.generate_key(bit_length=256)
            key_b64 = base64.b64encode(raw_key).decode("utf-8")
            
            # Save and heavily restrict file permissions (read/write for owner only)
            FALLBACK_KEY_PATH.write_text(key_b64)
            os.chmod(FALLBACK_KEY_PATH, 0o600)
            
            print("[SECURITY] Generated new Master Key and saved to restricted fallback file.")
        
        return base64.b64decode(key_b64)

    # Handle Normal Desktop Environments (Mac/Windows/Desktop Linux)
    if key_b64 is None:
        raw_key = AESGCM.generate_key(bit_length=256)
        key_b64 = base64.b64encode(raw_key).decode("utf-8")
        keyring.set_password(settings.SERVICE_NAME, KEYCHAIN_USER, key_b64)
        print("[SECURITY] Generated new AES-256 Master Key and stored in OS Keychain.")
    else:
        print("[SECURITY] Loaded existing Master Key from OS Keychain.")
        
    return base64.b64decode(key_b64)

class EncrypterAES256:
    def __init__(self):
        self.key = get_or_create_master_key()
        self.aesgcm = AESGCM(self.key)

    def encrypt_bytes(self, data: bytes) -> bytes:
        """
        Encrypts raw data using AES-256 GCM mode.
        Returns: Nonce (12 bytes) + Ciphertext + Authentication Tag
        """
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = self.aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_bytes(self, encrypted_payload: bytes) -> bytes:
        """
        Extracts Nonce and decrypts AES-256 GCM encrypted payload.
        """
        if len(encrypted_payload) < 12:
            raise ValueError("Payload too short to contain a valid nonce.")
        
        nonce = encrypted_payload[:12]
        ciphertext = encrypted_payload[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None)

vault_crypto = EncrypterAES256()