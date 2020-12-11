import os

# import pytest
from faker import Faker

f = Faker("en_US")

folder = f.file_name(extension="test")
os.makedirs(f"{folder}/data/logs")
os.chdir(folder)

print(f"FOLDER = {folder}")


# @pytest.fixture
# def fake():
#     return f
