# Outreach 插件

> 求职触达工具集 —— 根据 JD 与个人经历生成高回复率的打招呼语，规划扩展自动打招呼、自动投递简历与回复跟踪。

## 技能列表

| 技能 | 说明 | 触发方式 |
|------|------|---------|
| `gen-greeting` | 根据 JD 和个人经历材料生成打招呼语（主推版 + 超短版），内置证据分级匹配分析、平台最佳实践联网核查与自检清单 | "生成打招呼语" / "写打招呼" / "求职开场白" |

## 安装

```bash
# 通过 Marketplace（推荐）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon
/plugin install outreach@poseidon

# 或本地路径安装
/plugin install ./plugins/outreach
```

## gen-greeting 工作流

1. **收集输入**：JD（必需）+ 经历材料（简历或项目笔记；用户指定的经历文件优先）
2. **匹配分析**：JD 逐条拆解，按「商业交付 > 自研 > 学习」「职责同构 > 技术栈相似」「数字 > 形容词」选出唯一最匹配项
3. **联网核查**：搜索目标平台当前打招呼语最佳实践（可跳过，回退到沉淀标准）
4. **生成**：主推版（100-130 字）+ 超短版（70-80 字），证据先行、术语为 HR 降维、匹配断言只放结尾
5. **自检输出**：9 条自检清单逐项核对，输出附调整逻辑说明

标准沉淀在 `skills/gen-greeting/references/`：

- `greeting-principles.md` — 写作标准（证据先行、结构公式、禁止清单、发送时机）
- `greeting-templates.md` — 模板库（主推/超短/自研钩子变体/展开版/跟进版，含真实案例改前改后对照）

## Roadmap

- [ ] `auto-greet` — 对接招聘平台，按 gen-greeting 标准批量生成并发送打招呼语
- [ ] `send-resume` — 打招呼通过后自动投递简历
- [ ] `reply-tracker` — 跟踪已读/回复状态，定时跟进已读不回的会话
