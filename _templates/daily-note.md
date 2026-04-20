---
date: <% tp.date.now("YYYY-MM-DD") %>
type: daily
tags: [daily]
---

# <% tp.date.now("YYYY-MM-DD dddd") %>

## 今日 inbox 捕获

```dataview
LIST
FROM "inbox"
WHERE dateformat(file.mtime, "yyyy-MM-dd") = "<% tp.date.now("YYYY-MM-DD") %>"
SORT file.mtime DESC
```

## 今日 AI 对话回顾

![[journal/<% tp.date.now("YYYY-MM-DD") %>]]

## 反思

(在这里写今天的观察、决策、顿悟;写一条就行)

## 明日意图

- [ ] 
