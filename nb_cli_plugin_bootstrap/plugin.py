from typing import Optional, cast

import click
from nb_cli.cli import ClickAliasedGroup, cli as cli_, run_async

cli = cast(ClickAliasedGroup, cli_)


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="创建一个更实用的 NoneBot2 初始项目",
)
@click.argument("project-name", required=False, default=None)
@click.option("-y", "--yes", is_flag=True, help="全部使用默认选项")
@click.option("-v", "--verbose", is_flag=True, help="显示更多输出")
@click.option("--venv/--no-venv", default=None, help="指定是否创建虚拟环境")
@click.option(
    "-a",
    "--adapter",
    multiple=True,
    default=[],
    help="指定要安装的适配器名称/包名/模块名",
)
@run_async
async def bootstrap(
    project_name: Optional[str],
    yes: bool,
    verbose: bool,
    venv: Optional[bool],
    adapter: list[str],
):
    from .handlers.bootstrap import bootstrap_handler

    await bootstrap_handler(
        project_name=project_name,
        yes=yes,
        verbose=verbose,
        venv=venv,
        adapters=adapter,
    )


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="更新当前文件夹项目中的所有适配器和插件",
)
@click.option("-y", "--yes", is_flag=True, help="全部使用默认选项")
@click.option("-v", "--verbose", is_flag=True, help="显示更多输出")
@run_async
async def update_project(yes: bool, verbose: bool):
    from .handlers.update_project import update_project_handler

    await update_project_handler(yes=yes, verbose=verbose)


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="更改 pip 使用的 PyPI 镜像源",
)
@click.option("-v", "--verbose", is_flag=True, help="显示更多输出")
@run_async
async def pip_index(verbose: bool):
    from .handlers.pip_index import pip_index_handler

    await pip_index_handler(verbose=verbose)


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="打印进入虚拟环境的命令",
)
@run_async
async def venv():
    from .handlers.venv import venv_handler

    await venv_handler()


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="进入虚拟环境（旧版命令兼容）",
)
@run_async
async def shell():
    from .handlers.shell import shell_handler

    await shell_handler()


def install():
    cli.add_command(bootstrap)
    cli.add_aliases("bootstrap", ["bs"])

    cli.add_command(update_project)
    cli.add_aliases("update-project", ["up"])

    cli.add_command(pip_index)
    cli.add_aliases("pip-index", ["pi"])

    cli.add_command(venv)
    cli.add_aliases("venv", ["vv"])

    cli.add_command(shell)
    cli.add_aliases("shell", ["sh"])
