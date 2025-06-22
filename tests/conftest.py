from typing import Any, Dict
from uuid import UUID, uuid4

import pytest


@pytest.fixture
def sample_uuid() -> UUID:
    """Provides a consistent UUID for testing."""
    return UUID("12345678-1234-5678-9abc-123456789abc")


@pytest.fixture
def sample_name() -> str:
    """Provides a consistent name for testing."""
    return "test_entity"


@pytest.fixture
def sample_device_properties() -> Dict[str, Any]:
    """Provides sample device properties for testing."""
    return {
        "value": 42.5,
        "min": 0.0,
        "max": 100.0,
        "label": "Test Sensor",
        "unit": "°C"
    }


@pytest.fixture
def random_uuid() -> UUID:
    """Provides a random UUID for each test."""
    return uuid4()


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "simulation: marks tests as simulation tests")
    config.addinivalue_line("markers", "hardware: marks tests as hardware tests (may require physical hardware)")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
