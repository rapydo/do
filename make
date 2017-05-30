#!/bin/bash

## remove existing?
# rm -f dist/*

python3.6 setup.py sdist

version=$(ls -1rt dist | tail -n 1)

twine register dist/$version -r testpypi

twine upload dist/$version -r testpypi
