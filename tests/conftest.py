import os

import pytest
from faker import Faker

f = Faker("en_US")


@pytest.fixture(autouse=True)
def create_folder():

    folder = f.file_name(extension="test")
    os.makedirs(f"{folder}/data/logs")
    os.chdir(folder)

    print(f"FOLDER = {folder}")
    print(f"CWD = {os.getcwd()}")


# @pytest.fixture
# def fake():
#     return f
