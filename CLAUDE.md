# Brain — Kevin 的一人公司主仓库

## 我是谁

- Kevin,正在独立创业,目标:从 0 到 1 建一人公司(OPC)
- 当前仍在 Longbridge 担任前端工程师(过渡期)
- 我的角色是**架构师**——定方向、做决策、验收成果
- 执行——写代码、写文案、做运营——尽量交给 AI 或协作者

## 本仓库的意义

这是我和所有 AI 协作者(Claude Code、Telegram bot 背后的 Claude API、未来的任何 agent)共享的**单一真相源**。

所有重要的信息、决策、草稿、项目状态都应落在这里,不依赖任何云端对话历史。

## 仓库结构

- `inbox/` — 未整理的原料。手机通过 Telegram 发来的所有消息、想法、链接、图片落在这里。状态默认 `unprocessed`
- `knowledge/` — 长期沉淀。经过提炼、可复用的知识、方法论、参考资料
- `projects/` — 各项目子目录。每个项目一个子文件夹,内含策略、设计、执行记录
- `ops/` — 自动化脚本、bot、agent 配置
- `journal/` — 日志。包含 Telegram 与 Claude 的对话留档(按日)
- `publish/` — 待发布到小红书、即刻、Notion 等外部平台的内容草稿

## 协作规则

1. 重要决策和阶段性产出必须落到仓库文件,不要只留在对话里
2. 敏感信息(财务、合同、竞业相关)放本地,不进任何云端对话日志
3. AI 协作者在产出"观察"和"建议"时,应基于仓库事实,不凭空编造
4. 每个 inbox 条目最终都应被处理(归档到 knowledge/projects 或明确废弃),不留烂尾

## Git / 版本控制约定

- 远端:`git@github.com:gloomyKevin/myclaude.git`(private)
- 跟踪策略(决策 B):`inbox/ journal/ ops/venv/ .env *.log` 等不进 git,详见 `.gitignore`
- **自动 push 授权**:Kevin 已授权。AI 协作者完成普通 commit 后应**直接 `git push`**,不必每次确认
- 禁止项(仍需明确确认):`git push --force`、`git reset --hard`、改写远端已有 commit、任何会丢失 Kevin 工作的操作
- commit 本身不自动发起,仍需 Kevin 明确授意

## 当前阶段

2026 年 4 月 — 全端闭环与容器搭建阶段。

优先级:
- 基础设施稳定跑起来(Telegram bot + inbox + Obsidian)
- 6 月过渡到 Mac mini,整套环境可一键迁移

未来阶段(别提前讨论,除非我主动提):
- Solo Product 产品开发
- 内容渠道冷启动

## 风格偏好

- 简洁直接,不绕圈子
- 不要无意义的鼓励和套话
- 观察优先于判断
- 指出我的盲区比附和我更有价值
