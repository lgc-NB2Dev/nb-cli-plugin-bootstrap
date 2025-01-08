import json
import shlex
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click
import findpython
from cookiecutter.main import cookiecutter
from cookit.pyd import type_dump_json
from findpython.providers import RyeProvider
from nb_cli.cli.commands.project import ProjectContext, project_name_validator
from nb_cli.cli.utils import CLI_DEFAULT_STYLE
from nb_cli.config.parser import ConfigManager
from nb_cli.consts import REQUIRES_PYTHON, WINDOWS
from nb_cli.handlers import get_default_python
from nb_cli.handlers.adapter import list_adapters
from nb_cli.handlers.plugin import list_builtin_plugins
from nb_cli.handlers.venv import create_virtualenv
from noneprompt import CheckboxPrompt, Choice, ConfirmPrompt, InputPrompt, ListPrompt
from packaging.version import Version

from ..const import INPUT_QUESTION
from ..utils import (
    call_pip_update_simp,
    get_uv_python_path,
    uv_exists,
    validate_ip_v_any_addr,
    wait,
)
from .pip_index import pip_index_handler

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
BOOTSTRAP_TEMPLATE_DIR = TEMPLATES_DIR / "bootstrap"


@dataclass
class PythonInfo:
    path: Path
    version: str


def format_project_folder_name(project_name: str) -> str:
    return project_name.replace(" ", "-").lower()


async def prompt_input_list(prompt: str, **kwargs) -> list[str]:
    click.secho(f"{prompt}（留空回车结束输入）", bold=True)

    result: list[str] = []
    counter = 0
    while True:
        counter += 1
        answer = (
            await InputPrompt(
                f"第 {counter} 项 > ",
                **kwargs,
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        ).strip()
        if not answer:
            break
        result.append(answer)
    return result


async def prompt_bootstrap_context(
    context: ProjectContext,
    project_name: Optional[str] = None,
    yes: bool = False,
    adapters: Optional[list[str]] = None,
):
    def final_project_name_validator(x: str):
        return project_name_validator(x) and (
            not (Path(format_project_folder_name(x))).exists()
        )

    if project_name and (not final_project_name_validator(project_name)):
        click.secho("项目名称非法，或项目文件夹已存在！", fg="red")
        sys.exit(1)

    click.secho("加载适配器列表中……", fg="yellow", bold=True)
    all_adapters = await list_adapters()

    if not project_name:
        click.secho("请输入项目名称", bold=True)
        project_name = await InputPrompt(
            INPUT_QUESTION,
            validator=final_project_name_validator,
            error_message="项目名称非法，或项目文件夹已存在！",
        ).prompt_async(style=CLI_DEFAULT_STYLE)

    context.variables["project_name"] = project_name
    context.variables["folder_name"] = format_project_folder_name(project_name)
    context.packages.append("nonebot2[all]")
    context.variables["plugins"] = []

    if yes or adapters:
        adapters_info = []
        for adapter_query in adapters or []:
            for a in all_adapters:
                if (adapter_query.lower() in (a.name.lower(),)) or (
                    adapter_query in (a.module_name, a.project_link)
                ):
                    adapters_info.append(a)
                    break
            else:
                click.secho(f"未找到与 {adapter_query} 相关的适配器", fg="yellow")
                sys.exit(1)
        adapters_info = list(  # 根据模块名去重
            {a.module_name: a for a in adapters_info}.values(),
        )
        click.secho(f"已选择适配器：{', '.join(a.name for a in adapters_info) or '无'}")
    else:
        while True:
            adapter_choices = await CheckboxPrompt(
                "请选择你想要使用的适配器",
                [
                    Choice(f"{adapter.name} ({adapter.desc})", adapter)
                    for adapter in all_adapters
                ],
            ).prompt_async(style=CLI_DEFAULT_STYLE)
            if (
                True
                if adapter_choices
                else (
                    yes
                    or await ConfirmPrompt(
                        "你还没有选择任何适配器！适配器是 NoneBot2 对接聊天平台的关键组件！真的要继续吗？",
                        default_choice=False,
                    ).prompt_async(style=CLI_DEFAULT_STYLE)
                )
            ):
                break
        adapters_info = [a.data for a in adapter_choices]

    context.variables["adapters"] = type_dump_json(adapters_info)
    for pkg in (
        link for x in adapters_info if (link := x.project_link) not in context.packages
    ):
        context.packages.append(pkg)

    env_superusers = (
        []
        if yes
        else await prompt_input_list(
            "请输入 Bot 超级用户，超级用户拥有对 Bot 的最高权限（如对接 QQ 填 QQ 号即可）",
        )
    )
    context.variables["env_superusers"] = json.dumps(env_superusers)

    env_nickname = (
        []
        if yes
        else await prompt_input_list(
            "请输入 Bot 昵称，消息以 Bot 昵称开头可以代替艾特",
        )
    )
    context.variables["env_nickname"] = json.dumps(env_nickname)

    default_command_start = ["", "/", "#"]
    env_command_start = (
        None
        if yes
        else await prompt_input_list(
            "请输入 Bot 命令起始字符，消息以起始符开头将被识别为命令，\n"
            '如果有一个指令为 查询，当该配置项中有 "/" 时使用 "/查询" 才能够触发，\n'
            f"留空将使用默认值 {default_command_start}",
        )
    )
    context.variables["env_command_start"] = json.dumps(
        env_command_start or default_command_start,
    )

    default_command_sep = [".", " "]
    env_command_sep = (
        None
        if yes
        else await prompt_input_list(
            f"请输入 Bot 命令分隔符，一般用于二级指令，\n留空将使用默认值 {default_command_sep}",
        )
    )
    context.variables["env_command_sep"] = json.dumps(
        env_command_sep or default_command_sep,
    )

    env_host = "127.0.0.1"
    if not yes:
        click.secho(
            "请输入 NoneBot2 监听地址，如果要对公网开放，改为 0.0.0.0 即可",
            bold=True,
        )
        env_host = (
            await InputPrompt(
                INPUT_QUESTION,
                default_text=env_host,
                validator=validate_ip_v_any_addr,
                error_message="地址格式不正确！",
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        ).strip()
    context.variables["env_host"] = env_host

    env_port = "8080"
    if not yes:
        click.secho(
            "请输入 NoneBot2 监听端口，范围 1 ~ 65535，请保证该端口号与连接端配置相同，或与端口映射配置相关",
            bold=True,
        )
        env_port = (
            await InputPrompt(
                INPUT_QUESTION,
                default_text=env_port,
                validator=lambda x: x.isdigit() and 1 <= int(x) <= 65535,
                error_message="端口号必须为范围 1 ~ 65535 的整数！",
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        ).strip()
    context.variables["env_port"] = env_port

    use_run_script = (
        (
            yes
            or await ConfirmPrompt(
                "是否在项目目录中释出快捷启动脚本？",
                default_choice=True,
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        )
        if WINDOWS
        else False
    )
    context.variables["use_run_script"] = use_run_script
    context.variables["is_windows"] = WINDOWS

    redirect_localstore = yes or await ConfirmPrompt(
        "是否将 localstore 插件的存储路径重定向到项目路径下以便于后续迁移 Bot？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    context.variables["redirect_localstore"] = redirect_localstore

    use_ping = yes or await ConfirmPrompt(
        "是否使用超级用户 Ping 指令回复插件？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    context.variables["use_ping"] = use_ping

    install_logpile = yes or await ConfirmPrompt(
        "是否安装 logpile 插件提供日志记录到文件功能？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    context.variables["use_logpile"] = install_logpile
    if install_logpile:
        context.packages.append("nonebot-plugin-logpile")
        context.variables["plugins"].append("nonebot_plugin_logpile")

    context.variables["plugins"] = json.dumps(context.variables["plugins"])


async def post_project_render(
    context: ProjectContext,
    yes: bool = False,
    verbose: bool = False,
    venv: Optional[bool] = None,
) -> bool:
    use_venv = (
        (
            yes
            or await ConfirmPrompt(
                "是否新建虚拟环境？",
                default_choice=True,
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        )
        if venv is None
        else venv
    )

    required_ver = Version(".".join(str(x) for x in REQUIRES_PYTHON))
    finder = findpython.Finder()
    uv_python_path = await get_uv_python_path()
    if uv_python_path:
        finder.add_provider(RyeProvider(uv_python_path), 0)
    python_infos = [
        x
        for x in finder.find_all()
        if (
            x.version >= required_ver
            and all((p not in x.executable.parts) for p in (".venv", "venv"))
        )
    ]
    if not python_infos:
        selected_python = await get_default_python()
    elif len(python_infos) == 1 or yes:
        selected_python = python_infos[0].executable
    else:
        selected_python = (
            await ListPrompt(
                question="请选择你想要用来创建虚拟环境的 Python 解释器",
                choices=[
                    Choice(
                        f"{info.implementation} {info.version} ({info.executable})",
                        info,
                    )
                    for info in python_infos
                ],
            ).prompt_async()
        ).data.executable

    project_dir_name = context.variables["project_name"].replace(" ", "-").lower()
    project_dir = Path.cwd() / project_dir_name
    if use_venv:
        venv_dir = project_dir / ".venv"
        click.secho(
            (f"正在 {venv_dir} 中使用 Python {selected_python} 创建虚拟环境"),
            fg="yellow",
        )
        try:
            await create_virtualenv(
                venv_dir,
                prompt=project_dir_name,
                python_path=str(selected_python),
            )
        except Exception:
            click.secho(
                f"创建虚拟环境失败\n{traceback.format_exc()}",
                fg="red",
                bold=True,
                err=True,
            )
            return False
        click.secho("创建虚拟环境成功", fg="green", bold=True)

    if (
        False
        if yes or (await uv_exists())
        else await ConfirmPrompt(
            "是否需要修改或清除 pip 的 PyPI 镜像源配置？",
            default_choice=False,
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    ):
        await pip_index_handler(verbose=verbose)

    manually_install_tip = "项目依赖已写入项目 pyproject.toml 中，请自行手动安装，或使用 pdm 等包管理器安装"
    if not (
        (use_venv)  # 全默认别装全局环境
        if yes
        else await ConfirmPrompt(
            f"是否立即安装项目依赖？{'' if use_venv else '（注意：将会安装到默认全局环境中！）'}",
            default_choice=True,
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    ):
        click.secho(manually_install_tip, fg="green")
        return True

    click.secho("正在安装项目依赖", fg="yellow")
    config_manager = ConfigManager(working_dir=project_dir, use_venv=use_venv)
    proc = await call_pip_update_simp(
        *context.packages,
        python_path=config_manager.python_path,
    )
    code, _, stderr = await wait(proc, verbose=verbose)
    if code == 0:
        click.secho("依赖安装成功", fg="green", bold=True)
    else:
        click.secho(
            f"依赖安装失败，{manually_install_tip}\n{stderr}",
            fg="red",
            bold=True,
            err=True,
        )
        return False

    if not yes:
        builtin_plugins = await list_builtin_plugins(
            python_path=config_manager.python_path,
        )
        selected_builtin_plugins = [
            x.data
            for x in await CheckboxPrompt(
                "请选择需要启用的内置插件",
                [Choice(p, p) for p in builtin_plugins],
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        ]
        try:
            for plugin in selected_builtin_plugins:
                config_manager.add_builtin_plugin(plugin)
        except Exception:
            click.secho(
                f"启用内置插件失败\n{traceback.format_exc()}",
                fg="red",
                bold=True,
                err=True,
            )
            return False

    return True


async def bootstrap_handler(
    *,
    project_name: Optional[str] = None,
    yes: bool = False,
    verbose: bool = False,
    venv: Optional[bool] = None,
    adapters: Optional[list[str]] = None,
):
    context = ProjectContext()
    await prompt_bootstrap_context(
        context,
        yes=yes,
        project_name=project_name,
        adapters=adapters,
    )

    nb_command_list = [sys.executable, "-m", "nb_cli"]
    context.variables["nb_command"] = (
        subprocess.list2cmdline(nb_command_list)
        if WINDOWS
        else " ".join(shlex.quote(x) for x in nb_command_list)
    )
    extra_context = {
        "nonebot": {
            **context.variables,
            "packages": json.dumps(context.packages),
        },
    }
    try:
        cookiecutter(
            str(BOOTSTRAP_TEMPLATE_DIR.resolve()),
            no_input=True,
            extra_context=extra_context,
            output_dir=".",
        )
    except Exception:
        click.secho(
            f"新建项目失败！\n{traceback.format_exc()}",
            fg="red",
            bold=True,
            err=True,
        )
        return
    click.secho(
        f"成功新建项目 {context.variables['project_name']}",
        fg="green",
        bold=True,
    )

    if await post_project_render(context, yes=yes, verbose=verbose, venv=venv):
        click.secho("项目配置完毕，开始使用吧！", fg="green", bold=True)
    else:
        click.secho(
            "项目配置失败！你可能需要考虑手动进行后续配置，或重新创建一次项目",
            fg="red",
            bold=True,
            err=True,
        )
