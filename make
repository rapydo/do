#!/bin/bash

if [ "$1" == 'prod' ]; then
	# OR PRODUCTION
	dev=""
else
	# DEVELOPMENT
	dev="-r testpypi"
fi

git update-index --assume-unchanged README.rst
# pip3 install --upgrade -r dev-requirements.txt
pandoc \
	--from=markdown --to=rst \
	--output=README.rst README.md

# rm -f dist/*
python3.6 setup.py sdist

version=$(ls -1rt dist | tail -n 1)
twine register dist/$version $dev
twine upload dist/$version $dev

if [ "$2" == 'bump' ]; then
	git add *
	git commit -m "Bump to release $version"
	git push
fi
