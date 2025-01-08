import asyncio
import json
import locale
import sys
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Optional, TextIO, Union
from typing_extensions import TypeAlias

from nb_cli.compat import type_validate_python
from nb_cli.handlers import get_default_python
from nb_cli.handlers.pip import call_pip
from pydantic import AnyHttpUrl, BaseModel, IPvAnyAddress, ValidationError

if TYPE_CHECKING:
    from asyncio.subprocess import Process

InstallInfoType: TypeAlias = Union["SuccessInstallInfo", "FailInstallInfo"]

ENC = locale.getpreferredencoding()


class SuccessInstallInfo:
    def __init__(self, name: str, stdout: str, stderr: str):
        self.name = name
        self.stdout = stdout
        self.stderr = stderr
        self.packages = self._parse_packages()

    @property
    def version(self) -> Optional[str]:
        return self.packages.get(self.name)

    @property
    def packages_without_self(self) -> dict[str, str]:
        return {k: v for k, v in self.packages.items() if k != self.name}

    def _parse_packages(self) -> dict[str, str]:
        suc_out = "Successfully installed "
        if (out_index := self.stdout.rfind(suc_out)) == -1:
            return {}
        packages_str = self.stdout[out_index + len(suc_out) :].split()
        return dict(pkg_str.rsplit("-", maxsplit=1) for pkg_str in packages_str)


class FailInstallInfo:
    def __init__(self, name: str, stdout: str, stderr: str):
        self.name = name
        self.stdout = stdout
        self.stderr = stderr
        self.reason = self._parse_reason()

    def _parse_reason(self) -> Optional[str]:
        if "ConnectTimeoutError" in self.stderr:
            return "请求超时，请检查网络环境"
        if "ConnectionError" in self.stderr:
            return "连接失败，请检查网络环境"
        if "SSLError" in self.stderr:
            return "出现 SSL 相关问题，如果你正在使用代理，请切换节点后重试"
        if "WinError 5" in self.stderr:
            return "拒绝访问，可能是文件被占用，请关掉 NoneBot 后重试"
        if "ResolutionImpossible" in self.stderr:
            return "包版本冲突"

        nf_out = "No matching distribution found for "
        if (nf_index := self.stderr.find(nf_out)) != -1:
            index = nf_index + len(nf_out)
            pkg = self.stderr[index:].strip()
            return f"包 {pkg} 不存在，可能是插件 Import 包名与 PyPI 项目名不一致，请自行手动解决"

        return "未知原因"


def decode(s: bytes) -> str:
    try:
        return s.decode()
    except UnicodeDecodeError:
        return s.decode(ENC, errors="replace")


async def call_pip_simp(
    command: str,
    *pip_args: str,
    python_path: Optional[str] = None,
    force_no_uv: bool = False,
) -> "Process":
    if (not await uv_exists()) or force_no_uv:
        return await call_pip(
            [command, *pip_args],
            python_path=python_path,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    if python_path is None:
        python_path = await get_default_python()
    return await asyncio.create_subprocess_exec(
        *("uv", "pip", command, "-p", python_path, *pip_args),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def call_pip_update_simp(
    *pip_args: str,
    python_path: Optional[str] = None,
    force_no_uv: bool = False,
) -> "Process":
    return await call_pip_simp(
        *("install", "--upgrade", *pip_args),
        python_path=python_path,
        force_no_uv=force_no_uv,
    )


async def read_stream(
    stream: Optional[asyncio.StreamReader],
    outer: Optional[TextIO] = None,
) -> str:
    if not stream:
        return ""

    cached_io = StringIO()
    async for data in stream:
        data_str = decode(data)
        cached_io.write(data_str)
        if outer:
            outer.write(data_str)

    return cached_io.getvalue()


async def wait(
    proc: asyncio.subprocess.Process,
    verbose: bool = False,
) -> tuple[int, str, str]:
    if verbose:
        stdout, stderr = await asyncio.gather(
            read_stream(proc.stdout, sys.stdout),
            read_stream(proc.stderr, sys.stderr),
        )
    else:
        stdout_b, stderr_b = await proc.communicate()
        stdout = decode(stdout_b or b"")
        stderr = decode(stderr_b or b"")
    return (await proc.wait(), stdout, stderr)


def normalize_pkg_name(name: str) -> str:
    return name.replace("_", "-").lower()


async def list_all_packages(python_path: Optional[str] = None) -> dict[str, str]:
    proc = await call_pip_simp("list", "--format=json", python_path=python_path)
    return_code = await proc.wait()
    if not return_code == 0:
        raise RuntimeError("Failed to execute command `pip list`")
    assert proc.stdout
    stdout = decode(await proc.stdout.read())
    return {normalize_pkg_name(x["name"]): x["version"] for x in json.loads(stdout)}


async def update_package(
    pkg: str,
    python_path: Optional[str] = None,
    verbose: bool = False,
) -> InstallInfoType:
    if verbose:
        print()
    proc = await call_pip_update_simp(pkg, python_path=python_path)
    return_code, stdout, stderr = await wait(proc, verbose=verbose)
    return (
        SuccessInstallInfo(pkg, stdout, stderr)
        if return_code == 0
        else FailInstallInfo(pkg, stdout, stderr)
    )


def validate_ip_v_any_addr(addr: str) -> bool:
    class ValidateModel(BaseModel):
        addr: IPvAnyAddress

    try:
        type_validate_python(ValidateModel, {"addr": addr})
    except ValidationError:
        return False
    return True


def validate_http_url(url: str) -> bool:
    class ValidateModel(BaseModel):
        url: AnyHttpUrl

    try:
        type_validate_python(ValidateModel, {"url": url})
    except ValidationError:
        return False
    return True


_uv_exists = False


async def uv_exists() -> bool:
    global _uv_exists
    if _uv_exists:
        return True

    try:
        code = await (
            await asyncio.create_subprocess_exec(
                *("uv", "--version"),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        ).wait()
    except Exception:
        return False
    _uv_exists = code == 0
    return _uv_exists


async def get_uv_python_path() -> Optional[Path]:
    if not await uv_exists():
        return None
    code, stdout, _ = await wait(
        await asyncio.create_subprocess_exec(
            *("uv", "python", "dir"),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        ),
    )
    stdout = stdout.strip()
    if code == 0 and stdout and (p := Path(stdout)).exists():
        return p
    return None
