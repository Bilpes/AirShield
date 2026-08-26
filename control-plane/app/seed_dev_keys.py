"""Generate development-only secrets. Never use these files in production."""

import base64
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

private = Ed25519PrivateKey.generate().private_bytes(
    serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
)
print("LOCAL_MASTER_KEY_B64=" + base64.b64encode(os.urandom(32)).decode())
print("LOCAL_SIGNING_PRIVATE_KEY_B64=" + base64.b64encode(private).decode())
print("TOKEN_INDEX_KEY_B64=" + base64.b64encode(os.urandom(32)).decode())
