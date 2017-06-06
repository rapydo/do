# -*- coding: utf-8 -*-
"""
    Command line script main
"""

from rapydo.do.app import Application
import better_exceptions as be


def main():
    be  # activate better exceptions
    Application()


if __name__ == '__main__':
    main()
