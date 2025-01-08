from typing import TYPE_CHECKING, Optional

import click
from nb_cli.cli.utils import CLI_DEFAULT_STYLE
from nb_cli.handlers.meta import (
    get_default_python,
    get_nonebot_config,
    requires_pip,
    requires_project_root,
)
from noneprompt import ConfirmPrompt

from ..utils import (
    FailInstallInfo,
    InstallInfoType,
    SuccessInstallInfo,
    list_all_packages,
    normalize_pkg_name,
    update_package,
)

if TYPE_CHECKING:
    from pathlib import Path

ADAPTER_PKG_PFX = "nonebot.adapters."
LEN_ADAPTER_PKG_PFX = len(ADAPTER_PKG_PFX)


def guess_adapter_pkg_name(module_names: list[str]) -> list[str]:
    pkg_names = []
    for name in module_names:
        if name.startswith(ADAPTER_PKG_PFX):
            name = name[LEN_ADAPTER_PKG_PFX:]
        name = name.split(".", maxsplit=1)[0]
        pkg_names.append(f"nonebot-adapter-{name}")
    return [normalize_pkg_name(x) for x in pkg_names]


def style_change(*change: Optional[str]) -> str:
    return " -> ".join(
        click.style(x, fg="cyan")
        if x
        else (
            click.style("已卸载", fg="red") if i else click.style("未安装", fg="yellow")
        )
        for i, x in enumerate(change)
    )


def style_change_dict(change: dict[str, tuple[Optional[str], Optional[str]]]) -> str:
    width = max(len(x) for x in change)
    return "\n".join(
        f"  {k.ljust(width)} {style_change(*v)}" for k, v in change.items()
    )


async def summary_infos(
    infos: list[InstallInfoType],
    pkgs_before_install: dict[str, str],
    pkgs_after_install: dict[str, str],
) -> str:
    changed_pkgs: dict[str, tuple[Optional[str], Optional[str]]] = {
        k: (before, after)
        for k in sorted(set(pkgs_before_install) | set(pkgs_after_install))
        if (
            (before := pkgs_before_install.get(k))
            != (after := pkgs_after_install.get(k))
        )
    }

    success_infos = [x for x in infos if isinstance(x, SuccessInstallInfo)]
    unchanged_infos = [x for x in success_infos if x.name not in changed_pkgs]
    fail_infos = [x for x in infos if isinstance(x, FailInstallInfo)]
    changed_targets = {
        k: v
        for k, v in changed_pkgs.items()
        if any(True for x in success_infos if x.name == k)
    }
    changed_others = {k: v for k, v in changed_pkgs.items() if k not in changed_targets}

    info_li: list[str] = []
    if unchanged_infos:
        unchanged_title = click.style(
            f"版本未变（{len(unchanged_infos)} 个）：",
            fg="yellow",
            bold=True,
        )
        unchanged_plugins = "\n".join(f"  {x.name}" for x in unchanged_infos)
        info_li.append(f"{unchanged_title}\n{unchanged_plugins}")

    if changed_others:
        other_title = click.style(
            f"版本变动的其他包（{len(changed_others)} 个）：",
            fg="bright_blue",
            bold=True,
        )
        other_pkgs = style_change_dict(changed_others)
        info_li.append(f"{other_title}\n{other_pkgs}")

    if changed_targets:
        updated_title = click.style(
            f"已更新（{len(changed_targets)} 个）：",
            fg="green",
            bold=True,
        )
        updated_plugins = style_change_dict(changed_targets)
        info_li.append(f"{updated_title}\n{updated_plugins}")

    if fail_infos:
        fail_title = click.style(
            f"失败（{len(fail_infos)} 个）：",
            fg="red",
            bold=True,
        )
        fail_plugins = "\n".join(
            f"  {x.name}: {click.style(x.reason, fg='red')}" for x in fail_infos
        )
        info_li.append(f"{fail_title}\n{fail_plugins}")

    return "\n\n".join(info_li)


# 不能一下子全传进去，否则可能导致依赖冲突
async def update(
    packages: list[str],
    python_path: str,
    verbose: bool = False,
) -> list[InstallInfoType]:
    pkg_list_before = await list_all_packages(python_path)
    infos = []
    with click.progressbar(
        packages,
        show_eta=False,
        show_percent=True,
        show_pos=True,
        item_show_func=lambda x: (click.style(x, fg="green", bold=True) if x else None),
        bar_template=f"更新中 {click.style('%(info)s', fg='cyan')} [%(bar)s]",
    ) as pkgs_prog:
        for pkg in pkgs_prog:
            info = await update_package(pkg, python_path, verbose=verbose)
            infos.append(info)
            if isinstance(info, FailInstallInfo):
                click.secho(
                    f"\n更新 {pkg} 失败！可能原因：{info.reason}\n{info.stderr.rstrip()}",
                    fg="red",
                    err=True,
                )

    click.secho("统计数据中\n", fg="yellow")
    pkg_list_after = await list_all_packages(python_path)
    click.echo(await summary_infos(infos, pkg_list_before, pkg_list_after))
    return infos


@requires_project_root
@requires_pip
async def update_project_handler(
    *,
    yes: bool = False,
    verbose: bool = False,
    python_path: Optional[str] = None,
    cwd: Optional["Path"] = None,  # noqa: ARG001
):
    bot_config = get_nonebot_config()
    if python_path is None:
        python_path = await get_default_python()

    pkgs = [
        *guess_adapter_pkg_name([x.module_name for x in bot_config.adapters]),
        *(normalize_pkg_name(x) for x in bot_config.plugins),
    ]
    if not pkgs:
        click.secho("你还没有安装过商店插件或适配器，没有需要更新的包", fg="green")
        return

    if not (
        yes
        or await ConfirmPrompt(
            "一键更新所有适配器和插件有可能会导致它们之间不兼容导致报错，请问您是否真的要继续？",
            default_choice=True,
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    ):
        return

    while True:
        infos = await update(pkgs, python_path, verbose=verbose)
        failed_infos = [x for x in infos if isinstance(x, FailInstallInfo)]
        if (not failed_infos) or (
            not (
                yes
                or await ConfirmPrompt(
                    "部分包安装失败，是否重试？",
                    default_choice=True,
                ).prompt_async(style=CLI_DEFAULT_STYLE)
            )
        ):
            break
        pkgs = [x.name for x in failed_infos]
