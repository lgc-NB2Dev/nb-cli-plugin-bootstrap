import click
from nb_cli.cli import ClickAliasedGroup, run_async

from .handlers.bootstrap import bootstrap_handler
from .handlers.update_project import update_project_handler


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="创建一个更实用的 NoneBot2 初始项目",
)
@run_async
async def bootstrap():
    await bootstrap_handler()


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help="更新当前文件夹项目中的所有适配器和插件",
)
@run_async
async def update_project():
    await update_project_handler()
