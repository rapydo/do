# -*- coding: utf-8 -*-

import yaml
import os
# from functools import lru_cache
from do.utils.logs import get_logger
log = get_logger(__name__)

YAML_EXT = 'yaml'
# Test the library
yaml.dump({})


# @lru_cache()
def load_yaml_file(file, path=None, get_all=False, skip_error=False):
    """
    Import data from a YAML file.
    Reading is cached.
    """

    error = None
    if path is None:
        filepath = file
    else:
        filepath = os.path.join(path, file + "." + YAML_EXT)
    log.very_verbose("Reading file %s" % filepath)

    # load from this file
    if os.path.exists(filepath):
        with open(filepath) as fh:
            try:
                # LOAD fails if more than one document is there
                # return yaml.load(fh)
                # LOAD ALL gets more than one document inside the file
                gen = yaml.load_all(fh)
                docs = list(gen)
                if get_all:
                    return docs
                else:
                    if len(docs) > 0:
                        return docs[0]
                    else:
                        raise AttributeError("Missing YAML first document")
            except Exception as e:
                error = e
    else:
        error = 'File does not exist'

    message = "Failed to read YAML from '%s': %s" % (filepath, error)
    if skip_error:
        log.warning(message)
    else:
        raise Exception(message)
    return None
