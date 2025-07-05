#!/usr/bin/env python

import argparse
import re
import sys
from setuptools_scm import get_version

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--alpha", action="store_true")
DEPLOY_VERSION = r"\d+\.\d+\.\d+"
ALPHA_VERSION = DEPLOY_VERSION + r"a\d+"
args = parser.parse_args()
if args.alpha:
    print("checking alpha release")
    parser = ALPHA_VERSION
else:
    print("checking Final release.")
    parser = DEPLOY_VERSION

version = get_version()
print(f"version = {version}")
if not re.fullmatch(parser, version):
    exit(1)
exit(0)
