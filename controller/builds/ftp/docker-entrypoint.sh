#!/bin/bash
set -e

if [[ ! -t 0 ]]; then
    /bin/bash /etc/banner.sh
fi

CERT_FILE="/etc/letsencrypt/real/fullchain1.pem"
KEY_FILE="/etc/letsencrypt/real/privkey1.pem"
DHPARAMS_FILE="/etc/letsencrypt/dhparam.pem"

if [[ -f ${CERT_FILE} ]] && [[ -f ${KEY_FILE} ]]; then
    echo "Enabling SSL"
    cat ${CERT_FILE} ${KEY_FILE} > /etc/ssl/private/pure-ftpd.pem

    if [[ -f ${DHPARAMS_FILE} ]]; then
        cp ${DHPARAMS_FILE} /etc/ssl/private/pure-ftpd-dhparams.pem
    fi
    # -Y / --tls behavior
    # -Y 0 (default) disables SSL/TLS security mechanisms.
    # -Y 1 Accept both normal sessions and SSL/TLS ones.
    # -Y 2 refuses connections that aren't using SSL/TLS security mechanisms,
    #      including anonymous ones.
    # -Y 3 refuses connections that aren't using SSL/TLS security mechanisms,
    #      and refuse cleartext data channels as well.
    export ADDED_FLAGS="${ADDED_FLAGS} --tls=3"
fi

if ! grep "^${FTP_USER}:" /etc/pure-ftpd/passwd/pureftpd.passwd > /dev/null;
then
    echo "User ${FTP_USER} not found, creating it"

    mkdir -p /home/ftpusers/${FTP_USER}
    chown ftpuser:ftpgroup /home/ftpusers/${FTP_USER}
    yes ${FTP_PASSWORD} | pure-pw useradd ${FTP_USER} -f /etc/pure-ftpd/passwd/pureftpd.passwd -m -u ftpuser -d /home/ftpusers/${FTP_USER}

    echo "User ${FTP_USER} successfully created"
fi

# if prod mode and file exists create pure-ftpd.pem
/run.sh -c 50 -C 10 -l puredb:/etc/pure-ftpd/pureftpd.pdb -E -j -R -P $PUBLICHOST -p 30000:30019