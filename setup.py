from setuptools import find_packages, setup

version = "2.1"

setup(
    name="rapydo",
    version=version,
    description="Manage and deploy projects based on RAPyDo framework",
    url="https://rapydo.github.io/docs",
    license="MIT",
    packages=find_packages(where=".", exclude=["tests*"]),
    package_data={"controller": ["templates/*", "confs/*", "py.typed"]},
    python_requires=">=3.7.0",
    entry_points={
        "console_scripts": ["rapydo=controller.__main__:main"],
    },
    # Remember to update mypy.additional_dependencies
    install_requires=[
        "python-on-whales==0.32.0",
        "python-dateutil",
        "pytz",
        "loguru",
        "jinja2",
        "sultan==0.9.1",
        "plumbum",
        "glom",
        "GitPython==3.1.24",
        "PyYAML==5.4.1",
        "pip>=10.0.0",
        "requests>=2.6.1",
        "typer[all]==0.4.0",
        "click==8.0.1",
        "zxcvbn",
        "tabulate",
    ],
    extras_require={
        "dev": [
            "setuptools",
            "pytest",
            "pytest-cov",
            "pytest-timeout",
            "pytest-sugar",
            "Faker",
        ]
    },
    keywords=["http", "api", "rest", "web", "backend", "rapydo"],
    classifiers=[
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        # End-of-life: 2023-06-27
        "Programming Language :: Python :: 3.7",
        # End-of-life: 2024-10
        "Programming Language :: Python :: 3.8",
        # End-of-life: 2025-10
        "Programming Language :: Python :: 3.9",
    ],
)
