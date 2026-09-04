import logging
import keyring
from cryptography.fernet import Fernet

logger = logging.getLogger("FOMO.Security")

class SecurityVault:
    """
    Hardware-grade Security Vault storing encrypted credentials
    in OS Enclave (macOS Keychain, Windows Credential Manager, Linux Secret Service).
    """
    SERVICE_NAME = "FOMO_Desktop_App"

    def __init__(self):
        # Generate or load the master encryption key securely
        self._master_key = self._get_or_create_master_key()
        self._cipher = Fernet(self._master_key)

    def _get_or_create_master_key(self) -> bytes:
        """Fetch encryption master key from OS Keychain or generate a new one."""
        stored_key = keyring.get_password(self.SERVICE_NAME, "master_key")
        if stored_key:
            return stored_key.encode('utf-8')
        
        # Create a new secure Fernet key
        new_key = Fernet.generate_key()
        keyring.set_password(self.SERVICE_NAME, "master_key", new_key.decode('utf-8'))
        logger.info("New encryption key initialized in native OS Secure Enclave.")
        return new_key

    def store_private_key(self, wallet_address: str, private_key: str) -> bool:
        """Encrypt and store a private key into OS Secure Vault."""
        try:
            encrypted_pk = self._cipher.encrypt(private_key.encode('utf-8')).decode('utf-8')
            keyring.set_password(self.SERVICE_NAME, f"pk_{wallet_address}", encrypted_pk)
            logger.info(f"Private key for wallet {wallet_address[:6]}... securely stored.")
            return True
        except Exception as e:
            logger.error(f"Failed to store key in Secure Vault: {e}")
            return False

    def retrieve_private_key(self, wallet_address: str) -> str | None:
        """Retrieve and decrypt private key from OS Secure Vault."""
        try:
            encrypted_pk = keyring.get_password(self.SERVICE_NAME, f"pk_{wallet_address}")
            if not encrypted_pk:
                return None
            decrypted_pk = self._cipher.decrypt(encrypted_pk.encode('utf-8')).decode('utf-8')
            return decrypted_pk
        except Exception as e:
            logger.error(f"Failed to decrypt key for wallet {wallet_address[:6]}...: {e}")
            return None
