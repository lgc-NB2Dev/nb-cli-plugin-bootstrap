import asyncio
from pathlib import Path
from typing import List, Optional, Union
from typing_extensions import TypeAlias

import click
from nb_cli.cli.utils import CLI_DEFAULT_STYLE
from nb_cli.handlers.meta import get_default_python, get_nonebot_config, requires_pip
from nb_cli.handlers.pip import call_pip_update
from nb_cli.handlers.project import requires_project_root
from noneprompt import ConfirmPrompt

ADAPTER_PKG_PFX = "nonebot.adapters."
LEN_ADAPTER_PKG_PFX = len(ADAPTER_PKG_PFX)


class SuccessInstallInfo:
    def __init__(self, name: str, stdout: str):
        self.name = name
        self.stdout = stdout

        self.version = self._parse_version()

    def _parse_version(self) -> Optional[str]:
        suc_out = "Successfully installed "
        if suc_out in self.stdout:
            index = self.stdout.rfind(self.name) + len(self.name) + 1
            return self.stdout[index : self.stdout.find(" ", index)].strip()
        return None


class FailInstallInfo:
    def __init__(self, name: str, stderr: str):
        self.name = name
        self.stderr = stderr

        self.reason = self._parse_reason()

    def _parse_reason(self) -> Optional[str]:
        nf_out = "No matching distribution found for "
        if (nf_index := self.stderr.find(nf_out)) != -1:
            index = nf_index + len(nf_out)
            pkg = self.stderr[index:].strip()
            return f"包 {pkg} 不存在"
        return "未知原因"


InstallInfoType: TypeAlias = Union[SuccessInstallInfo, FailInstallInfo]


def guess_adapter_pkg_name(module_names: List[str]) -> List[str]:
    pkg_names = []
    for name in module_names:
        if name.startswith(ADAPTER_PKG_PFX):
            name = name[LEN_ADAPTER_PKG_PFX:]
        name = name.split(".", maxsplit=1)[0]
        pkg_names.append(f"nonebot-adapter-{name}")
    return pkg_names


async def update_pkg(python_path: str, pkg: str) -> InstallInfoType:
    proc = await call_pip_update(
        pkg,
        python_path=python_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return_code = await proc.wait()

    if return_code == 0:
        return SuccessInstallInfo(
            pkg,
            (await proc.stdout.read()).decode() if proc.stdout else "",
        )
    return FailInstallInfo(
        pkg,
        (await proc.stderr.read()).decode() if proc.stderr else "",
    )


def summary_infos(infos: List[InstallInfoType]) -> str:
    success_infos = [x for x in infos if isinstance(x, SuccessInstallInfo)]
    updated_infos = [x for x in success_infos if x.version]
    unchanged_infos = [x for x in success_infos if x not in updated_infos]
    fail_infos = [x for x in infos if isinstance(x, FailInstallInfo)]

    info_li: List[str] = []

    if updated_infos:
        updated_title = click.style(
            f"已更新（{len(updated_infos)} 个）：",
            fg="green",
            bold=True,
        )
        updated_plugins = "\n".join(
            f"  {x.name} {click.style(x.version, fg='cyan')}" for x in updated_infos
        )
        info_li.append(f"{updated_title}\n{updated_plugins}")

    if unchanged_infos:
        unchanged_title = click.style(
            f"版本未变（{len(unchanged_infos)} 个）：",
            fg="yellow",
            bold=True,
        )
        unchanged_plugins = "\n".join(f"  {x.name}" for x in unchanged_infos)
        info_li.append(f"{unchanged_title}\n{unchanged_plugins}")

    if fail_infos:
        fail_title = click.style(
            f"失败（{len(fail_infos)} 个）：",
            fg="red",
            bold=True,
        )
        fail_plugins = "\n".join(
            f"  {x.name}：{click.style(x.reason, fg='red')}" for x in fail_infos
        )
        info_li.append(f"{fail_title}\n{fail_plugins}")

    return "\n\n".join(info_li)


@requires_project_root
@requires_pip
async def update_project_handler(
    *,
    python_path: Optional[str] = None,
    cwd: Optional[Path] = None,  # noqa: ARG001
):
    bot_config = get_nonebot_config()
    if python_path is None:
        python_path = await get_default_python()

    pkgs = [
        *guess_adapter_pkg_name([x.module_name for x in bot_config.adapters]),
        *(x.replace("_", "-") for x in bot_config.plugins),
    ]
    if not pkgs:
        click.secho("你还没有安装过商店插件或适配器，没有需要更新的包", fg="green")
        return

    if not await ConfirmPrompt(
        "一键更新所有适配器或插件有可能会导致它们之间不兼容导致报错，请问您是否真的要继续？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE):
        return

    infos = []
    with click.progressbar(
        pkgs,
        show_eta=False,
        show_percent=True,
        show_pos=True,
        item_show_func=lambda x: (click.style(x, fg="green", bold=True) if x else None),
        bar_template=f"更新中 {click.style('%(info)s', fg='cyan')} [%(bar)s]",
    ) as pkgs_prog:
        for pkg in pkgs_prog:
            info = await update_pkg(python_path, pkg)
            infos.append(info)
            if isinstance(info, FailInstallInfo):
                click.secho(
                    f"\n更新 {pkg} 失败！原因：{info.reason}\n{info.stderr.rstrip()}",
                    fg="red",
                )

    click.secho("更新完毕！\n", fg="green", bold=True)
    click.echo(summary_infos(infos))
