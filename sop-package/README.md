# 怎么用这个包

Kevin 你好,这个包就是今晚的全套 SOP + 所有代码文件。使用方法如下。

## 第一步:把整个包放到 Mac 上

把整个 `sop-package/` 文件夹**原封不动**放到 `~/Personal/brain/` 下。

最终路径应该是:

```
~/Personal/brain/sop-package/
  ├── README.md(本文件)
  ├── SOP-全端闭环与容器搭建.md(主 SOP)
  └── files/
      ├── bot.py
      ├── bot-with-brain.py
      ├── com.kevin.brainbot.plist
      ├── CLAUDE.md
      ├── .env.template
      └── .gitignore
```

## 第二步:在 VS Code 里开 Claude Code

1. VS Code 打开 `~/Personal/brain/` 作为工作区
2. 打开 Claude Code 插件(或终端里 `cd ~/Personal/brain && claude`)

## 第三步:让 Claude Code 执行 SOP

直接粘贴这段话给它:

> 请读取 `sop-package/SOP-全端闭环与容器搭建.md`,按照 SOP 里的 Phase 1 → Phase 5 顺序执行。每个 Phase 完成后停下来,用清晰的格式告诉我当前进度 + 需要我验证的动作(里程碑)。等我回"通了"或"ok"你再进下一 Phase。
>
> 执行时参考 `sop-package/files/` 目录下的文件作为源文件(`bot.py`、`bot-with-brain.py`、plist、CLAUDE.md 等),按 SOP 的指引把它们复制到正确位置。
>
> 涉及我需要手动填的东西(Token、API Key),你要明确告诉我填在哪个文件的哪一行,我自己去填,不要问我要明文。
>
> 遇到报错立刻停下汇报,不要自行尝试超过三次修复。

## 第四步:按里程碑验证

整个流程有 5 个里程碑,每个里程碑你只需要:
- 按 Claude Code 的提示做一个验证动作(手机发条消息、打开 Obsidian 看一眼等)
- 告诉它"通了"或"不对,XXX"

你不需要记任何命令、不需要手动敲任何代码。

## 里程碑一览

| Phase | 里程碑 | 你要做的验证 |
|---|---|---|
| 1 | bot 用 .env 配置正常跑 | 手机发消息,bot 回 ✅ |
| 2 | launchd 常驻 | 关终端后手机发消息,仍收到 ✅ |
| 3 | Obsidian 容器 | Obsidian 能看到 inbox 新文件 |
| 4 | Telegram 跟 Claude 对话 | 手机发 `/ask 我最近在想什么`,收到有意义的回答 |
| 5 | 收尾 + Git | `brain` 仓库已 commit |

## 跑完之后

- 手机有任何想法,Telegram 发给 bot → inbox 自动归档
- 想问 AI → `/ask xxx`,Telegram 里直接对话
- 打开 Obsidian → 所有东西一目了然
- 换电脑 → `git clone brain` 仓库 + 重跑 SOP 的 Phase 1-2-4,半小时恢复

---

如果 Claude Code 卡住了或者你觉得不对,随时回到我们 Claude 对话(我这边)找我,把报错或现象发给我,我帮你判断。
