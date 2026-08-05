# WorkBuddy Daily Credits 交接与迁移指南

本文用于在删除旧聊天、迁移 Mac 或开启新的 Codex 会话后，继续维护和恢复 WorkBuddy 每日积分自动领取任务。

## 当前方案

- 项目仓库：<https://github.com/95junminhuang/workbuddy-daily-credits>
- 实现方式：Python 标准库脚本 + macOS LaunchAgent
- 默认时间：每天 `00:30`
- 不使用 WorkBuddy Skill，不调用 AI 模型，不消耗模型 token
- WorkBuddy 不需要保持打开，但本机登录会话必须有效
- 定时任务只查询每日赠送积分状态，并在尚未领取时提交一次领取请求

## 本机文件

| 用途 | 路径 |
| --- | --- |
| 已安装运行目录 | `~/.local/share/workbuddy-daily-credits` |
| 领取脚本 | `~/.local/share/workbuddy-daily-credits/claim_daily_credit.py` |
| 安装与卸载脚本 | `~/.local/share/workbuddy-daily-credits/install_launch_agent.py` |
| LaunchAgent | `~/Library/LaunchAgents/com.workbuddy.daily-credits.plist` |
| 日志 | `~/.workbuddy/logs/daily-credits.log` |
| 互斥锁 | `~/.workbuddy/daily-credits.lock` |

安装器会把仓库中的两个脚本复制到独立运行目录。因此，安装完成后，定时任务不依赖仓库目录或 Codex 会话。

## 使用 macOS 迁移助理

完整迁移用户账户时，上述用户目录和 LaunchAgent 通常会一起迁移，但仍需在新 Mac 登录后验证。

1. 登录新 Mac，确认用户主目录是否仍为原路径。
2. 登录 WorkBuddy；迁移后的会话可能因设备或钥匙串变化而失效。
3. 如果项目仓库没有迁移，重新克隆；然后在仓库目录运行安装器：

   ```bash
   git clone https://github.com/95junminhuang/workbuddy-daily-credits.git
   cd workbuddy-daily-credits
   python3 scripts/install_launch_agent.py
   ```

重新运行安装器是幂等操作：它会覆盖运行文件并重新加载同一个 LaunchAgent，不会创建重复任务，也不会立即领取积分。

如果仓库已经迁移，只需进入现有仓库目录执行最后一条安装命令，不要重复克隆。

如果新 Mac 的用户名不同，或者 Python 的安装路径、Mac 架构发生变化，必须重新运行安装器。安装器会用新机器的主目录和 Python 绝对路径重写 plist。

## 干净安装的新 Mac

1. 安装 Python 3，并登录 WorkBuddy。先确认解释器可用：

   ```bash
   python3 --version
   ```

2. 克隆项目并安装定时任务：

   ```bash
   git clone https://github.com/95junminhuang/workbuddy-daily-credits.git
   cd workbuddy-daily-credits
   python3 scripts/install_launch_agent.py
   ```

3. 使用下方命令完成只读验证。

## 只读验证

以下命令不会领取积分：

```bash
plutil -lint ~/Library/LaunchAgents/com.workbuddy.daily-credits.plist
/usr/libexec/PlistBuddy -c 'Print :ProgramArguments:1' ~/Library/LaunchAgents/com.workbuddy.daily-credits.plist
/usr/libexec/PlistBuddy -c 'Print :ProgramArguments:0' ~/Library/LaunchAgents/com.workbuddy.daily-credits.plist
test -x ~/.local/share/workbuddy-daily-credits/claim_daily_credit.py && echo "claim script: OK"
test -x ~/.local/share/workbuddy-daily-credits/install_launch_agent.py && echo "manager: OK"
launchctl print gui/$(id -u)/com.workbuddy.daily-credits
```

预期结果：

- `plutil` 返回 `OK`
- plist 的脚本路径指向 `~/.local/share/workbuddy-daily-credits/claim_daily_credit.py`
- plist 中的 Python 绝对路径在新 Mac 上仍然存在并可执行；否则重新运行安装器
- 两个脚本均显示 `OK`
- `launchctl print` 能找到 `com.workbuddy.daily-credits`
- 等待定时执行时显示 `state = not running` 属于正常状态

这些检查只能证明文件和任务已安装，不能证明 WorkBuddy 登录及服务接口可用。最终成功标准是等待一次计划执行后检查日志：`CLAIMED`、`ALREADY_CLAIMED` 或 `INACTIVE` 表示任务正常完成；`AUTH_REQUIRED`、网络错误或 API 错误表示仍需处理。

查看最近日志：

```bash
tail -n 50 ~/.workbuddy/logs/daily-credits.log
```

## 常见恢复操作

### LaunchAgent 不存在或路径错误

在仓库目录重新安装：

```bash
python3 scripts/install_launch_agent.py
```

### 返回 `AUTH_REQUIRED`

打开 WorkBuddy 并重新登录，然后等待下一次定时执行。不要复制、打印或上传认证文件及访问令牌。

### WorkBuddy 更新后接口失败

保留失败日志中不含凭证的错误信息，在新的 Codex 会话中检查项目脚本。该接口不是公开稳定 API，更新后可能需要适配。

### 两台 Mac 同时保留了任务

两台机器的锁文件互不共享，不能防止跨机器同时请求。即使服务端通常会返回“已领取”，也不要把它当作跨机器防重保证。确认新 Mac 正常后，在旧 Mac 运行：

```bash
python3 ~/.local/share/workbuddy-daily-credits/install_launch_agent.py --uninstall
```

卸载会移除 LaunchAgent 和独立运行目录，日志与锁文件会保留。

如果旧 Mac 暂时无法操作，先将它关机或退出旧机的 WorkBuddy，再启用新 Mac 的任务；无法从这个项目远程卸载另一台机器的 LaunchAgent。

## 避免误触领取

- 不带参数运行 `claim_daily_credit.py` 时，默认行为等同于 `--claim`。
- `--status --json` 不会领取，但会读取登录信息、发起状态查询网络请求并使用本机锁文件。
- 只做迁移检查时，优先使用本文“只读验证”中的命令。

## 新 Codex 会话交接提示

可将以下内容粘贴到新会话：

```text
请接手 WorkBuddy 每日积分自动领取项目：
https://github.com/95junminhuang/workbuddy-daily-credits

当前实现是 Python 标准库脚本加 macOS LaunchAgent，不使用 Skill 或 AI 模型。
运行目录为 ~/.local/share/workbuddy-daily-credits，LaunchAgent 为
~/Library/LaunchAgents/com.workbuddy.daily-credits.plist，默认每天 00:30 执行，
日志为 ~/.workbuddy/logs/daily-credits.log。

请先阅读 HANDOFF.md，再只读检查仓库、本机安装目录、plist 和 LaunchAgent 状态。
不要打印或上传 WorkBuddy token，也不要实际领取积分，除非我明确要求。
如果需要修改，先核对 GitHub main 与本地版本，再测试并通过 PR 发布。
```

## 安全边界

- 不在 Issue、PR、聊天或日志中暴露认证文件、access token 或 refresh token。
- 不自动发布内容、邀请用户、执行成长任务或领取每日赠送积分以外的奖励。
- `ALREADY_CLAIMED` 视为成功，不循环重试。
- 网络错误交给下一次定时任务重试，不进行高频请求。
- 使用前自行确认符合所在地法律以及 WorkBuddy 服务条款。
