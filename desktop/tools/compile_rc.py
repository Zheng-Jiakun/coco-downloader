#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyQt5 Resource Compiler Wrapper
Usage: python compile_rc.py input.qrc -o output.py
"""
import sys
from PyQt5.pyrcc_main import processResourceFile

if __name__ == '__main__':
    sys.exit(processResourceFile(sys.argv[1:]))
