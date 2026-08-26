from __future__ import annotations

import base64
import hashlib
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import Settings, get_settings


class KeyProvider(ABC):
    @abstractmethod
    def wrap_key(self, plaintext_key: bytes) -> tuple[bytes, str]: ...
    @abstractmethod
    def unwrap_key(self, wrapped_key: bytes, key_id: str) -> bytes: ...
    @abstractmethod
    def sign_digest(self, digest: bytes) -> tuple[bytes, str, str]: ...
    @abstractmethod
    def verify_digest(self, digest: bytes, signature: bytes, key_id: str, algorithm: str) -> bool: ...


class LocalKeyProvider(KeyProvider):
    """Development/test provider. Production configuration rejects it."""

    def __init__(self, settings: Settings):
        if not settings.local_master_key_b64 or not settings.local_signing_private_key_b64:
            raise ValueError("Local wrapping and signing keys are required")
        self.master = base64.b64decode(settings.local_master_key_b64)
        private_bytes = base64.b64decode(settings.local_signing_private_key_b64)
        self.private = Ed25519PrivateKey.from_private_bytes(private_bytes)
        self.public: Ed25519PublicKey = self.private.public_key()

    def wrap_key(self, plaintext_key: bytes) -> tuple[bytes, str]:
        nonce = __import__("os").urandom(12)
        return nonce + AESGCM(self.master).encrypt(
            nonce, plaintext_key, b"airshield-dek-wrap-v1"
        ), "local://wrap/v1"

    def unwrap_key(self, wrapped_key: bytes, key_id: str) -> bytes:
        if key_id != "local://wrap/v1":
            raise ValueError("Unknown local wrap key")
        return AESGCM(self.master).decrypt(wrapped_key[:12], wrapped_key[12:], b"airshield-dek-wrap-v1")

    def sign_digest(self, digest: bytes) -> tuple[bytes, str, str]:
        return self.private.sign(digest), "local://sign/v1", "Ed25519"

    def verify_digest(self, digest: bytes, signature: bytes, key_id: str, algorithm: str) -> bool:
        try:
            if key_id != "local://sign/v1" or algorithm != "Ed25519":
                return False
            self.public.verify(signature, digest)
            return True
        except Exception:
            return False


class AzureKeyVaultProvider(KeyProvider):
    def __init__(self, settings: Settings):
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.keys import KeyClient
        from azure.keyvault.keys.crypto import CryptographyClient

        if not settings.azure_key_vault_url:
            raise ValueError("AZURE_KEY_VAULT_URL is required for the Azure key provider")
        self.settings = settings
        self.credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        self.key_client = KeyClient(vault_url=settings.azure_key_vault_url, credential=self.credential)
        self.wrap_key_obj = self.key_client.get_key(settings.azure_wrap_key_name)
        self.sign_key_obj = self.key_client.get_key(settings.azure_sign_key_name)
        self.wrap_client = CryptographyClient(self.wrap_key_obj, self.credential)
        self.sign_client = CryptographyClient(self.sign_key_obj, self.credential)

    def _crypto_for_id(self, key_id: str):
        from azure.keyvault.keys.crypto import CryptographyClient

        return CryptographyClient(key_id, self.credential)

    def wrap_key(self, plaintext_key: bytes) -> tuple[bytes, str]:
        from azure.keyvault.keys.crypto import KeyWrapAlgorithm

        result = self.wrap_client.wrap_key(KeyWrapAlgorithm.rsa_oaep_256, plaintext_key)
        if not result.key_id:
            raise RuntimeError("Azure Key Vault wrap response omitted key id")
        return result.encrypted_key, result.key_id

    def unwrap_key(self, wrapped_key: bytes, key_id: str) -> bytes:
        from azure.keyvault.keys.crypto import KeyWrapAlgorithm

        return self._crypto_for_id(key_id).unwrap_key(KeyWrapAlgorithm.rsa_oaep_256, wrapped_key).key

    def sign_digest(self, digest: bytes) -> tuple[bytes, str, str]:
        from azure.keyvault.keys.crypto import SignatureAlgorithm

        result = self.sign_client.sign(SignatureAlgorithm.rs256, digest)
        if not result.key_id:
            raise RuntimeError("Azure Key Vault sign response omitted key id")
        return result.signature, result.key_id, "RS256"

    def verify_digest(self, digest: bytes, signature: bytes, key_id: str, algorithm: str) -> bool:
        from azure.keyvault.keys.crypto import SignatureAlgorithm

        if algorithm != "RS256":
            return False
        return bool(self._crypto_for_id(key_id).verify(SignatureAlgorithm.rs256, digest, signature).is_valid)


class OpenBaoTransitProvider(KeyProvider):
    def __init__(self, settings: Settings):
        if not settings.openbao_addr:
            raise ValueError("OPENBAO_ADDR is required for the OpenBao key provider")
        self.settings = settings
        self.token = settings.openbao_token_file.read_text().strip()
        self.client = httpx.Client(
            base_url=settings.openbao_addr, verify=True, timeout=10, headers={"X-Vault-Token": self.token}
        )

    def _post(self, path: str, body: dict) -> dict:
        response = self.client.post(path, json=body)
        response.raise_for_status()
        return response.json()["data"]

    def wrap_key(self, plaintext_key: bytes) -> tuple[bytes, str]:
        data = self._post(
            f"/v1/{self.settings.openbao_transit_mount}/encrypt/{self.settings.openbao_wrap_key}",
            {"plaintext": base64.b64encode(plaintext_key).decode()},
        )
        return data["ciphertext"].encode(), f"openbao://{self.settings.openbao_wrap_key}"

    def unwrap_key(self, wrapped_key: bytes, key_id: str) -> bytes:
        data = self._post(
            f"/v1/{self.settings.openbao_transit_mount}/decrypt/{self.settings.openbao_wrap_key}",
            {"ciphertext": wrapped_key.decode()},
        )
        return base64.b64decode(data["plaintext"])

    def sign_digest(self, digest: bytes) -> tuple[bytes, str, str]:
        data = self._post(
            f"/v1/{self.settings.openbao_transit_mount}/sign/{self.settings.openbao_sign_key}",
            {
                "input": base64.b64encode(digest).decode(),
                "prehashed": True,
                "hash_algorithm": "sha2-256",
                "signature_algorithm": "pss",
            },
        )
        return (
            data["signature"].encode(),
            f"openbao://{self.settings.openbao_sign_key}",
            "OpenBao-RSA-PSS-SHA256",
        )

    def verify_digest(self, digest: bytes, signature: bytes, key_id: str, algorithm: str) -> bool:
        data = self._post(
            f"/v1/{self.settings.openbao_transit_mount}/verify/{self.settings.openbao_sign_key}",
            {
                "input": base64.b64encode(digest).decode(),
                "signature": signature.decode(),
                "prehashed": True,
                "hash_algorithm": "sha2-256",
                "signature_algorithm": "pss",
            },
        )
        return bool(data.get("valid"))


@lru_cache(maxsize=1)
def get_key_provider() -> KeyProvider:
    settings = get_settings()
    if settings.key_provider == "azure":
        return AzureKeyVaultProvider(settings)
    if settings.key_provider == "openbao":
        return OpenBaoTransitProvider(settings)
    return LocalKeyProvider(settings)


def digest_bytes(payload: bytes) -> bytes:
    return hashlib.sha256(payload).digest()
