# WorkBuddy Daily Credits

一个非官方的 WorkBuddy 每日赠送积分领取工具：直接调用桌面端使用的服务接口，不启动模型、不截图、不模拟点击。

> This is an unofficial community project and is not affiliated with Tencent or WorkBuddy.

## 特点

- 零模型调用，因此定时任务本身不消耗 AI token 或 WorkBuddy 任务积分
- 先查询状态，只有尚未领取时才提交
- 重复执行安全，已领取会返回 `ALREADY_CLAIMED`
- 只使用 Python 标准库，无需安装依赖
- macOS LaunchAgent 定时执行，WorkBuddy 窗口无需保持打开
- 不复制、不保存、不打印 access token

## 要求

- macOS
- Python 3
- WorkBuddy 已在本机登录且会话仍有效
- 当前存在可领取的每日赠送积分活动

## 安装为 WorkBuddy Skill

```bash
mkdir -p ~/.workbuddy/skills
cp -R workbuddy-daily-credits ~/.workbuddy/skills/
```

然后可以在 WorkBuddy 中要求“领取今日积分”，或直接运行：

```bash
python3 ~/.workbuddy/skills/workbuddy-daily-credits/scripts/claim_daily_credit.py --claim --json
```

只查询状态：

```bash
python3 ~/.workbuddy/skills/workbuddy-daily-credits/scripts/claim_daily_credit.py --status --json
```

## 每日自动领取

默认每天 `00:30` 执行：

```bash
python3 ~/.workbuddy/skills/workbuddy-daily-credits/scripts/install_launch_agent.py
```

指定时间，例如每天 `08:15`：

```bash
python3 ~/.workbuddy/skills/workbuddy-daily-credits/scripts/install_launch_agent.py --hour 8 --minute 15
```

卸载定时任务：

```bash
python3 ~/.workbuddy/skills/workbuddy-daily-credits/scripts/install_launch_agent.py --uninstall
```

日志位置：`~/.workbuddy/logs/daily-credits.log`

## 工作原理与安全边界

脚本在运行时读取 WorkBuddy 已有的本地登录会话，只向 `https://copilot.tencent.com` 发送 WorkBuddy 所需的认证请求。目标域名经过严格校验，防止凭证被发送到其他主机。

它只实现两种操作：查询每日领取状态，以及领取当前账号的每日赠送积分。不会自动发布内容、邀请用户或完成其他成长任务。

请勿在 Issue 中上传 WorkBuddy 的认证文件、完整日志或任何访问令牌。更多说明见 [SECURITY.md](SECURITY.md)。

## 注意

- 接口并非公开稳定 API，WorkBuddy 更新后可能失效。
- 退出登录或会话过期后，需要重新打开 WorkBuddy 登录。
- 活动结束时脚本返回 `INACTIVE`，不会循环请求。
- 使用前请确认符合你所在地法律及 WorkBuddy 的服务条款。

## License

[MIT](LICENSE)
