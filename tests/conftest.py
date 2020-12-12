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
    suffix = ".random.test"
    if os.getcwd().endswith(suffix):
        os.chdir("..")

    # Create a new folder with a random name
    folder = f"{f.pystr(min_chars=16, max_chars=16)}{suffix}"
    os.makedirs(f"{folder}/data/logs")
    os.chdir(folder)

    print(f"FOLDER = {folder}")


@pytest.fixture
def fake():
    return f
