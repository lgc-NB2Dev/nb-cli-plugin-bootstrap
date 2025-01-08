import shlex
import sys
from pathlib import Path
from typing import Optional

import click
import shellingham
from nb_cli.config import ConfigManager
from nb_cli.consts import WINDOWS
from nb_cli.handlers import requires_project_root

# https://github.com/python-poetry/poetry/blob/404aea53/src/poetry/console/commands/env/activate.py


def quote_command(command: str, shell: str) -> str:
    if WINDOWS:
        if shell == "cmd":
            return f'"{command}"'
        if shell in ["powershell", "pwsh"]:
            return f'& "{command}"'
    return shlex.quote(command)


def get_activate_command(bin_dir: Path, shell: str) -> Optional[str]:
    if shell == "fish":
        command, filename = "source", "activate.fish"
    elif shell == "nu":
        command, filename = "overlay use", "activate.nu"
    elif shell == "csh":
        command, filename = "source", "activate.csh"
    elif shell in ["powershell", "pwsh"]:
        command, filename = ".", "Activate.ps1"
    elif shell == "cmd":
        command, filename = ".", "activate.bat"
    else:
        command, filename = "source", "activate"

    if (activation_script := bin_dir / filename).exists():
        if WINDOWS:
            return f"{quote_command(str(activation_script), shell)}"
        return f"{command} {quote_command(str(activation_script), shell)}"
    return None


@requires_project_root
async def venv_handler(cwd: Optional[Path] = None):
    python_path: Optional[str] = ConfigManager._detact_virtual_env(cwd)  # noqa: SLF001
    if not python_path:
        click.secho("未找到虚拟环境", fg="yellow")
        sys.exit(1)

    bin_dir = Path(python_path).parent

    try:
        shell, _ = shellingham.detect_shell()
    except shellingham.ShellDetectionFailure:
        shell = ""

    command = get_activate_command(bin_dir, shell)
    if not command:
        click.secho("暂不支持当前环境，激活环境脚本未找到", fg="yellow")
        sys.exit(1)

    click.echo(command)
