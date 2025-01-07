import subprocess
import click
import os

async def shell_handler():
    """Handle 'nb shell' command, print output of 'poetry env activate'."""
    try:
        # 获取当前目录
        current_dir = os.getcwd()
        
        # 执行 poetry env activate 命令
        result = subprocess.run(
            ["poetry", "env", "activate"],
            cwd=current_dir,
            check=True,  # 确保命令执行成功
            capture_output=True,  # 捕获标准输出和标准错误输出
            text=True,  # 输出为文本格式
        )
        
        # 获取 poetry env activate 的输出
        activate_command_output = result.stdout.strip()  # 去除多余的空格和换行
        
        # 如果命令输出不为空，高亮显示命令
        if activate_command_output:
            click.echo(f"命令: {click.style(activate_command_output, fg='green')}")  # 高亮显示命令
        
        # 输出提示信息（另起一行）
        click.echo(
            "在新版Poetry中，为了提高兼容性，删去了自动进入Python虚拟环境的代码，所以您需要手动执行上述代码进入Python虚拟环境。"
            f"本命令 {click.style('nb shell', fg='green')} 与 {click.style('poetry env activate', fg='green')} 等价"
        )
        click.echo(
            f"在Python虚拟环境中，执行：{click.style('deactivate', fg='green')} 可以退出"
        )
            
    except subprocess.CalledProcessError as e:
        # 如果命令执行失败，捕获异常并输出错误信息
        click.secho(
            f"运行 'poetry env activate' 时出错: {e}",
            fg="red", bold=True, err=True
        )
    except Exception as e:
        # 其他未知错误
        click.secho(
            f"发生未知错误: {e}",
            fg="red", bold=True, err=True
        )
