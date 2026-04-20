# SOP:全端闭环 + 容器搭建

> 执行者:Mac 上的 Claude Code
> 使用者:Kevin
> 目标:今晚一次性把顶层架构跑通,包含 (1) Telegram bot launchd 常驻 (2) Obsidian 容器 (3) Telegram ↔ Claude 对话闭环

---

## 执行须知(给 Mac 上的 Claude Code 看)

- 严格按本文件顺序执行,每个 Phase 完成后主动跟用户汇报里程碑,等用户确认再进入下一 Phase
- 遇到报错立刻停下汇报,不要自行修复尝试三轮以上
- 涉及密钥/Token 的操作只指导用户自己填,不要主动问用户要明文
- 工作目录:`~/Personal/brain/`(已存在)
- 用户 macOS 用户名:`admin`
- Python 绝对路径:`/opt/homebrew/bin/python3`
- 用户 Home:`/Users/admin`

---

## 当前已完成的部分(不要重做)

- [x] `~/Personal/brain/` 目录已建,含 inbox / knowledge / projects / ops / journal / publish 子目录
- [x] `~/Personal/brain/ops/bot.py` 已存在,基础 Telegram bot 可跑
- [x] `~/Personal/brain/ops/venv/` 虚拟环境已建,装了 `python-telegram-bot`
- [x] Telegram bot `@Kevin_opc_bot` 已创建,User ID `1532059589`
- [x] 手动运行 bot 时,手机发消息能收到 ✅ 已入库并生成 inbox md 文件

## 当前未完成 / 待修复的部分

- [ ] `.env` 方案未落地(token 还在 export 里,launchd 起来读不到)
- [ ] `bot.py` 未改造为读 .env(还在用 `os.environ[]`)
- [ ] launchd plist 未创建
- [ ] Obsidian 未安装
- [ ] "大脑"进程未搭建(Telegram 消息不会被 Claude 自动回复)

---

## Phase 1:修复 bot 的配置读取(.env 方案)

**目标**:让 bot 脚本从 `.env` 文件读 token,不依赖终端 export。这是 launchd 能跑起来的前提。

### 1.1 装 python-dotenv

```bash
cd ~/Personal/brain/ops
source venv/bin/activate
pip install python-dotenv
```

### 1.2 建 .env 文件(指导用户填,不要主动写 token)

在 `~/Personal/brain/ops/.env` 建文件,内容:

```
BOT_TOKEN=请Kevin自己填入BotFather最新给的token
MY_USER_ID=1532059589
```

**执行规则**:文件 Claude Code 可以创建,但 `BOT_TOKEN=` 后面就写 `请Kevin自己填入BotFather最新给的token` 这个占位符,让用户手动替换。**不要问用户要 token 明文**。

### 1.3 建/更新 .gitignore

在 `~/Personal/brain/ops/.gitignore`:

```
.env
venv/
__pycache__/
*.log
```

### 1.4 改造 bot.py

把 `~/Personal/brain/ops/bot.py` 替换为本 SOP 包里的 `files/bot.py`(见附件)。

关键变化:
- import 增加 `from dotenv import load_dotenv`
- 脚本开头 `load_dotenv(Path(__file__).parent / ".env")`
- 其余逻辑保持,支持文字/语音/图片/文件/链接入库

### 1.5 里程碑 1:前台验证

指导用户:
1. 确认 `.env` 里 `BOT_TOKEN=` 后面已经替换成真 token 了
2. 终端跑:
   ```bash
   cd ~/Personal/brain/ops
   source venv/bin/activate
   python bot.py
   ```
3. 看到 `Bot 启动中...` 输出
4. 手机 Telegram 发一条 "phase 1 测试",bot 回 ✅ 已入库
5. `cat ~/Personal/brain/inbox/` 里最新的 .md,内容是 "phase 1 测试"

**用户确认"通了"后**,Ctrl+C 停掉手动运行的 bot,进入 Phase 2。

---

## Phase 2:launchd 常驻

**目标**:bot 脱离终端,开机自启,崩溃自重启。

### 2.1 复制 plist

把本 SOP 包里的 `files/com.kevin.brainbot.plist` 复制到:

```
~/Library/LaunchAgents/com.kevin.brainbot.plist
```

### 2.2 加载

```bash
launchctl load ~/Library/LaunchAgents/com.kevin.brainbot.plist
launchctl list | grep brainbot
```

能看到一行 PID 就是起来了。

### 2.3 里程碑 2:压力测试

指导用户按顺序做:
1. 手机 Telegram 发 "launchd 测试 1",应收到 ✅
2. **关闭所有终端窗口**,再发 "launchd 测试 2",应收到 ✅
3. 看日志:`tail -20 ~/Personal/brain/ops/bot.log`
4. (可选,今晚不做也行)重启 Mac 后不做任何操作直接发消息测自启

**用户确认"独立跑通"后**,进入 Phase 3。

### 常用运维命令(写入本 SOP,让用户留存)

```bash
# 状态
launchctl list | grep brainbot

# 停止
launchctl unload ~/Library/LaunchAgents/com.kevin.brainbot.plist

# 启动
launchctl load ~/Library/LaunchAgents/com.kevin.brainbot.plist

# 改代码后重启
launchctl unload ~/Library/LaunchAgents/com.kevin.brainbot.plist
launchctl load ~/Library/LaunchAgents/com.kevin.brainbot.plist

# 看日志
tail -f ~/Personal/brain/ops/bot.log
tail -f ~/Personal/brain/ops/bot.err.log
```

---

## Phase 3:Obsidian 容器

**目标**:把 `~/Personal/brain/` 变成一个可视化容器。

### 3.1 安装

指导用户:
1. 下载:https://obsidian.md/
2. 拖进 Applications
3. 打开 Obsidian → "Open folder as vault" → 选择 `/Users/admin/Personal/brain`
4. 确认左侧 sidebar 能看到 inbox / knowledge / projects 等目录

### 3.2 基础配置(不强求,用户后面可自行调)

- Settings → Files & Links → Default location for new notes → `inbox`
- 启用 Core Plugin:Graph view, Backlinks, Outgoing links, Tag pane
- **不要**建议用户装 Git 插件(会和 Claude Code 的 commit 冲突,等稳定后再评估)

### 3.3 里程碑 3

指导用户:
1. 手机 Telegram 发 "obsidian 测试"
2. Obsidian 侧边栏 inbox 目录下应立刻出现新 md 文件
3. 点进去能看到 frontmatter + 正文

**用户确认"看到了"后**,进入 Phase 4。

---

## Phase 4:Telegram ↔ Claude 对话闭环(大脑进程)

**目标**:用户在 Telegram 发消息,自动调 Claude API,回复推回 Telegram。这是全端闭环真正闭合的一步。

### 4.1 架构说明(执行前先让用户理解)

- 方案:改造现有 bot,消息进来时根据**前缀**路由
- 默认行为(无前缀):**只存不答**,保持现有 inbox 捕获能力
- 前缀 `/ask` 或 `@`:调 Claude API,把回答写回 Telegram + 同时存到 `~/Personal/brain/journal/` 留档

**为什么这样设计**:
- 快速捕获想法时不想被 AI 插嘴(保留"静默秘书"能力)
- 明确问问题时才走 AI(省 token,也避免误触发)

### 4.2 Claude API Key 获取

指导用户:
- 访问 https://console.anthropic.com/
- 用**个人邮箱**注册(不要用 Longbridge 公司邮箱,这是独立的个人 API 账号,和 Team Plan 无关)
- Settings → API Keys → Create Key
- 复制 key(`sk-ant-api03-...`),填入 `~/Personal/brain/ops/.env`:

```
ANTHROPIC_API_KEY=请Kevin自己填
```

**重要提示给用户**:
- Anthropic API 按用量付费,和 Claude Pro/Team 订阅独立计费
- 个人 API 账号会给你 $5 免费额度,用完再充值
- 这一步如果用户暂时不想建 API 账号,可以跳过 Phase 4,停在 Phase 3 也是完整的捕获闭环

### 4.3 装 anthropic SDK

```bash
cd ~/Personal/brain/ops
source venv/bin/activate
pip install anthropic
```

### 4.4 替换 bot.py 为增强版

把本 SOP 包里的 `files/bot-with-brain.py` 覆盖 `~/Personal/brain/ops/bot.py`。

关键增强:
- 检测消息前缀 `/ask` 或 `@`
- 命中时调 claude-opus-4-5(或 sonnet,见脚本配置)
- 带上 CLAUDE.md 和最近 inbox 作为上下文
- 回答推回 Telegram
- 对话留档到 `journal/YYYY-MM-DD.md`

### 4.5 重载 launchd

```bash
launchctl unload ~/Library/LaunchAgents/com.kevin.brainbot.plist
launchctl load ~/Library/LaunchAgents/com.kevin.brainbot.plist
```

### 4.6 里程碑 4(终极验证)

指导用户:
1. 手机 Telegram 发 "记一下,我想做播客",bot 回 ✅ 已入库(**只存不答**)
2. 手机 Telegram 发 "/ask 我刚才说想做什么?",bot 调 Claude,回复"你想做播客"(**对话闭环**)
3. Obsidian 侧 `journal/` 下出现今日对话记录
4. `inbox/` 下也有对应 md

至此全端闭环完成。

---

## Phase 5:收尾

### 5.1 建 CLAUDE.md

在 `~/Personal/brain/CLAUDE.md` 写入基础上下文(本 SOP 包里的 `files/CLAUDE.md`)。Claude Code 和 Phase 4 的大脑进程都会读这个文件。

### 5.2 初始化 Git

```bash
cd ~/Personal/brain
git init
git add .
git commit -m "init: 全端闭环与容器搭建完成"
```

建议用户在 GitHub 建 private repo `brain`,然后:

```bash
git remote add origin git@github.com:用户名/brain.git
git push -u origin main
```

### 5.3 最终里程碑

- [ ] 手机 Telegram 发消息 → Mac inbox 有文件
- [ ] launchd 独立跑,关终端不影响
- [ ] Obsidian 打开 brain 能看到一切
- [ ] `/ask` 能在 Telegram 里跟 Claude 对话
- [ ] 整个 brain 仓库已 commit,可迁移

---

## 故障排查(给 Claude Code 参考)

### bot 不响应
1. `launchctl list | grep brainbot` 看 PID
2. `tail -50 ~/Personal/brain/ops/bot.err.log` 看错误
3. 常见错误:
   - `KeyError: 'BOT_TOKEN'` → .env 没建好或路径不对
   - `Unauthorized` → token 错,让用户重新从 BotFather 拿
   - `ModuleNotFoundError` → venv 没激活或依赖没装

### /ask 无响应
1. 确认 `.env` 里 `ANTHROPIC_API_KEY` 已填
2. `tail -50 ~/Personal/brain/ops/bot.err.log` 看 API 报错
3. 常见:额度耗尽、key 无效、网络(需确认 api.anthropic.com 可达)

### launchd 加载失败
1. `launchctl load` 不报错不代表成功,要 `launchctl list | grep brainbot` 验证
2. plist 里路径必须是绝对路径,变量不展开
3. plist 改动后必须 unload + load,不能只 load

---

## 边界:今晚不做的事(记住别扩散)

- 语音转录(whisper)
- 链接抓取与总结
- 定时汇报 / 主动推送
- inbox 自动归档
- 多设备 Git 同步
- VPS / Mac mini 迁移

这些都是未来的事,今晚就是顶层架构跑通,不要扩散。
