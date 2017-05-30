# -*- coding: utf-8 -*-

import yaml
import os
# from functools import lru_cache

YAML_EXT = 'yaml'
# Test the library
yaml.dump({})


# @lru_cache()
def load_yaml_file(file, path=None,
                   get_all=False, skip_error=False,
                   extension=YAML_EXT, return_path=False, logger=True):
    """
    Import data from a YAML file.
    """

    if logger:
        from rapydo.utils.logs import get_logger
        log = get_logger(__name__)

    error = None
    if path is None:
        filepath = file
    else:
        filepath = os.path.join(path, file + "." + extension)

    if not return_path and logger:
        # TODO: add CHECKED
        log.verbose("Reading file %s" % filepath)

    # load from this file
    if os.path.exists(filepath):
        if return_path:
            return filepath

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
                        message = "YAML file is empty %s" % filepath
                        if logger:
                            log.critical_exit(message)
                        else:
                            raise AttributeError(message)
            except Exception as e:
                error = e
    else:
        error = 'File does not exist'

    # # IF dealing with a strange exception string (escaped)
    # import codecs
    # mystring, _ = codecs.getdecoder("unicode_escape")(str(error))
    # message = "Failed to read YAML file [%s]: %s" % (filepath, mystring)

    message = "Failed to read YAML file [%s]: %s" % (filepath, error)

    if skip_error:
        if logger:
            log.warning(message)
        else:
            raise NotImplementedError("Cannot log warning %s" % message)
    else:
        if logger:
            log.warning(message)
        else:
            raise AttributeError(message)
    return {}
