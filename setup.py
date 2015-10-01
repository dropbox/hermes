#!/usr/bin/env python

import os

from setuptools import find_packages
from distutils.core import setup

execfile('hermes/version.py')

with open('requirements.txt') as requirements:
    required = requirements.read().splitlines()

package_data = {}
def get_package_data(package, base_dir):
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirpath = dirpath[len(package)+1:]  # Strip package dir
        for filename in filenames:
            package_data.setdefault(package, []).append(os.path.join(dirpath, filename))
        for dirname in dirnames:
            get_package_data(package, dirname)

get_package_data("hermes", "hermes/webapp/build")
get_package_data("hermes", "hermes/templates")

kwargs = {
    "name": "hermes",
    "version": str(__version__),
    "packages": find_packages(exclude=['tests']),
    "package_data": package_data,
    "scripts": ["bin/hermes-server", "bin/hermes", "bin/hermes-notify"],
    "description": "Hermes Event Management and Autotasker",
    "author": "Digant C Kasundra",
    "maintainer": "Digant C Kasundra",
    "author_email": "digant@dropbox.com",
    "maintainer_email": "digant@dropbox.com",
    "license": "Apache",
    "install_requires": required,
    "url": "https://github.com/dropbox/hermes",
    "download_url": "https://github.com/dropbox/hermes/archive/master.tar.gz",
    "classifiers": [
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
}

setup(**kwargs)
