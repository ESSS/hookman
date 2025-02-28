Releasing procedure
-------------------

Make sure all your changes are committed (including an entry in HISTORY.rst).
Then run::

$ git tag vX.Y.Z (where the X.Y.Z numbers should follow the semantic versioning, for more details read https://semver.org/)
$ git push
$ git push --tags

Travis will then deploy to PyPI if tests pass.
