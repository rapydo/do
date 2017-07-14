# -*- coding: utf-8 -*-

from setuptools import setup
from utilities import __version__
from controller import __package__ as main_package

app = '%s.__main__:main' % main_package

setup(
    name='rapydo_controller',
    version=__version__,
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
        "rapydo-utils==%s" % __version__,
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
    keywords=['http', 'api', 'rest', 'web', 'backend', 'rapydo'],
    # FIXME: import from utils
    author="Paolo D'Onorio De Meo",
    author_email='p.donorio.de.meo@gmail.com',
    # FIXME: import from utils
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
