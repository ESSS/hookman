#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages, setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['Click>=6.0', 'strictyaml', 'invoke', 'attrs']

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

setup(
    author="ESSS",
    author_email='foss@esss.co',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
    ],
    description="A hook manager in python that enables cpp applications call dlls in C/C++",
    entry_points={
        'console_scripts': [
            'hookman=hookman.cli:main',
        ],
    },
    extras_require={
        'docs': [ 'sphinx >= 1.4', 'sphinx_rtd_theme', 'sphinx-autodoc-typehints']
        },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='hookman',
    name='hookman',
    packages=find_packages(include=['hookman']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/esss/hookman',
    version='0.1.0',
    zip_safe=False,
)
