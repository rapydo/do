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

from rapydo.do import __version__

from distutils.core import setup
# from setuptools import setup

#################
# FIXME: use it or not? from pip code:

# # import os
# # import codecs

# # def read(*parts):
# #     here = os.path.abspath(os.path.dirname(__file__))
# #     return codecs.open(os.path.join(here, *parts), 'r').read()

# # long_description = read('README.rst')


#################
setup(
    name='rapydo_controller',
    description='Do development and deploy with the RAPyDo framework',
    long_description=__doc__,
    version=__version__,
    author="Paolo D'Onorio De Meo",
    author_email='p.donorio.de.meo@gmail.com',
    url='https://github.com/rapydo/do',
    license='MIT',
    packages=[
        'rapydo.do',
    ],
    package_data={
        'rapydo.do': [
            'argparser.yaml'
        ],
    },
    python_requires='>=3.4',
    entry_points={
        'console_scripts': [
            'rapydo=rapydo.do.__main__:main',
        ],
    },
    install_requires=[
        "rapydo-utils",
        "requests==2.11.1",
        "docker",
        "docker-compose>=1.13",
        "gitpython",
        "dockerfile-parse",
        "better_exceptions"
    ],
    # tests_require=[  # from PIP code
    #     'pytest',
    #     'mock',
    #     'pretend',
    #     'scripttest>=1.3',
    #     'virtualenv>=1.10',
    #     'freezegun',
    # ],
    # extras_require={
    #     'testing': tests_require,
    # },
    classifiers=[
        'Programming Language :: Python',
        'Intended Audience :: Developers',
    ],
    keywords=['http', 'api', 'rest', 'web', 'backend', 'rapydo'],
    zip_safe=False,
)
