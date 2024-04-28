#!/bin/ash
set -e

if [[ -z $REGISTRY_HOST ]];
then
    echo "Invalid registry host"
    exit 1
fi

if [[ -z $REGISTRY_USERNAME ]];
then
    echo "Invalid registry username"
    exit 1
fi

if [[ -z $REGISTRY_PASSWORD ]];
then
    echo "Invalid registry password"
    exit 1
fi

htpasswd -Bbn "${REGISTRY_USERNAME}" "${REGISTRY_PASSWORD}" > /auth

if [[ ! -f ${REGISTRY_HTTP_TLS_KEY} || ! -f ${REGISTRY_HTTP_TLS_CERTIFICATE} ]];
then

    echo -e """[req]
default_bits = 4096
default_md = sha256
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no
[req_distinguished_name]
C = XX
ST = XX
L = XXX
O = NoCompany
OU = Organizational_Unit
CN = ${REGISTRY_HOST}
[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
IP.1 = ${REGISTRY_HOST}
""" > /tmp/config.ini
    openssl req -newkey rsa:4096 -nodes -sha256 -keyout ${REGISTRY_HTTP_TLS_KEY} -x509 -days 365 -config /tmp/config.ini -out ${REGISTRY_HTTP_TLS_CERTIFICATE} -subj '/CN=*/'
fi