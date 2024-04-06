from typing import cast

import click
from nb_cli.cli import ClickAliasedGroup, cli as cli_, run_async

from .handlers.bootstrap import bootstrap_handler
from .handlers.pip_index import pip_index_handler
from .handlers.shell import shell_handler
from .handlers.update_project import update_project_handler

cli = cast(ClickAliasedGroup, cli_)


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="创建一个更实用的 NoneBot2 初始项目",
)
@click.option("-y", "--yes", is_flag=True, help="全部使用默认选项")
@click.option("-v", "--verbose", is_flag=True, help="显示更多输出")
@run_async
async def bootstrap(yes: bool, verbose: bool):
    await bootstrap_handler(yes=yes, verbose=verbose)


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="更新当前文件夹项目中的所有适配器和插件",
)
@click.option("-y", "--yes", is_flag=True, help="全部使用默认选项")
@click.option("-v", "--verbose", is_flag=True, help="显示更多输出")
@run_async
async def update_project(yes: bool, verbose: bool):
    await update_project_handler(yes=yes, verbose=verbose)


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="更改 pip 使用的 PyPI 镜像源",
)
@click.option("-v", "--verbose", is_flag=True, help="显示更多输出")
@run_async
async def pip_index(verbose: bool):
    await pip_index_handler(verbose=verbose)


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="进入虚拟环境（需要安装 Poetry）",
)
@run_async
async def shell():
    await shell_handler()


def install():
    cli.add_command(bootstrap)
    cli.add_aliases("bootstrap", ["bs"])

    cli.add_command(update_project)
    cli.add_aliases("update-project", ["up"])

    cli.add_command(pip_index)
    cli.add_aliases("pip-index", ["pi"])

    cli.add_command(shell)
    cli.add_aliases("shell", ["sh"])
