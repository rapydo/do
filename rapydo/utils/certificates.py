# -*- coding: utf-8 -*-

"""
Using x509 certificates
"""

import os
import re
from OpenSSL import crypto
from plumbum import local
import pytz
import dateutil.parser
from datetime import datetime, timedelta

from rapydo.utils.basher import BashCommands
from rapydo.utils import htmlcodes as hcodes
from rapydo.utils.uuid import getUUID
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


class Certificates(object):

    _dir = os.environ.get('CERTDIR')
    _proxyfile = 'userproxy.crt'

    @classmethod
    def get_dn_from_cert(cls, certdir, certfilename, ext='pem'):

        dn = ''
        cpath = os.path.join(cls._dir, certdir, "%s.%s" % (certfilename, ext))
        content = open(cpath).read()
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, content)
        sub = cert.get_subject()

        for tup in sub.get_components():
            dn += '/' + tup[0].decode() + '=' + tup[1].decode()

        log.verbose("Host DN computed is %s", dn)
        return dn

    @classmethod
    def get_proxy_filename(cls, user, dir=False):
        if dir:
            return "%s/%s" % (cls._dir, user)
        return "%s/%s/%s" % (cls._dir, user, cls._proxyfile)

    def save_proxy_cert(self, tmpproxy, user='guest'):

        import os
        directory = self.get_proxy_filename(user, dir=True)
        if not os.path.exists(directory):
            os.mkdir(directory)

        dst = self.get_proxy_filename(user)

        from shutil import copyfile
        copyfile(tmpproxy, dst)

        os.chmod(dst, 0o600)  # note: you need the octave of the unix mode

        return dst

    def encode_csr(self, req):
        enc = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        data = {'certificate_request': enc}
        return data

    @staticmethod
    def generate_csr_and_key(user='TestUser'):
        """
        TestUser is the user proposed by the documentation,
        which will be ignored
        """
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)
        req = crypto.X509Req()
        req.get_subject().CN = user
        req.set_pubkey(key)
        req.sign(key, "sha1")
        # print("CSR", key, req)
        return key, req

    def write_key_and_cert(self, key, cert):
        proxycertcontent = cert.decode()
        if proxycertcontent is None or proxycertcontent.strip() == '':
            return None
        tempfile = "/tmp/%s" % getUUID()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        with os.fdopen(os.open(tempfile, flags, 0o600), 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key).decode())
            f.write(proxycertcontent)
        return tempfile

    def proxy_from_ca(self, ca_client, prod=False):
        """
        Request for certificate and save it into a file

        NOTE: insecure ssl context is required with b2access dev,
        because they do not have a valid HTTPS certificate for development
        """

        if not prod:
            # INSECURE SSL CONTEXT.
            # source: http://stackoverflow.com/a/28052583/2114395
            import ssl
            ssl._create_default_https_context = \
                ssl._create_unverified_context

        #######################
        key, req = self.generate_csr_and_key()
        # log.debug("Key and Req:\n%s\n%s" % (key, req))

        #######################
        response = None
        try:
            response = ca_client.post(
                'ca/o/delegateduser',
                data=self.encode_csr(req),
                headers={'Accept-Encoding': 'identity'})
            # Note: token is applied from oauth2 lib using the session content
        except ValueError as e:
            log.error("Oauthlib call with CA: %s" % e)
            return None
        except Exception as e:
            # TODO: expand this case
            # 1. CA is unreachable (internet)
            # 2. CA says the token is invalid
            log.error("CA is probably down... [%s]" % e)
            return None

        if response.status != hcodes.HTTP_OK_BASIC:
            # print("\nCertificate:"); log.pp(response)
            log.error("Could not get proxy from CA: %s" % response.data)
            return None
        # log.pp(response)

        #######################
        # write proxy certificate to a random file name
        proxyfile = self.write_key_and_cert(key, response.data)
        log.debug('Wrote certificate to %s' % proxyfile)

        return proxyfile

    @classmethod
    def check_cert_validity(cls, certfile, validity_interval=1):
        args = ["x509", "-in", certfile, "-text"]

        bash = BashCommands()
        output = bash.execute_command("openssl", args)

        pattern = re.compile(
            r"Validity.*\n\s*Not Before: (.*)\n" +
            r"\s*Not After *: (.*)")
        validity = pattern.search(output).groups()

        not_before = dateutil.parser.parse(validity[0])
        not_after = dateutil.parser.parse(validity[1])
        now = datetime.now(pytz.utc)
        valid = \
            (not_before < now) and \
            (not_after > now - timedelta(hours=validity_interval))

        return valid, not_before, not_after

    @classmethod
    def get_myproxy_certificate(cls, irods_env,
                                irods_user, myproxy_cert_name, irods_cert_pwd,
                                proxy_cert_file,
                                duration=168,
                                myproxy_host="grid.hpc.cineca.it"
                                ):
        try:
            myproxy = local["myproxy-logon"]
            if irods_env is not None:
                myproxy = myproxy.with_env(**irods_env)

            # output = (myproxy["-s", myproxy_host, "-l", irods_user, "-k", myproxy_cert_name, "-t", str(duration), "-o", proxy_cert_file, "-S"] << irods_cert_pwd)()
            # log.critical(output)
            (
                myproxy[
                    "-s", myproxy_host,
                    "-l", irods_user,
                    "-k", myproxy_cert_name,
                    "-t", str(duration),
                    "-o", proxy_cert_file,
                    "-S"
                ] << irods_cert_pwd
            )()

            return True
        except Exception as e:
            log.error(e)
            return False
