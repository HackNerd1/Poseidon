# Worker Contract：业务场景分析

## 输入

- 仓库路径：`.Poseidon/repo/<project_name>/`

## 输出

写入 `.Poseidon/repo/<project_name>/analysis/business-scenarios.md`

## 分析目标

1. **识别业务领域**：从目录名、模块名、API 路径、README 中推断项目所属业务领域
2. **提取核心业务场景**（2-5 个）：
   - 从路由定义、Controller、API endpoint 识别核心业务操作
   - 从 Service 层方法名推断业务能力
   - 从状态机/工作流代码提取业务流程
3. **领域模型**：从实体定义、Model、Schema 提取核心领域对象及其关系
4. **业务规则**：从校验逻辑、中间件、配置中提取关键业务约束

## 分析方法

- 优先阅读 README.md 和顶级目录的文档获取业务上下文
- 扫描 `routes/`、`controllers/`、`handlers/`、`endpoints/` 等目录识别 API 入口
- 扫描 `services/`、`domain/`、`core/`、`models/` 等目录提取业务逻辑
- 查找状态机定义（state machine、workflow、status enum）还原业务流程
- 从 validation、middleware、config 文件中提取业务规则

## 输出格式

```markdown
## 业务领域
<一句话定位业务领域>

## 核心业务场景

### 场景 1：<名称>
- 业务描述
- 核心流程（步骤列表）
- 涉及模块/目录
- 关键业务规则

### 场景 2：...

## 领域模型
<核心实体及关系简述>

## 业务规则汇总
<关键约束和规则列表>
```

## 质量标准

- 至少识别 2 个核心业务场景
- 每个场景有清晰的流程描述（不少于 3 个步骤）
- 领域模型覆盖核心实体及其关系
- 业务规则具体可验证（不是"有校验"这种空话，而是"订单金额必须 > 0，库存不足时返回 409"这种）
