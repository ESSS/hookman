# -*- coding: utf-8 -*-

"""Console script for hookman."""
import sys

import click


@click.command()
@click.argument('specs_path', type=click.Path(exists=True))
@click.option('--dst-path', default='./', help='Path to where the files will be destined')
def main(specs_path, dst_path):
    """
    This task will invoke a code generation to produce the following files:
        - hook_specs.h - `File to be used by the plugin implementation`
        - HookCaller.hpp - `File to be passed to the application`
        - HookCallerPython.cpp - `Bindings for the function available on the plugin implementation`

    In order to call this command is necessary to inform the hook_specs.py file that has the
    specifications of the hooks available, and the destination path, (where the files will be created).

    Per default dst-path is the same directory that the command is called.

    Example:
    > hookman /<some_dir>/hook_specs.py --dst-path=/home/<some_other_path>
    """

    from pathlib import Path
    from hookman.hookman_generator import HookManGenerator

    hook_specs_path = Path(specs_path)
    hm_generator = HookManGenerator(hook_spec_file_path=hook_specs_path)
    hm_generator.generate_project_files(Path(dst_path))

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
