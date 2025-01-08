import sys

import click
from nb_cli.cli.utils import CLI_DEFAULT_STYLE
from noneprompt import Choice, InputPrompt, ListPrompt

from ..const import INPUT_QUESTION
from ..utils import call_pip_simp, uv_exists, validate_http_url, wait

PyPIMirrorCustom = type("PyPIMirrorCustom", (), {})
PYPI_MIRRORS = (
    ("清华大学", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    ("中国科学技术大学", "https://pypi.mirrors.ustc.edu.cn/simple"),
    ("阿里云", "https://mirrors.aliyun.com/pypi/simple/"),
    ("豆瓣", "https://pypi.douban.com/simple/"),
    ("自定义", PyPIMirrorCustom()),
    ("不使用镜像源", None),
)


async def pip_index_handler(verbose: bool = False):
    if await uv_exists():
        click.secho("此功能暂不适用于 uv", fg="yellow")
        sys.exit(1)

    choice = await ListPrompt(
        "请选择你想要对 pip 使用的 PyPI 镜像源",
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

    proc = await call_pip_simp(
        *("config", "get", "global.index-url"),
        force_no_uv=True,
    )
    code, stdout, _ = await wait(proc, verbose=verbose)
    current_mirror = stdout.strip() if (code == 0) else None
    if selected_mirror:
        proc = await call_pip_simp(
            *("config", "set", "global.index-url", selected_mirror),
            force_no_uv=True,
        )
    elif current_mirror:  # 设置过才执行清空
        proc = await call_pip_simp(
            *("config", "unset", "global.index-url"),
            force_no_uv=True,
        )
    else:
        proc = None
    code, _, stderr = await wait(proc, verbose=verbose) if proc else (0, b"", b"")

    if (not proc) or current_mirror == selected_mirror:
        click.secho("PyPI 源配置未变", fg="yellow", bold=True)
    elif code == 0:
        click.secho("PyPI 源配置成功", fg="green", bold=True)
    else:
        err = stderr or ""
        click.secho(f"PyPI 源配置失败！\n{err}", fg="red", bold=True, err=True)
