from nb_cli.cli import cli

from .cli import bootstrap, update_project


def install():
    cli.add_command(bootstrap)
    cli.add_command(update_project)
