import pytest
from k360_token_python import pub_key_utils as pk_utils

@pytest.fixture(autouse=True)
def reset_public_key_manager():
    """Automatically resets PublicKeyManager before every test."""

    pk_utils.public_key_manager.reset()
    yield
    pk_utils.public_key_manager.reset()