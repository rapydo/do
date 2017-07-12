# -*- coding: utf-8 -*-

import os
import codecs
from rapydo.do import __version__

# from distutils.core import setup
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()


setup(
    name='rapydo_controller',
    version=__version__,
    description='Do development and deploy with the RAPyDo framework',
    # long_description=__doc__,
    long_description=read('README.rst'),
    # keywords='http api rest web backend rapydo',
    # keywords=['http', 'api', 'rest', 'web', 'backend', 'rapydo'],
    author="Paolo D'Onorio De Meo",
    author_email='p.donorio.de.meo@gmail.com',
    url='https://github.com/rapydo/do',
    license='MIT',
    packages=['rapydo.do'],
    package_data={
        'rapydo.do': ['argparser.yaml'],
    },
    python_requires='>=3.4',
    entry_points={
        'console_scripts': [
            'rapydo=rapydo.do.__main__:main',
            'do=rapydo.do.__main__:main',
        ],
    },
    install_requires=[
        # "rapydo-utils==0.5.0",
        "rapydo-utils==0.4.7",
        # ###### DOCKER
        # combo that works
        "docker-compose==1.14",
        "docker==2.4.2",
        "dockerfile-parse",
        # ###### others
        "gitpython",
        "better_exceptions",
        # ###### BUG FIX
        "requests==2.11.1",
        # requests==2.18.1 # otherwise it goes with this, which break things
    ],
    classifiers=[
        'Programming Language :: Python',
        'Intended Audience :: Developers',
    ]
)
