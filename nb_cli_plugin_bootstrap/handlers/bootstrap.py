import asyncio
import json
import platform
import shlex
import subprocess
import sys
import traceback
from asyncio.subprocess import Process
from pathlib import Path
from typing import List, Optional

import click
from cookiecutter.main import cookiecutter
from nb_cli.cli.commands.project import (
    ProjectContext,
    project_name_validator,
)
from nb_cli.cli.utils import CLI_DEFAULT_STYLE
from nb_cli.config.parser import ConfigManager
from nb_cli.handlers.adapter import list_adapters
from nb_cli.handlers.pip import call_pip
from nb_cli.handlers.plugin import list_builtin_plugins
from nb_cli.handlers.process import create_process
from nb_cli.handlers.venv import create_virtualenv
from noneprompt import CheckboxPrompt, Choice, ConfirmPrompt, InputPrompt
from noneprompt.prompts.list import ListPrompt
from pydantic.config import BaseConfig
from pydantic.errors import IPvAnyAddressError
from pydantic.fields import ModelField
from pydantic.networks import AnyHttpUrl, IPvAnyAddress

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
BOOTSTRAP_TEMPLATE_DIR = TEMPLATES_DIR / "bootstrap"
IS_WINDOWS = "Windows" in platform.system()
INPUT_QUESTION = "请输入 > "

PyPIMirrorCustom = type("PyPIMirrorCustom", (), {})
PYPI_MIRRORS = (
    ("清华大学", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    ("中国科学技术大学", "https://pypi.mirrors.ustc.edu.cn/simple"),
    ("阿里云", "https://mirrors.aliyun.com/pypi/simple/"),
    ("豆瓣", "https://pypi.douban.com/simple/"),
    ("自定义", PyPIMirrorCustom()),
    ("不使用镜像源", None),
)


def validate_ip_v_any_addr(addr: str) -> bool:
    try:
        IPvAnyAddress.validate(addr)
    except IPvAnyAddressError:
        return False
    return True


def validate_http_url(url: str) -> bool:
    try:
        AnyHttpUrl.validate(
            url,
            ModelField(
                name="",
                type_=AnyHttpUrl,
                class_validators=None,
                model_config=BaseConfig,
            ),
            BaseConfig(),
        )
    except Exception:
        return False
    return True


def format_project_folder_name(project_name: str) -> str:
    return project_name.replace(" ", "-").lower()


async def call_pip_no_output(
    pip_args: List[str],
    python_path: Optional[str] = None,
) -> Process:
    return await call_pip(
        pip_args,
        python_path=python_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def call_pip_update_no_output(
    pip_args: List[str],
    python_path: Optional[str] = None,
) -> Process:
    return await call_pip_no_output(
        ["install", "--upgrade", *pip_args],
        python_path=python_path,
    )


async def prompt_input_list(prompt: str, **kwargs) -> List[str]:
    click.secho(f"{prompt}（留空回车结束输入）", bold=True)

    result: List[str] = []
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


async def prompt_bootstrap_context(context: ProjectContext):
    context.packages.append("nonebot2[all]")
    context.variables["plugins"] = []

    click.secho("加载适配器列表中……", fg="yellow", bold=True)
    all_adapters = await list_adapters()

    click.secho("请输入项目名称", bold=True)
    project_name = await InputPrompt(
        INPUT_QUESTION,
        validator=lambda x: (
            project_name_validator(x)
            and (not (Path(format_project_folder_name(x))).exists())
        ),
        error_message="项目名称非法，或项目文件夹已存在！",
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    context.variables["project_name"] = project_name
    context.variables["folder_name"] = format_project_folder_name(project_name)

    while True:
        adapters = await CheckboxPrompt(
            "请选择你想要使用的适配器",
            [
                Choice(f"{adapter.name} ({adapter.desc})", adapter)
                for adapter in all_adapters
            ],
        ).prompt_async(style=CLI_DEFAULT_STYLE)
        if (
            True
            if adapters
            else (
                await ConfirmPrompt(
                    "你还没有选择任何适配器！适配器是 NoneBot2 对接聊天平台的关键组件！真的要继续吗？",
                    default_choice=False,
                ).prompt_async(style=CLI_DEFAULT_STYLE)
            )
        ):
            break
    context.variables["adapters"] = json.dumps([a.data.dict() for a in adapters])
    for pkg in (
        link for x in adapters if (link := x.data.project_link) not in context.packages
    ):
        context.packages.append(pkg)

    env_superusers = await prompt_input_list(
        "请输入 Bot 超级用户，超级用户拥有对 Bot 的最高权限（如对接 QQ 填 QQ 号即可）",
    )
    context.variables["env_superusers"] = json.dumps(env_superusers)

    env_nickname = await prompt_input_list(
        "请输入 Bot 昵称，消息以 Bot 昵称开头可以代替艾特",
    )
    context.variables["env_nickname"] = json.dumps(env_nickname)

    default_command_start = ["", "/", "#"]
    env_command_start = await prompt_input_list(
        "请输入 Bot 命令起始字符，消息以起始符开头将被识别为命令，\n"
        '如果有一个指令为 查询，当该配置项中有 "/" 时使用 "/查询" 才能够触发，\n'
        f"留空将使用默认值 {default_command_start}",
    )
    context.variables["env_command_start"] = json.dumps(
        env_command_start or default_command_start,
    )

    default_command_sep = [".", " "]
    env_command_sep = await prompt_input_list(
        f"请输入 Bot 命令分隔符，一般用于二级指令，\n留空将使用默认值 {default_command_sep}",
    )
    context.variables["env_command_sep"] = json.dumps(
        env_command_sep or default_command_sep,
    )

    click.secho("请输入 NoneBot2 监听地址，如果要对公网开放，改为 0.0.0.0 即可", bold=True)
    env_host = (
        await InputPrompt(
            INPUT_QUESTION,
            default_text="127.0.0.1",
            validator=validate_ip_v_any_addr,
            error_message="地址格式不正确！",
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    ).strip()
    context.variables["env_host"] = env_host

    click.secho(
        "请输入 NoneBot2 监听端口，范围 1 ~ 65535，请保证该端口号与连接端配置相同，或与端口映射配置相关",
        bold=True,
    )
    env_port = (
        await InputPrompt(
            INPUT_QUESTION,
            default_text="8080",
            validator=lambda x: x.isdigit() and 1 <= int(x) <= 65535,
            error_message="端口号必须为范围 1 ~ 65535 的整数！",
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    ).strip()
    context.variables["env_port"] = env_port

    use_run_script = await ConfirmPrompt(
        "是否在项目目录中释出快捷启动脚本？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    context.variables["use_run_script"] = use_run_script
    context.variables["is_windows"] = IS_WINDOWS

    redirect_localstore = await ConfirmPrompt(
        "是否将 localstore 插件的存储路径重定向到项目路径下以便于后续迁移 Bot？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    context.variables["redirect_localstore"] = redirect_localstore

    use_ping = await ConfirmPrompt(
        "是否使用超级用户 Ping 指令回复插件？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    context.variables["use_ping"] = use_ping

    has_onebot = "nonebot-adapter-onebot" in context.packages
    if has_onebot:
        install_gocqhttp = await ConfirmPrompt(
            "是否安装 gocqhttp 插件提供内置 GoCQHTTP 启动器？（不推荐）",
            default_choice=False,
        ).prompt_async(style=CLI_DEFAULT_STYLE)
        if install_gocqhttp:
            context.packages.append("nonebot-plugin-gocqhttp")
            context.variables["plugins"].append("nonebot_plugin_gocqhttp")

        install_guild_patch = await ConfirmPrompt(
            "是否安装 guild-patch 插件提供对 GoCQHTTP 的 QQ 频道支持？",
            default_choice=True,
        ).prompt_async(style=CLI_DEFAULT_STYLE)
        if install_guild_patch:
            context.packages.append("nonebot-plugin-guild-patch")
            context.variables["plugins"].append("nonebot_plugin_guild_patch")

    install_logpile = await ConfirmPrompt(
        "是否安装 logpile 插件提供日志记录到文件功能？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    if install_logpile:
        context.packages.append("nonebot-plugin-logpile")
        context.variables["plugins"].append("nonebot_plugin_logpile")

    if use_run_script:
        use_web_ui = await ConfirmPrompt(
            "是否在启动脚本中使用 webui 插件启动项目以使用网页管理 NoneBot？（该插件缺少教程，仅推荐进阶用户使用）",
            default_choice=False,
        ).prompt_async(style=CLI_DEFAULT_STYLE)
        context.variables["use_web_ui"] = use_web_ui
    else:
        context.variables["use_web_ui"] = False

    context.variables["plugins"] = json.dumps(context.variables["plugins"])


async def configure_web_ui():
    click.secho("正在为 nb-cli 安装 webui 插件，请稍候", fg="yellow", bold=True)
    proc = await call_pip_update_no_output(
        ["nb-cli-plugin-webui"],
        python_path=sys.executable,
    )
    if await proc.wait() != 0:
        click.secho(
            f"插件安装失败，请使用 `nb self update nb-cli-plugin-webui` 指令手动安装\n{proc.stderr}",
            fg="red",
            bold=True,
            err=True,
        )

    click.secho("插件安装成功", fg="green", bold=True)
    # click.secho("接下来，让我们开始配置 webui 插件，请稍等", fg="yellow", bold=True)
    proc = await create_process(
        sys.executable,
        "-c",
        "import nb_cli_plugin_webui.app.config",
    )
    await proc.wait()


async def change_pip_mirror():
    choice = await ListPrompt(
        "请选择你想要使用的 PyPI 镜像源",
        [
            Choice(f"{name} > {url}" if isinstance(url, str) else name, url)
            for name, url in PYPI_MIRRORS
        ],
    ).prompt_async(style=CLI_DEFAULT_STYLE)

    selected = choice.data
    if isinstance(selected, PyPIMirrorCustom):
        click.secho("请输入 PyPI 源地址", bold=True)
        selected_mirror = await InputPrompt(
            INPUT_QUESTION,
            validator=validate_http_url,
            error_message="链接格式不正确！",
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    else:
        selected_mirror = selected

    proc = await call_pip_no_output(["config", "get", "global.index-url"])
    current_mirror = (
        (await proc.stdout.read()).decode().strip()
        if (await proc.wait() == 0) and proc.stdout
        else None
    )
    if selected_mirror:
        proc = await call_pip_no_output(
            ["config", "set", "global.index-url", selected_mirror],
        )
    elif current_mirror:  # 设置过才执行清空
        proc = await call_pip_no_output(
            ["config", "unset", "global.index-url"],
        )
    else:
        proc = None
    code = await proc.wait() if proc else 0

    if (not proc) or current_mirror == selected_mirror:
        click.secho("PyPI 源配置未变", fg="yellow", bold=True)
    elif code == 0:
        click.secho("PyPI 源配置成功", fg="green", bold=True)
    else:
        err = (await proc.stderr.read()).decode() if proc.stderr else ""
        click.secho(f"PyPI 源配置失败！\n{err}", fg="red", bold=True, err=True)


async def post_project_render(context: ProjectContext) -> bool:
    if context.variables["use_web_ui"]:
        await configure_web_ui()

    use_venv = await ConfirmPrompt(
        "是否新建虚拟环境？",
        default_choice=True,
    ).prompt_async(style=CLI_DEFAULT_STYLE)
    project_dir_name = context.variables["project_name"].replace(" ", "-").lower()
    project_dir = Path.cwd() / project_dir_name
    if use_venv:
        venv_dir = project_dir / ".venv"
        click.secho(f"正在 {venv_dir} 中创建虚拟环境", fg="yellow")
        try:
            await create_virtualenv(venv_dir, prompt=project_dir_name)
        except Exception:
            click.secho(
                f"创建虚拟环境失败\n{traceback.format_exc()}",
                fg="red",
                bold=True,
                err=True,
            )
            return False
        click.secho("创建虚拟环境成功", fg="green", bold=True)

    if await ConfirmPrompt(
        "是否需要修改或清除 pip 的 PyPI 镜像源配置？",
        default_choice=False,
    ).prompt_async(style=CLI_DEFAULT_STYLE):
        await change_pip_mirror()

    manually_install_tip = "项目依赖已写入项目 pyproject.toml 中，请自行手动安装，或使用 pdm 等包管理器安装"
    if (not use_venv) or (
        not await ConfirmPrompt(
            "是否立即安装项目依赖？",
            default_choice=True,
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    ):
        click.secho(manually_install_tip, fg="green")
        return True

    click.secho("正在安装项目依赖", fg="yellow")
    config_manager = ConfigManager(working_dir=project_dir, use_venv=use_venv)
    proc = await call_pip_update_no_output(
        context.packages,
        python_path=config_manager.python_path,
    )
    if await proc.wait() == 0:
        click.secho("依赖安装成功", fg="green", bold=True)
    else:
        click.secho(
            f"依赖安装失败，{manually_install_tip}\n{proc.stderr}",
            fg="red",
            bold=True,
            err=True,
        )
        return False

    builtin_plugins = await list_builtin_plugins(python_path=config_manager.python_path)
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


async def bootstrap_handler():
    context = ProjectContext()
    await prompt_bootstrap_context(context)

    nb_command_list = [sys.executable, "-m", "nb_cli"]
    context.variables["nb_command"] = (
        subprocess.list2cmdline(nb_command_list)
        if IS_WINDOWS
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
        click.secho(f"新建项目失败！\n{traceback.format_exc()}", fg="red", bold=True, err=True)
        return
    click.secho(f"成功新建项目 {context.variables['project_name']}", fg="green", bold=True)

    if await post_project_render(context):
        click.secho("项目配置完毕，开始使用吧！", fg="green", bold=True)
    else:
        click.secho("项目配置失败！你可能需要考虑手动进行后续配置，或重新创建一次项目", fg="red", bold=True, err=True)
