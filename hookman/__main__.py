# -*- coding: utf-8 -*-

"""Console script for hookman."""
import sys
from pathlib import Path

import click
from hookman.hookman_generator import HookManGenerator


@click.group()
def cli():
    pass


@cli.command()
@click.argument('specs_path', type=click.Path(exists=True))
@click.option('--dst-path', default='./', help='Path to where the files will be written')
def generate_project_files(specs_path, dst_path):
    """
    Generate hooks_pecs.h, HookCaller c++ class and bindings.

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
    hm_generator = HookManGenerator(hook_spec_file_path=specs_path)
    hm_generator.generate_project_files(Path(dst_path))
    return 0


@cli.command()
@click.argument('specs_path', type=click.Path(exists=True))
@click.argument('caption')
@click.argument('plugin_id')
@click.argument('author_name')
@click.argument('author_email')
@click.option('--dst-path', default='./', help='Path to where the files will be written')
def generate_plugin_template(
        specs_path: str,
        caption: str,
        plugin_id: str,
        author_email: str,
        author_name: str,
        dst_path: Path):
    """Generate a plugin starting template."""
    hm_generator = HookManGenerator(hook_spec_file_path=specs_path)
    hm_generator.generate_plugin_template(
        caption=caption,
        plugin_id=plugin_id,
        author_email=author_email,
        author_name=author_name,
        dst_path=Path(dst_path))
    return 0


@cli.command()
@click.argument('specs_path', type=click.Path(exists=True))
@click.argument('package_name')
@click.argument('plugin_dir')
@click.option('--dst-path', default='./', help='Path to where the files will be written')
def package_plugin(specs_path: str, package_name: str, plugin_dir: str, dst_path: Path):
    """Packages a plugin for distribution."""
    hm_generator = HookManGenerator(hook_spec_file_path=specs_path)
    hm_generator.generate_plugin_package(
        package_name=package_name,
        plugin_dir=plugin_dir,
        dst_path=Path(dst_path))
    return 0


@cli.command()
@click.argument('specs_path', type=click.Path(exists=True))
@click.argument('plugin_id')
@click.option('--dst-path', default='./', help='Path to where the files will be written')
def generate_hook_specs_h(specs_path: str, plugin_id: str, dst_path: Path):
    """Generates or update the hook_specs.h header file."""
    hm_generator = HookManGenerator(hook_spec_file_path=specs_path)
    hm_generator.generate_hook_specs_header(
        plugin_id=plugin_id,
        dst_path=Path(dst_path))
    return 0


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
