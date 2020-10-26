#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages, setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["Click>=7.0", "strictyaml", "invoke", "attrs"]

setup(
    author="ESSS",
    author_email="foss@esss.co",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="HookMan is a python package that provides a plugin management system to applications, specially those who are written (in totally or partially) in C++.",
    entry_points={"console_scripts": ["hookman=hookman.__main__:cli"]},
    extras_require={"docs": ["sphinx >= 1.4", "sphinx_rtd_theme", "sphinx-autodoc-typehints"]},
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/x-rst",
    include_package_data=True,
    keywords="hookman",
    name="python-hookman",
    packages=find_packages(include=["hookman"]),
    url="https://github.com/esss/hookman",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    zip_safe=False,
)
