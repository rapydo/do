import os

import pytest
from faker import Faker

f = Faker("en_US")


# This fixture is execute before every test to create a new random folder
# To execute tests in an insulated environment
@pytest.fixture(autouse=True)
def create_folder() -> None:

    # If you are already in a test folder
    # (this is the case starting from the second test)
    # back to the main folder
    prefix = "0."
    suffix = ".random.test"

    # This is not executed on GithuActions because all tests are exeuted in parallel
    if os.getcwd().endswith(suffix):  # pragma: no cover
        os.chdir("..")

    # Create a new folder with a random name
    folder = f"{prefix}{f.pystr(min_chars=12, max_chars=12)}{suffix}"
    os.makedirs(f"{folder}/data/logs")
    os.chdir(folder)

    print(f"FOLDER = {folder}")


@pytest.fixture
def fake():
    return f
