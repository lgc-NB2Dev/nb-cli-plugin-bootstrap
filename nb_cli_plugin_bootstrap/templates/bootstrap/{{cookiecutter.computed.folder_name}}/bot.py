#!/usr/bin/env python3

import importlib
from pathlib import Path

import nonebot

try:
    import tomllib  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:
    import tomli as tomllib

nonebot.init()

driver = nonebot.get_driver()

# region load project info
data = tomllib.loads(Path("pyproject.toml").read_text(encoding="u8"))
nonebot_data = data.get("tool", {}).get("nonebot")
assert nonebot_data is not None, "Cannot find '[tool.nonebot]' in project toml file!"
assert isinstance(nonebot_data, dict), "[tool.nonebot] must be a table"

adapters = nonebot_data.get("adapters", [])
plugins = nonebot_data.get("plugins", [])
plugin_dirs = nonebot_data.get("plugin_dirs", [])
builtin_plugins = nonebot_data.get("builtin_plugins", [])
assert isinstance(adapters, list), "adapters must be a list of adapter info"
assert isinstance(plugins, list), "plugins must be a list of plugin name"
assert isinstance(plugin_dirs, list), "plugin_dirs must be a list of directories"
assert isinstance(builtin_plugins, list), "builtin_plugins must be a list of plugin name"
# endregion

# region load adapters and plugins
for ad in adapters:
    assert isinstance(ad, dict), "adapter info must be a table"
    assert (md := ad.get("module_name")), "adapter must have a module_name"
    driver.register_adapter(importlib.import_module(md).Adapter)
for pl in plugins:  # load plugins in order
    nonebot.load_plugin(pl)
for pd in plugin_dirs:
    nonebot.load_plugins(pd)
for pl in builtin_plugins:
    nonebot.load_builtin_plugin(pl)
# endregion

nonebot.run()
