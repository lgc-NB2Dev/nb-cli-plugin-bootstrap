import click
import shellingham


async def shell_handler():
    click.echo(
        f"由于一些原因，现已无法通过此命令直接进入虚拟环境\n"
        f"你可以执行 {click.style('nb venv', fg='green')}"
        f"（简写形式 {click.style('nb vv', fg='green')} ）获取进入虚拟环境要执行的命令",
    )

    try:
        shell, _ = shellingham.detect_shell()
    except shellingham.ShellDetectionFailure:
        shell = ""

    quick_cmd = None
    if shell in ["powershell", "pwsh"]:
        quick_cmd = "nb venv | Invoke-Expression"
    elif shell != "cmd":
        quick_cmd = "eval $(nb venv)"

    if quick_cmd:
        click.echo(f"或直接执行这个命令：{click.style(quick_cmd, fg='green')}")
    else:  # cmd
        quick_cmd = 'start powershell -NoExit -Command "nb venv | Invoke-Expression"'
        click.echo(
            "\n"
            "可以使用以下内容替换掉你当前执行的批处理文件中的内容（如果有，右键文件点击编辑）",
        )
        click.secho(quick_cmd, fg="green")
        input("\n" "按回车键退出")
