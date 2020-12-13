from setuptools import find_packages, setup

version = "0.9"

setup(
    name="rapydo",
    version=version,
    description="Manage and deploy projects based on RAPyDo framework",
    url="https://rapydo.github.io/docs",
    license="MIT",
    packages=find_packages(where=".", exclude=["tests*"]),
    package_data={"controller": ["templates/*", "confs/*"]},
    python_requires=">=3.6.0",
    entry_points={
        "console_scripts": ["rapydo=controller.__main__:main"],
    },
    # Remember to update mypy.additional_dependencies
    install_requires=[
        "docker-compose==1.27.4",
        "dockerfile-parse==1.0.0",
        "python-dateutil",
        "pytz",
        "loguru",
        "prettyprinter",
        "jinja2",
        "sultan==0.9.1",
        "plumbum",
        "glom",
        "GitPython==3.1.11",
        "PyYAML==5.3.1",
        "pip>=10.0.0",
        "typer[all]==0.3.2",
    ],
    keywords=["http", "api", "rest", "web", "backend", "rapydo"],
    classifiers=[
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        # End-of-life: 2021-12-23
        "Programming Language :: Python :: 3.6",
        # End-of-life: 2023-06-27
        "Programming Language :: Python :: 3.7",
        # End-of-life: 2024-10
        "Programming Language :: Python :: 3.8",
    ],
)
