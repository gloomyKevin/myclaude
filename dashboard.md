---
type: dashboard
pinned: true
---

# Inbox 工作台

> 本页依赖 Dataview 插件。未装看见的是原生代码块,装好 + 重载后会变成动态表格。

---

## 今天进来的

```dataview
TABLE WITHOUT ID file.link AS "条目", type AS "类型", dateformat(file.mtime, "HH:mm") AS "时间"
FROM "inbox"
WHERE file.mtime >= date(today)
SORT file.mtime DESC
```

---

## 未处理(`status: unprocessed`)

```dataview
TABLE WITHOUT ID file.link AS "条目", type AS "类型", (date(today) - date(file.mtime)).days AS "天前"
FROM "inbox"
WHERE status = "unprocessed"
SORT file.mtime DESC
LIMIT 30
```

---

## 3 天以上未动(待催办)

```dataview
LIST
FROM "inbox"
WHERE status = "unprocessed" AND (date(today) - date(file.mtime)).days > 3
SORT file.mtime ASC
```

---

## 最近 7 天按类型分布

```dataview
TABLE WITHOUT ID type AS "类型", length(rows) AS "数量"
FROM "inbox"
WHERE file.mtime >= date(today) - dur(7 days)
GROUP BY type
SORT length(rows) DESC
```

---

## 工作流说明

- **处理完一条 inbox**:把其 frontmatter 里的 `status: unprocessed` 改成 `status: archived`(或归档到 knowledge/projects 再删除)。处理后它就会从上面列表里消失
- **新增 status 值**:`archived`(已归档) / `noise`(废弃) / `in-progress`(处理中)
- **加标签**:可以在 frontmatter 加 `tags: [产品, 播客]`,之后用 `#tag` 查
