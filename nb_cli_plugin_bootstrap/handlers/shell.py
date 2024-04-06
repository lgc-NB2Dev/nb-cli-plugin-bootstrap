from pathlib import Path
from typing import Optional

import click
from nb_cli.handlers import requires_project_root
from poetry.utils.env import VirtualEnv
from poetry.utils.shell import Shell

# if not importlib.util.find_spec("poetry"):
#     raise ImportError(
#         "Please install `poetry` in nb-cli's environment first, "
#         "use `nb self install poetry`",
#     )


def get_venv_dir(cwd: Path) -> Path:
    path = cwd / ".venv"
    if path.is_dir() and (path / "pyvenv.cfg").is_file():
        return path
    raise FileNotFoundError("No virtual environment found")


@requires_project_root
async def shell_handler(cwd: Optional[Path] = None):
    shell = Shell.get()
    venv_path = get_venv_dir(cwd or Path.cwd())
    venv = VirtualEnv(venv_path)
    click.secho(f"进入虚拟环境：{venv_path}", fg="green")
    shell.activate(venv)
