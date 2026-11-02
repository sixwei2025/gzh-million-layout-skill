# 汇芯 gzh-design（评测号 2号排版）

## 愿景

评测号 = **极好用 / 高价值 / 高设计感** 的全自动 AI 评测公众号工作流。

只走三条轨：

1. **汇芯红六套骨架**（本目录）— 主色 `#C8102E`，按天轮换，不问主题  
2. **乱码硬闸** — `sanitize → gate → gzh_design_pack_bundle` → 只进草稿箱  
3. **写作 skill** — `ai-tool-review-writing` + 评测号写作硬闸（选题→大纲→正文→推箱）

**已废弃**：评测号流程里的「1号排版 / heijin 黑金」。主号若仍用 heijin，与评测号无关。

## 与上游关系

| | 路径 |
|--|------|
| 上游只读 | `/workspace/gzh-skill/v2/vendor/gzh-design-skill/references/` |
| 公司自有（本目录） | `/workspace/gzh-skill/v2/huixin-gzh-design/` |

上游提供六套**骨架**（开篇组件/密度/装饰/字号差异）；本目录只换主色与强调色为汇芯红系，**禁止把六套排成同一套红白**。

## 目录

```
huixin-gzh-design/
  README.md                 # 本说明
  palette.md                # 色板速查
  rotation.md               # 按天轮换
  references/
    theme-index.md
    common-components.md
    theme-magazine-card.md  # ← 摸鱼绿骨架
    theme-classic-edit.md   # ← 红白骨架（#DC2626→#C8102E）
    theme-minimal-line.md   # ← 石墨极简（橙点睛→红）
    theme-zen-space.md      # ← 留白禅意（墨绿→红系）
    theme-ticket.md         # ← 摸鱼票据（绿→红）
    theme-journal.md        # ← 橄榄手记（橙→红）
```

## 轮换规则

见 `rotation.md`：一周 5～7 篇，一天一骨架。Skill `skill-1793168836892` 默认从本目录读主题。

## 接入

- Skill：`sand-workflow:skill-1793168836892`
- 接入短文：`/workspace/gzh-skill/v2/排版-gzh-design接入.md`
- 乱码硬闸：`/workspace/gzh-skill/v2/排版-乱码硬闸.md`
