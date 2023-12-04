from contextlib import suppress
from pathlib import Path

use_run_script = "{{ cookiecutter.nonebot.use_run_script }}" == "True"
is_windows = "{{ cookiecutter.nonebot.is_windows }}" == "True"
project_root = Path.cwd()


def rm_linux_script():
    for x in project_root.glob("*.sh"):
        x.unlink()


def rm_windows_script():
    for x in project_root.glob("*.bat"):
        x.unlink()


def chmod_linux_script():
    for x in project_root.glob("*.sh"):
        with suppress(Exception):
            x.chmod(0o755)


if not use_run_script:
    rm_linux_script()
    rm_windows_script()
elif is_windows:
    rm_linux_script()
else:
    rm_windows_script()
    chmod_linux_script()
