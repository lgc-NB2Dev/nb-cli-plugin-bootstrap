from contextlib import suppress
from pathlib import Path
from typing import Optional

import click
from nb_cli.config import ConfigManager
from nb_cli.handlers import requires_project_root
from nb_cli.handlers.meta import _get_env_python
from poetry.utils.env import VirtualEnv
from poetry.utils.env import EnvCommandError

# if not importlib.util.find_spec("poetry"):
#     raise ImportError(
#         "Please install `poetry` in nb-cli's environment first, "
#         "use `nb self install poetry`",
#     )


def find_venv_root(child_path: Path) -> Path:
    while True:
        if (child_path / "pyvenv.cfg").exists():
            return child_path
        child_path = child_path.parent
        if len(child_path.parts) <= 1:
            break
    raise FileNotFoundError("No virtual environment found")


def get_venv_dir(cwd: Optional[Path]) -> Path:
    config = ConfigManager(working_dir=cwd, use_venv=True)
    if config.python_path:
        return find_venv_root(Path(config.python_path).parent)
    raise FileNotFoundError("No virtual environment found")


@requires_project_root
async def shell_handler(cwd: Optional[Path] = None):
    venv_path = get_venv_dir(cwd)
    with suppress(FileNotFoundError):
        now_venv_path = find_venv_root(Path(await _get_env_python()).parent)
        if now_venv_path == venv_path:
            click.secho("您当前已在虚拟环境内", fg="yellow")
            return

    click.secho(f"进入虚拟环境：{venv_path}", fg="green")
    venv = VirtualEnv(venv_path)
    shell = Shell.get()
    shell.activate(venv)
