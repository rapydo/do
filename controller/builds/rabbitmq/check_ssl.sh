#!/bin/bash
set -e

# Mostly equal to check_ssl.sh script in neo4j build
function verify_ssl_files {

    if [[ -z "${1}" ]];
    then
        echo "SSL not enabled";
    elif [[ ! -f "${1}" ]];
    then
        echo "SSL mandatory file not found: ${1}"
        echo "If you are already starting a proxy container, just wait for the installation of SSL certificates to be completed"
        echo "If you do not have a proxy container running on this host, you can create SSL certificates with the command: rapydo ssl --volatile"
        echo "This check will be automatically re-tried in a few seconds..."
        echo ""
        exit 1
    else
        echo "File ${1} verified";
    fi

}

verify_ssl_files ${SSL_CACERTFILE}
verify_ssl_files ${SSL_CERTFILE}
verify_ssl_files ${SSL_KEYFILE}

