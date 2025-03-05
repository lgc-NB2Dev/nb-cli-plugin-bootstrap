#!/usr/bin/env python3

import nonebot

nonebot.init()


def prepare():
    import importlib
    from pathlib import Path

    from nonebot.compat import type_validate_python
    from pydantic import BaseModel

    try:  # pragma: py-gte-311
        import tomllib  # pyright: ignore[reportMissingImports]
    except ModuleNotFoundError:  # pragma: py-lt-311
        import tomli as tomllib  # pyright: ignore[reportMissingImports]

    class AdapterInfo(BaseModel):
        module_name: str

    class NoneBotPyProjectConfig(BaseModel):
        adapters: list[AdapterInfo]
        plugins: list[str]
        plugin_dirs: list[str]
        builtin_plugins: list[str]

    class PyProjectTool(BaseModel):
        nonebot: NoneBotPyProjectConfig

    class PyProject(BaseModel):
        tool: PyProjectTool

    toml = type_validate_python(
        PyProject,
        tomllib.loads(Path("pyproject.toml").read_text("u8")),
    )
    config = toml.tool.nonebot

    driver = nonebot.get_driver()
    for ad in config.adapters:
        driver.register_adapter(importlib.import_module(ad.module_name).Adapter)

    for pl in config.plugins:  # load plugins in order
        nonebot.load_plugin(pl)

    for pd in config.plugin_dirs:
        nonebot.load_plugins(pd)

    for pl in config.builtin_plugins:
        nonebot.load_builtin_plugin(pl)


if __name__ == "__main__":
    prepare()
    nonebot.run()
