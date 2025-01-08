<!-- markdownlint-disable MD031 MD033 MD036 MD041 -->

<div align="center">

<a href="https://cli.nonebot.dev/">
  <img src="https://cli.nonebot.dev/logo.png" width="200" height="200" alt="NoneBotCliPluginLogo">
</a>

<p>
  <img src="https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/template/cli.svg" alt="NoneBotCliPluginText">
</p>

# NB-Cli-Plugin-Bootstrap

_✨ NoneBot2 更实用的初始项目新建工具 ✨_

<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">
<a href="https://pdm.fming.dev">
  <img src="https://img.shields.io/badge/pdm-managed-blueviolet" alt="pdm-managed">
</a>
<a href="https://wakatime.com/badge/user/b61b0f9a-f40b-4c82-bc51-0a75c67bfccf/project/018c33e5-66c5-4aee-ad15-2d9104d177c4">
  <img src="https://wakatime.com/badge/user/b61b0f9a-f40b-4c82-bc51-0a75c67bfccf/project/018c33e5-66c5-4aee-ad15-2d9104d177c4.svg" alt="wakatime">
</a>

<br />

<a href="https://pydantic.dev">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/template/pyd-v1-or-v2.json" alt="Pydantic Version 1 Or 2" >
</a>
<a href="./LICENSE">
  <img src="https://img.shields.io/github/license/lgc-NB2Dev/nb-cli-plugin-bootstrap.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nb-cli-plugin-bootstrap">
  <img src="https://img.shields.io/pypi/v/nb-cli-plugin-bootstrap.svg" alt="pypi">
</a>
<a href="https://pypi.python.org/pypi/nb-cli-plugin-bootstrap">
  <img src="https://img.shields.io/pypi/dm/nb-cli-plugin-bootstrap" alt="pypi download">
</a>

</div>

## 💿 安装

```shell
nb self install nb-cli-plugin-bootstrap
```

## 🎉 使用

### 创建一个更实用的 NoneBot2 初始项目

```shell
nb bootstrap
nb bs
```

<details>
<summary>效果图（点击展开）</summary>

![效果图](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/cli-bootstrap/bootstrap.png)

</details>

### 更新当前文件夹项目中的所有适配器和插件

```shell
nb update-project
nb up
```

<details>
<summary>效果图（点击展开）</summary>

![效果图](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/cli-bootstrap/update-project1.png)
![效果图](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/cli-bootstrap/update-project2.png)

</details>

### 快速修改全局 pip 的 PyPI 镜像源配置

```shell
nb pip-index
nb pi
```

<details>
<summary>效果图（点击展开）</summary>

![效果图](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/cli-bootstrap/pip-index.png)

</details>

### 进入当前项目的虚拟环境

```shell
nb shell
nb sh
```

<details>
<summary>效果图（点击展开）</summary>

![效果图](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/cli-bootstrap/shell.png)

</details>

## 📞 联系

QQ：3076823485  
Telegram：[@lgc2333](https://t.me/lgc2333)  
吹水群：[1105946125](https://jq.qq.com/?_wv=1027&k=Z3n1MpEp)  
邮箱：<lgc2333@126.com>

## 💰 赞助

**[赞助我](https://blog.lgc2333.top/donate)**

感谢大家的赞助！你们的赞助将是我继续创作的动力！

## 📝 更新日志

### 0.5.0

- 现在支持调用 `uv` 安装依赖，以及可以识别使用 `uv` 安装的 Python 了
- 添加 `nb venv` 指令用于显示激活虚拟环境的指令，同时修改 `nb shell` 指令为转向使用 `nb venv` 指令的提示
- 给 `nb bootstrap` 指令填加了一些新的选项，现在 `-y` 选项默认不安装适配器，请使用 `-a` 选项来指定要安装的适配器
- 删除了安装 WebUI 的功能
- 项目模板微调，删除了 Linux 下的快速脚本，推荐直接使用 `nb` 子命令进行操作

### 0.4.0

- 创建虚拟环境时可选使用哪一个 Python
- 不创建虚拟环境时也会提示是否安装依赖了
- `nb shell` 当已处在虚拟环境内时会输出提示，并不会再开一层 Shell 了
- 微调项目模板

### 0.3.1

- 修复无法配置 WebUI

### 0.3.0

- 添加 `nb pip-index` 与 `nb shell` 命令
- 为部分指令新增 `-v` 选项用于输出更多信息
- 微调项目模板

### 0.2.0

- 适配 Pydantic V1 & V2
- 可能再次修复了更新所有插件后统计归类不正确的问题

### 0.1.6

- 修复由于下划线横线不统一导致的显示错误

### 0.1.5

- 更新项目的总结会显示包更新前的版本号
- 给指令添加了别名
- 新增选项 `-y`，可以跳过大部分询问，直接使用默认值
- 微调项目模板

### 0.1.4

- 更新所有插件后如果有失败项会询问是否重试
- 新增部分 pip 安装错误原因分析
- 重构部分逻辑
- 微调项目模板 `.env.prod` 文件中的 `DRIVERS` 配置

### 0.1.3

- 加入了设置 pip 镜像源的选项
- 其他小修改

### 0.1.2

- 微调项目模板和创建项目步骤

### 0.1.1

- 修复版本号显示不正确的 Bug
