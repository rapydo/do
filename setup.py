# -*- coding: utf-8 -*-

"""
RAPyDo controller
-----

Welcome to our new RAPyDo framework.

This project is based on Flask and aims at making easy for a web developer
to write Python code on his own HTTP-API;
Forget about the difficult setup of the server, authentication,
plugin of services, testing connections, documenting your endpoints
and injecting components into Flask.

How to start
````````````

.. code:: bash

    $ pip install rapydo-controller
    $ rapydo


Links
`````
* `github <http://github.com/rapydo>`_
"""

from distutils.core import setup
from rapydo.do import __version__

setup(
    name='rapydo_controller',
    description='Makes you do REST API development with the RAPyDo framework',
    version=__version__,
    author="Paolo D'Onorio De Meo",
    author_email='p.donorio.de.meo@gmail.com',
    url='https://github.com/rapydo/do',
    license='MIT',
    packages=[
        # 'rapydo',
        'rapydo.do',
        'rapydo.utils'
    ],
    package_data={
        'rapydo.do': [
            'argparser.yaml'
        ],
        'rapydo.utils': [
            'logging.ini'
        ]
    },
    python_requires='>=3.4',
    entry_points={
        'console_scripts': [
            'rapydo=rapydo.do.__main__:main',
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
        "pytz"
    ],
    classifiers=[
        'Programming Language :: Python',
        'Intended Audience :: Developers',
    ],
    keywords=['http', 'api', 'rest', 'web', 'backend']
    # download_url='https://github.com/author/repo/tarball/1.0',
)
