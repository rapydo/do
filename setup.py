# -*- coding: utf-8 -*-

"""
My first Pypi package test

example of versions:
1.2.0 .dev1/.a1/.b1/.rc1/FINAL/.post1

"""

from distutils.core import setup

setup(
    name='rapydo_do',
    packages=[
        'do'
        # 'rapydo'
    ],
    python_requires='>=3.4',
    description='Makes you do REST API development with the RAPyDo framework',
    version='0.1.dev1',
    license='MIT',
    author="Paolo D'Onorio De Meo",
    author_email='p.donorio.de.meo@gmail.com',
    url='https://github.com/rapydo/do',
    keywords=['http', 'api', 'rest', 'web', 'backend'],
    # download_url='https://github.com/author/repo/tarball/1.0',
    entry_points={
        'console_scripts': [
            'rapydo=do.__main__:main',
        ],
    },
    install_requires=[
        "requests==2.11.1",
        "docker",
        "docker-compose>=1.13",
        "gitpython",
        "dockerfile-parse",
        "beeprint",
        "better_exceptions",
    ],
    classifiers=[
        'Programming Language :: Python',
        'Intended Audience :: Developers',
    ]
)
