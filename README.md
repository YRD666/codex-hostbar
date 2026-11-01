# Codex Hostbar

[English](README.en.md) · MIT · Linux · Python 标准库

**把 Codex 状态和服务器资源固定在底部相邻两行。**

```text
 GPT-Example high · weekly 80% left · Context 100% left  ⚠ 2 warnings · f2
 demo-server | 内存 3.2/8.0 GiB 40% | 根盘 24.0/80.0 GiB 30% | 数据盘 40.0/100.0 GiB 40%
```

以上是示例数据。Codex 原生状态栏和快捷键提示常占两行，另加主机监控后变成三行；内联模式下，它们又可能被空白区域隔开。Hostbar 用独立 tmux 会话把已识别的两行原生页脚合并成一行，下一行显示主机资源。终端变窄时压缩单位和标签，再按显示宽度截断。

这是社区工具，与 OpenAI 无隶属关系。不包含 Codex 二进制；你需要自行安装和登录 Codex。

## 功能

- 模型、推理级别、周配额、上下文、Token 用量与警告合并显示；内容以 Codex 实际提供的信息为准。
- 内存、根盘和可选数据盘实时显示，支持中文和英文标签。
- 外层状态文字为白色，Codex 状态颜色关闭；不会把整个聊天界面强制变成白色。
- `F2` 查看警告；`Shift+PageUp` 进入 tmux 历史，`q` 返回。
- `Ctrl+Z` 关闭当前 Hostbar 终端会话。**这不是 Unix 挂起**，不能用 `fg` 恢复；需要时用 `codex-hostbar -- resume --last` 重开。不会主动停止 Codex 共享后台服务或其他 tmux 会话。
- 不修改全局 tmux 配置、Codex 配置文件、网络或代理设置，不读取登录凭据。原有代理环境或 Codex 启动包装器继续生效。

## 要求和兼容性

Linux、Python **3.10+**、tmux **3.4+**、UTF-8 终端，以及已可独立运行的 Codex CLI。

真实运行验证环境：Ubuntu 24.04、Python 3.12、tmux 3.4、Codex CLI **0.166.0**。其他 Codex 版本尚未逐个验证；本项目依赖该版本的全屏选项和英文页脚文本结构。若上游改变结构，Hostbar 会保留完整原生视口，可能重新出现额外的原生状态行，而不会继续折叠未知界面。中文、ASCII 和普通符号按终端单元格计算，复杂 emoji 的宽度仅近似支持。

建议终端至少 80 列。更窄时仍维持两条外层状态行，但可能截断部分信息；小于 35 列或 10 行时停用原生页脚折叠。菜单和历史模式在下一次刷新（约 1 秒）恢复完整视口。弹出面板时外层第一行暂显示 `Codex`。

## 安装

Debian/Ubuntu 先安装依赖（其他发行版使用自己的包管理器）：

```bash
sudo apt-get install python3 tmux
git clone https://github.com/YRD666/codex-hostbar.git
cd codex-hostbar
python3 install.py
~/.local/bin/codex-hostbar
```

安装脚本自身不联网、不需要 root，只复制明确列出的项目文件到 `~/.local/share/codex-hostbar`，创建 `~/.local/bin/codex-hostbar`。已有同名文件时停止，不覆盖。若该目录已在 `PATH` 中，可直接运行 `codex-hostbar`。原来的 `codex` 命令保持可用。

也可以不安装，直接运行 `python3 hostbar.py`。升级时先退出 Hostbar 会话，使用相同 prefix 卸载旧版，再安装新版。

## 使用

```bash
# 原有 Codex 从 PATH 查找
codex-hostbar

# 自定义主机标签、数据盘路径和语言
codex-hostbar --host-label demo-server --data-path /mnt/data --language zh
codex-hostbar --language en

# Codex 参数放在 -- 后面；支持模型、提示词、resume/fork 等
codex-hostbar -- -m your-model
codex-hostbar -- resume --last
codex-hostbar -- 'Explain this repository'

# 指定原有 Codex 可执行文件或启动包装器，保留原有网络设置
codex-hostbar --codex /path/to/original/codex

# 隐藏数据盘行中的数据盘字段
codex-hostbar --data-path ''
```

不指定数据盘路径时，仅在 `/srv` 本身为挂载点时显示它。显式路径显示其所在文件系统的容量，并非该目录自身占用。根盘百分比与 `df` 一样考虑文件系统保留块，可能不同于显示的 used/total 比值。

| 环境变量 | 对应参数 / 用途 |
| --- | --- |
| `CODEX_HOSTBAR_CODEX` | `--codex`；默认在 PATH 中查找 `codex` |
| `CODEX_HOSTBAR_LABEL` | `--host-label`；默认系统主机名 |
| `CODEX_HOSTBAR_DATA_PATH` | `--data-path`；空字符串隐藏数据盘 |
| `CODEX_HOSTBAR_LANGUAGE` | `--language`；`zh`（默认）或 `en` |
| `CODEX_HOSTBAR=0` | 直接运行原有 Codex，绕过 Hostbar |

在非 TTY、已有 tmux 会话或 `TERM=dumb` 中启动时，直接透传给 Codex。`exec`、`review`、`login` 等非交互子命令也透传；此类子命令应紧跟 `--`，其选项放在子命令之后。

交互启动通过 `-c` 传入显示选项：全屏、启用 alternate screen、关闭 raw output 和状态颜色、使用 github 主题，以及模型/周配额/上下文/用量四项状态。它们只对这次启动生效，不写入你的配置文件。用户在 `--` 后提供的显示覆盖可能改变两行效果；模型、认证和网络设置由原有 Codex 处理。

## 卸载

在源码目录中执行：

```bash
python3 install.py --uninstall
# 自定义安装位置时，安装和卸载使用同一个 prefix
python3 install.py --prefix /your/prefix
python3 install.py --prefix /your/prefix --uninstall
```

卸载会校验安装清单及文件哈希；文件若被自行修改，会停止并保留它们。不会删除原有 Codex、配置、历史记录，也不会修改 shell 启动文件。

## 开发与验证

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_public.py
```

测试包含显示宽度、警告保留、菜单保护、资源计算、安装/卸载、特殊路径及参数透传。Linux + tmux 下还用模拟 Codex 进行真实 PTY 测试，无需登录凭据或 API 请求。这个测试不能代替真实 Codex 版本兼容验证。

更多实现说明见 [docs/architecture.md](docs/architecture.md)，发布检查见 [docs/releasing.md](docs/releasing.md)。问题反馈请提供版本、终端尺寸和经过脱敏的复现步骤，不要提交聊天记录、登录文件或完整环境变量。

## 许可证

[MIT](LICENSE)。
