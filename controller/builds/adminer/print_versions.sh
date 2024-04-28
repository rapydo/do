#!/bin/bash
echo "Adminer ${ADMINER_VERSION} $(nginx -v 2>&1 | sed 's/nginx version: //')"
