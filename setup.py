from setuptools import find_packages, setup

version = "2.2"

setup(
    name="rapydo",
    version=version,
    description="Manage and deploy projects based on RAPyDo framework",
    url="https://rapydo.github.io/docs",
    license="MIT",
    packages=find_packages(where=".", exclude=["tests*"]),
    package_data={"controller": ["templates/*", "confs/*", "py.typed"]},
    python_requires=">=3.8.0",
    entry_points={
        "console_scripts": ["rapydo=controller.__main__:main"],
    },
    # Remember to update mypy.additional_dependencies
    install_requires=[
        "python-on-whales==0.36.1",
        "python-dateutil",
        "pytz",
        "loguru",
        "jinja2",
        "sultan==0.9.1",
        "plumbum",
        "glom",
        "GitPython==3.1.25",
        "PyYAML==6.0",
        "pip>=10.0.0",
        "requests>=2.6.1",
        "typer[all]==0.4.0",
        "click==8.0.4",
        "zxcvbn",
        "tabulate",
        "packaging",
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
        # End-of-life: 2024-10
        "Programming Language :: Python :: 3.8",
        # End-of-life: 2025-10
        "Programming Language :: Python :: 3.9",
        # End-of-life: 2026-10
        "Programming Language :: Python :: 3.10",
    ],
)
