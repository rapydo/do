# -*- coding: utf-8 -*-

from setuptools import setup
# from controller import __version__ as current_version

current_version = "0.7.0"

main_package = "controller"
app = '%s.__main__:main' % main_package

setup(
    name='rapydo_controller',
    version=current_version,
    author="Paolo D'Onorio De Meo",
    author_email='p.donorio.de.meo@gmail.com',
    description='Do development and deploy with the RAPyDo framework',
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
            'rapydo=%s' % app,
            'do=%s' % app,
        ],
    },
    install_requires=[
        # "rapydo-utils==%s" % current_version,
        "docker-compose==1.24.0",
        "dockerfile-parse",
        "python-dateutil",
        "pytz",
        "loguru",
        "better_exceptions",
        "prettyprinter",
        "jinja2",
        "parse_it==3.3.2",
        "sultan==0.9.1",
        # "requests==2.18.4",
        # "requests==2.20.0",
        # unable to update due to docker-compose
        # docker-compose 1.23.2 has requirement
        # requests!=2.11.0,!=2.12.2,!=2.18.0,<2.21,>=2.6.1
        # but you'll have requests 2.21.0 which is incompatible.
        # "requests==2.21.0",
        # Forced because utils requires PyYAML 3.13 but requests 2.20 installs 3.12
        # "PyYAML==3.13",

        "plumbum",
        "glom",
        "gitpython==3.0.2",

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
