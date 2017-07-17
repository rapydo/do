# -*- coding: utf-8 -*-

from setuptools import setup
from controller import \
    __package__ as main_package, \
    __version__ as current_version

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
        main_package: ['argparser.yaml'],
    },
    python_requires='>=3.4',
    entry_points={
        'console_scripts': [
            'rapydo=%s' % app,
            'do=%s' % app,
        ],
    },
    install_requires=[
        "rapydo-utils==%s" % current_version,
        "docker-compose==1.14",
        "docker==2.4.2",
        "dockerfile-parse",
        "gitpython",
        "better_exceptions",
        # necessary for docker-compose
        # https://github.com/docker/compose/issues/4431
        "requests==2.11.1"
    ],
    keywords=['http', 'api', 'rest', 'web', 'backend', 'rapydo'],
    classifiers=[
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
