from nonebot import on_command
from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="Ping",
    description="超级用户 Ping 指令回复，用于检查 Bot 是否存活",
    usage="指令：ping",
    homepage=None,
    type="application",
    config=None,
    supported_adapters=None,
)


cmd_ping = on_command("ping", aliases={"Ping", "PING"}, permission=SUPERUSER)


@cmd_ping.handle()
async def _(matcher: Matcher, _: Event):
    await matcher.finish("Pong~")
