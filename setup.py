#!/usr/bin/python3

from setuptools import setup

setup(
    install_requires=[
        "python-on-whales==0.49.0",
        "python-dateutil",
        "pytz",
        "loguru",
        "jinja2",
        "sultan==0.9.1",
        "plumbum",
        "glom",
        "GitPython==3.1.27",
        "PyYAML==6.0",
        "pip>=21.3",
        "requests>=2.6.1",
        "typer[all]==0.5.0",
        "click==8.1.3",
        "zxcvbn",
        "colorama",
        "tabulate",
        "packaging",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "pytest-timeout",
            "pytest-sugar",
            "freezegun",
            "Faker",
        ]
    },
)
