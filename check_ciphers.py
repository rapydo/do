from pathlib import Path

import requests
from bs4 import BeautifulSoup  # type: ignore
from loguru import logger as log

nginx_header = "controller/builds/proxy/confs/production.conf"

with open(nginx_header) as headers:
    for line in headers.readlines():
        line = line.strip()
        if not line.startswith("ssl_ciphers"):
            continue
        line = line.removeprefix('ssl_ciphers "')
        line = line.removesuffix('";')

        ciphers = line.split(":")
        for cipher in ciphers:
            if cipher.startswith("!"):
                continue

            page = requests.get(
                f"https://ciphersuite.info/search/?q={cipher}", timeout=30
            )
            soup = BeautifulSoup(page.content, "html5lib")
            # Results are organized on a ul class='prettylist'
            ul = soup.find("ul", attrs={"class": "prettylist"})
            # Find all the <a> into the ul
            a_list = ul.findChildren("a")

            for a in a_list:
                # The <a> content has a lot of thinghs, in particular
                # multiple spaces to be removed:
                text = " ".join(a.text.split())
                # After removing all the multiple spaces
                # only two words space-separated will remain
                # text_split == the level (Recommended, Secure, Weak, etc)
                # Recommended == the cipher
                text_split = text.split(" ")

                # The href points to the detail page where the IANA name can be found
                # that is the same used by ssllab
                # Convert the href to a path to take the last part
                iana_name = Path(a["href"]).name
                if text_split[1] == cipher:
                    level = text_split[0]
                    if level == "Recommended":
                        log.info(f"{cipher: <30} {iana_name: <45} {level}")
                    elif level == "Secure":
                        log.info(f"{cipher: <30} {iana_name: <45} {level}")
                    elif level == "Weak":
                        log.warning(f"{cipher: <30} {iana_name: <45} {level}")
                    else:
                        log.error(f"{cipher: <30} {iana_name: <45} {level}")
                    break
            else:
                log.error("{} not found on ciphersuite", cipher)
