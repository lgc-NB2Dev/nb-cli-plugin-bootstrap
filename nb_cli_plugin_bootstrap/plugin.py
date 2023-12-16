import click
from nb_cli.cli import ClickAliasedGroup, cli, run_async

from .handlers.bootstrap import bootstrap_handler
from .handlers.update_project import update_project_handler


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="创建一个更实用的 NoneBot2 初始项目",
)
@click.option("-y", "--yes", is_flag=True, help="全部使用默认选项")
@run_async
async def bootstrap(yes: bool):
    await bootstrap_handler(yes=yes)


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="更新当前文件夹项目中的所有适配器和插件",
)
@click.option("-y", "--yes", is_flag=True, help="全部使用默认选项")
@run_async
async def update_project(yes: bool):
    await update_project_handler(yes=yes)


def install():
    cli.add_command(bootstrap)
    cli.add_command(update_project)
    cli.add_aliases("bootstrap", ["bs"])
    cli.add_aliases("update-project", ["up"])
