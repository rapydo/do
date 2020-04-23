# -*- coding: utf-8 -*-

from setuptools import setup
from controller.templating import TEMPLATE_DIR

current_version = "0.7.3"

main_package = "controller"
app = '{}.__main__:main'.format(main_package)

setup(
    name='rapydo_controller',
    version=current_version,
    author="Paolo D'Onorio De Meo",
    author_email='p.donorio.de.meo@gmail.com',
    description='Manage and deploy projects based on RAPyDo framework',
    url='https://rapydo.github.io/do',
    license='MIT',
    packages=[main_package],
    package_data={
        main_package: ['argparser.yaml', '{}/*'.format(TEMPLATE_DIR)]
    },
    # End-of-life: 2020-09-13
    python_requires='>=3.5.0',
    entry_points={
        'console_scripts': [
            'rapydo={}'.format(app),
            'do={}'.format(app),
        ],
    },
    install_requires=[
        "docker-compose==1.25.4",
        "dockerfile-parse",
        "python-dateutil",
        "pytz",
        "loguru",
        "prettyprinter",
        "jinja2",
        "sultan==0.9.1",
        "plumbum",
        "glom",
        "gitpython==3.1.0",
        "PyYAML==5.3.1",
        "pip>=10.0.0"

    ],
    keywords=['http', 'api', 'rest', 'web', 'backend', 'rapydo'],
    classifiers=[
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        # End-of-life: 2020-09-13
        'Programming Language :: Python :: 3.5',
        # End-of-life: 2021-12-23
        'Programming Language :: Python :: 3.6',
        # End-of-life: 2023-06-27
        'Programming Language :: Python :: 3.7',
        # End-of-life: 2024-10
        'Programming Language :: Python :: 3.8',
    ]
)
