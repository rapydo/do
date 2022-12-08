#!/bin/bash
set -e

CONF="/etc/rabbitmq/rabbitmq.conf"

echo "loopback_users.guest = false" >> ${CONF}
echo "default_user = ${DEFAULT_USER}" >> ${CONF}
echo "default_pass = ${DEFAULT_PASS}" >> ${CONF}
echo "consumer_timeout = 31622400000" >> ${CONF}

if [[ ! -z $SSL_KEYFILE ]];
then
    echo "listeners.ssl.default = ${RABBITMQ_PORT}" >> ${CONF}
    echo "ssl_options.keyfile = ${SSL_KEYFILE}" >> ${CONF}
    echo "ssl_options.certfile = ${SSL_CERTFILE}" >> ${CONF}
    echo "ssl_options.cacertfile = ${SSL_CACERTFILE}" >> ${CONF}
    echo "ssl_options.fail_if_no_peer_cert = ${SSL_FAIL_IF_NO_PEER_CERT}" >> ${CONF}
    echo "management.ssl.port = ${RABBITMQ_MANAGEMENT_PORT}" >> ${CONF}
    echo "management.ssl.keyfile = ${SSL_KEYFILE}" >> ${CONF}
    echo "management.ssl.certfile = ${SSL_CERTFILE}" >> ${CONF}
    echo "management.ssl.cacertfile = ${SSL_CACERTFILE}" >> ${CONF}
    echo "management.ssl.fail_if_no_peer_cert = ${SSL_FAIL_IF_NO_PEER_CERT}" >> ${CONF}
else
    echo "listeners.tcp.default = ${RABBITMQ_PORT}" >> ${CONF}
    echo "management.tcp.port = ${RABBITMQ_MANAGEMENT_PORT}" >> ${CONF}
fi
