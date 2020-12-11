import os

import pytest
from faker import Faker

f = Faker("en_US")

folder = f.file_name(extension="")
os.makedirs(f"{folder}/data/logs")
os.chdir(folder)

print(folder)


@pytest.fixture
def fake():
    return f
