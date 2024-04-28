#!/bin/bash

if [ "${SSL_VERIFY_CLIENT}" == "1" ] || [ "${SSL_VERIFY_CLIENT}" == "on" ]; then
    echo "Reloading of client certificates not implemented yet"
fi

echo "Reloading nginx..."
nginx -s reload