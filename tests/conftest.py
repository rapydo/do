import os

import pytest
from faker import Faker

f = Faker("en_US")


@pytest.fixture(autouse=True)
def create_folder() -> None:

    folder = f.pystr(min_chars=16, max_chars=16)
    os.makedirs(f"{folder}/data/logs")
    os.chdir(folder)

    print(f"FOLDER = {folder}")
    print(f"CWD = {os.getcwd()}")


# @pytest.fixture
# def fake():
#     return f
