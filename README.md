# do
Do things with RAPyDo ecosystem

---

## Install

Use the official python package manager

```bash
$ pip3 install --upgrade rapydo-controller
```

## Use it on your REST API project

```bash
# clone/fork rapydo framework and use it
$ git clone https://github.com/rapydo/core.git
$ rapydo check
$ rapydo -h
```

## Developers

Do you want to partecipate?

You are very welcome! `^_^`

### Become a developer

```bash
# clone and install in 'development' mode
$ git clone https://github.com/rapydo/do.git
$ pip3 install --no-cache-dir --upgrade --editable .
```

Now you can start developing your patch.

### Release a new version

1. change version inside the file `rapydo/do/__init__.py`
2. build and publish in testing with

```bash
./make
```

Note: this action expects you to: 

- being registered on PyPi
- have a `~/.pypirc` file configured
- know what you're doing `:D`
