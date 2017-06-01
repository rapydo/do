#!/bin/bash

# dev="-r testpypi"
dev=""

# env python3 md2text.py
rm -f dist/*
python3.6 setup.py sdist

version=$(ls -1rt dist | tail -n 1)
twine register dist/$version $dev
twine upload dist/$version $dev

# git add MANIFEST
# git commit -m "releasing $version"
# git push
