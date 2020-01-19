# -*- coding: utf-8 -*-

from setuptools import setup
# from controller import __version__ as current_version

current_version = "0.7.1"

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
        main_package: [
            'argparser.yaml',
            'templates/class.py',
            'templates/get.yaml',
            'templates/specs.yaml',
            'templates/unittests.py',
        ],
    },
    python_requires='>=3.4.3',
    entry_points={
        'console_scripts': [
            'rapydo={}'.format(app),
            'do={}'.format(app),
        ],
    },
    install_requires=[
        "docker-compose==1.25.1-rc1",
        "dockerfile-parse",
        "python-dateutil",
        "pytz",
        "loguru",
        "better_exceptions",
        "prettyprinter",
        "jinja2",
        "sultan==0.9.1",
        # "requests==2.21.0",
        # "PyYAML==3.13",
        "plumbum",
        "glom",
        "gitpython==3.0.5",
        "pip>=10.0.0"

    ],
    keywords=['http', 'api', 'rest', 'web', 'backend', 'rapydo'],
    classifiers=[
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
