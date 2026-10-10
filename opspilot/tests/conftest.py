import pytest

from opspilot.simulate import generate


@pytest.fixture(scope="session")
def events():
    return generate()
