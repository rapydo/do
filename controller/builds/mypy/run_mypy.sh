#!/bin/bash

set -e

if [[ ! -z "${ADD_LIBS}" ]]; then
	pip3 install ${ADD_LIBS}
fi

MYPY="/tmp/mypy.ini"

echo "[mypy]" > "${MYPY}"
echo "disallow_incomplete_defs = True" >> "${MYPY}"
echo "disallow_any_generics = True" >> "${MYPY}"
echo "disallow_any_unimported = True" >> "${MYPY}"
echo "check_untyped_defs = True" >> "${MYPY}"
echo "warn_redundant_casts = True" >> "${MYPY}"
echo "warn_unused_ignores = True" >> "${MYPY}"
echo "warn_unused_configs = True" >> "${MYPY}"
echo "warn_return_any = True" >> "${MYPY}"
echo "warn_unreachable = True" >> "${MYPY}"
echo "txt_report=/tmp/report" >> "${MYPY}"
echo "html_report=/tmp/report" >> "${MYPY}"
echo "exclude=(?x)(migrations|tests/base/)" >> "${MYPY}"

if [[ "${DISALLOW_UNTYPED_DEFS}" == "1" ]]; then
	echo "disallow_untyped_defs = True" >> "${MYPY}"
	echo "disallow_untyped_calls = True" >> "${MYPY}"
fi

echo "[mypy-neomodel.*]" >> "${MYPY}"
echo "ignore_missing_imports = True" >> "${MYPY}"

echo "[mypy-neo4j.*]" >> "${MYPY}"
echo "ignore_missing_imports = True" >> "${MYPY}"

for lib in $(echo "${IGNORE_LIBS}"); do
	echo "Ignoring: [${lib}]";
    echo "[mypy-${lib}.*]" >> "${MYPY}"
    echo "ignore_missing_imports = True" >> "${MYPY}"
done

cd "/code/${PROJECT_NAME}"

echo "Running mypy..."

mypy --config-file "${MYPY}" . 

cat /tmp/report/index.txt
