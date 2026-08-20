import base64
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("AUTH_MODE", "dev")
os.environ.setdefault("KEY_PROVIDER", "local")
os.environ.setdefault("FAIL_CLOSED", "true")
os.environ.setdefault("LOCAL_MASTER_KEY_B64", base64.b64encode(b"m" * 32).decode())
os.environ.setdefault(
    "LOCAL_SIGNING_PRIVATE_KEY_B64",
    base64.b64encode(Ed25519PrivateKey.generate().private_bytes_raw()).decode(),
)
os.environ.setdefault("TOKEN_INDEX_KEY_B64", base64.b64encode(b"i" * 32).decode())
os.environ.setdefault("POLICY_DIRECTORY", os.path.join(os.path.dirname(__file__), "..", "policies"))

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory.begin() as session:
        yield session
    await engine.dispose()
