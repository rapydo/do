
# RAPyDo controller 

(a.k.a. `do`)

Do things with RAPyDo ecosystem

---

## The project

Welcome to our new `RAPyDo` framework.

This project is based on Flask and aims at making easy for a web developer
to write Python code on his own HTTP-API;

Forget about the difficult setup of the server, authentication,
plugin of services, testing connections, documenting your endpoints
and injecting components into Flask.

## Requirements

This component is written and tested with `Python 3.4+`.
All bash commands below are using `pip3` as a reference for `pip` installed with Python3.

Before starting you have to make sure to install:

- python 3
- pip 3
- docker
- git

## Install the controller

Use the official python package manager:

```bash
$ pip3 install --upgrade rapydo-controller
```

## Use it on your REST API project

This controller works only on a [RAPyDo compliant](https://github.com/rapydo) repository.
Clone or fork the core framework to start your project:

```bash
$ git clone https://github.com/rapydo/core.git

$ rapydo check
$ rapydo -h
```

## Developers

Do you want to partecipate?

Well, you are very welcome here! `^_^`

### Become a developer

Clone and install in 'development' mode:

```bash
$ git clone https://github.com/rapydo/do.git
$ pip3 install --no-cache-dir --upgrade --editable .
```

Now you can start developing your patch.

### Release a new version

1. change version inside the file `rapydo/do/__init__.py`
2. build and publish in testing

The latter can be done with the command:

```bash
$ pip3 install -r dev-requirements.txt
$ ./make
```

Note! The last command expects you to 

- being registered on PyPi
- have a `~/.pypirc` file configured
- know what you're doing `:D`
