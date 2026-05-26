# Kimi-X Desktop → Agent 演进方案

> 版本: v1.0
> 日期: 2026-05-26
> 目标: 分析当前 Kimi-X Desktop 与真正 AI Agent 的差距，制定分阶段演进路线

---

## 一、现状诊断：我们有什么？

### 1.1 当前架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                     Kimi-X Desktop (壳)                      │
│  ┌─────────────┐  ┌──────────────────────────────────────┐  │
│  │ DeepIntent  │  │         iframe (kimi web)            │  │
│  │   面板      │  │  ┌────────────────────────────────┐  │  │
│  │             │  │  │         Kimi CLI 服务端         │  │  │
│  │ • 健康检查  │  │  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐  │  │  │
│  │ • CPU调速   │  │  │  │LLM │ │工具│ │记忆│ │对话│  │  │  │
│  │ • 闭环验证  │  │  │  └────┘ └────┘ └────┘ └────┘  │  │  │
│  │ • 学习反馈  │  │  └────────────────────────────────┘  │  │
│  │ • API密钥   │  │                                      │  │
│  └─────────────┘  └──────────────────────────────────────┘  │
│           ↑                         ↑                        │
│      runJavaScript             localStorage                  │
│      (PyQt→JS)                 (JS→PyQt)                     │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 已有能力清单

| 层级 | 能力 | 实现状态 | 质量 |
|------|------|---------|------|
| **感知** | 硬件扫描 (CPU/内存/磁盘/GPU) | ✅ | 完善 |
| **感知** | 项目结构检测 (DeepIntent) | ✅ | 完善 |
| **感知** | GitHub 认证检测 | ✅ | 基础 |
| **感知** | 用户点击/输入捕获 | ✅ | 基础 |
| **记忆** | 跨会话 JSON 记忆 | ✅ | 基础 |
| **记忆** | 配置持久化 | ✅ | 完善 |
| **记忆** | 反馈历史 (jsonl) | ✅ | 基础 |
| **记忆** | 项目记忆 (PROJECT.md) | ✅ | 基础 |
| **行动** | 启动/监控 kimi web | ✅ | 完善 |
| **行动** | 写入上下文文件 | ✅ | 基础 |
| **行动** | 桌面快捷方式生成 | ✅ | 完善 |
| **学习** | 👍👎 反馈接收 | ✅ | 原始 |
| **学习** | 对话主题学习 | ✅ | 原始 |

### 1.3 当前代码统计

| 文件 | 行数 | 职责 |
|------|------|------|
| `main.py` | 915 | 主窗口、UI、事件处理、流水线编排 |
| `deepintent_worker.py` | 275 | DeepIntent 后台线程、反馈持久化 |
| `hardware_profiler.py` | 202 | 硬件扫描 |
| `config.py` | 160 | 配置管理 |
| `logger.py` | ~100 | 日志系统 |
| `styles.py` | ~150 | QSS 样式 |
| `setup_desktop.py` | 73 | 快捷方式创建 |
| `web_ui/*` | ~700 | 前端面板 |
| **总计** | **~2,575** | |

---

## 二、Agent 的定义：我们缺什么？

### 2.1 Agent 的五大支柱

一个真正的 AI Agent 必须具备以下五个层次：

```
┌──────────────────────────────────────────┐
│  L5: 目标层 (Goal)                        │
│     理解用户长期意图，主动设定目标          │
├──────────────────────────────────────────┤
│  L4: 规划层 (Planning)                    │
│     任务分解、子目标生成、计划调整          │
├──────────────────────────────────────────┤
│  L3: 推理层 (Reasoning)                   │
│     LLM 驱动的思考、决策、代码生成          │
├──────────────────────────────────────────┤
│  L2: 记忆层 (Memory)                      │
│     长期语义记忆、工作记忆、 episodic 记忆   │
├──────────────────────────────────────────┤
│  L1: 感知层 (Perception)                  │
│     文件系统、代码、git、用户行为、网络       │
└──────────────────────────────────────────┘
```

### 2.2 当前差距矩阵

| 支柱 | 当前状态 | 差距描述 | 严重程度 |
|------|---------|---------|---------|
| **L1 感知** | 仅硬件 + 项目检测 | 不感知代码变更、git diff、用户编辑行为、网络状态 | 🔴 高 |
| **L2 记忆** | JSON 文件存储 | 无向量语义检索、无工作记忆、无 episodic 时间线 | 🔴 高 |
| **L3 推理** | 无本地 LLM | 所有推理在 iframe 内的 kimi web 中，壳本身无脑 | 🔴 高 |
| **L4 规划** | 无 | 无任务分解、无计划执行、无子 Agent | 🔴 高 |
| **L5 目标** | 无 | 不理解用户长期意图，不会主动行动 | 🔴 高 |

**结论：当前 Kimi-X Desktop 是一个「有感知能力的容器」，距离「Agent」还差一个完整的认知架构。**

---

## 三、竞品对标

### 3.1 横向对比

| 产品 | 定位 | LLM | 记忆 | 工具 | 自主 | 差距分析 |
|------|------|-----|------|------|------|---------|
| **Kimi-X Desktop** | 桌面壳 | iframe 外包 | JSON 文件 | 无 | ❌ | 缺推理和自主 |
| **Cursor** | IDE Agent | 内置 | 项目级 | 文件编辑 | ⚠️ 半自动 | 我们缺 IDE 集成 |
| **Claude Code** | 终端 Agent | Claude | 会话级 | shell/文件 | ⚠️ 半自动 | 我们缺终端工具链 |
| **Reasonix** | 终端 Agent | DeepSeek | 四级记忆 | 文件/web | ⚠️ 半自动 | 我们缺缓存优化 |
| **Aider** | 终端 Agent | 任意 | 文件级 | git/编辑 | ⚠️ 半自动 | 我们缺 git 集成 |
| **Kimi CLI** | 终端 Agent | Moonshot | 服务端 | 文件/Shell | ✅ 自动 | 我们就在它上面 |

### 3.2 关键洞察

**Kimi-X Desktop 的独特位置：**
- 其他 Agent 都是「终端优先」或「IDE 优先」
- Kimi-X 是「桌面壳优先」，有 GUI 面板优势
- **核心差异化**：可以把 Agent 状态可视化在侧边栏，而不是藏在终端日志里
- **机会**：成为「带 GUI 的 Agent 编排器」，而不是和 Cursor/Claude Code 竞争编码能力

---

## 四、演进方案：分四阶段

### Phase 0: 感知增强（1-2 周）
**目标：让壳能「看见」用户正在做什么**

#### 4.1.1 文件系统监控
```python
# 新增: file_watcher.py
class FileWatcher:
    """监控项目文件变更，生成事件流"""
    
    def __init__(self, project_root: Path):
        self.observer = Observer()  # watchdog
        self.event_queue = deque(maxlen=100)
    
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            self.event_queue.append({
                'type': 'file_modified',
                'path': event.src_path,
                'timestamp': time.time(),
            })
```

**价值**：Agent 能知道用户改了什么文件，主动建议相关操作。

#### 4.1.2 Git 状态感知
```python
# 新增: git_sensor.py
class GitSensor:
    """实时感知 git 状态"""
    
    def get_status(self) -> dict:
        return {
            'branch': self._run('git branch --show-current'),
            'dirty': bool(self._run('git status --short')),
            'uncommitted_files': self._get_uncommitted(),
            'ahead_behind': self._get_ahead_behind(),
            'last_commit': self._get_last_commit(),
        }
```

**价值**：Agent 知道用户有没有未提交代码，提醒 commit/push。

#### 4.1.3 用户行为追踪
```python
# 新增: behavior_tracker.py
class BehaviorTracker:
    """追踪用户在面板和 iframe 中的行为模式"""
    
    def record(self, event: str, context: dict):
        """记录：点击了哪个按钮、输入了什么、停留多久"""
        self.events.append({
            'event': event,           # 'click_learn', 'click_like', 'idle_5min'
            'context': context,
            'timestamp': time.time(),
        })
```

**价值**：Agent 学习用户习惯，比如「每次修改 models.py 后都会跑测试」。

#### Phase 0 交付物
| 新增文件 | 功能 |
|---------|------|
| `file_watcher.py` | watchdog 监控项目文件 |
| `git_sensor.py` | git 状态实时读取 |
| `behavior_tracker.py` | 用户行为事件流 |
| `panel.js` | 新增事件上报（点击、输入、停留） |

---

### Phase 1: 记忆升级（2-3 周）
**目标：从「JSON 存储」升级到「向量语义记忆」**

#### 4.2.1 向量记忆引擎
```python
# 新增: memory_engine.py
class MemoryEngine:
    """
    三层记忆架构（受 Reasonix 启发）
    
    L1: Immutable Prefix — 系统提示、项目规范、用户偏好（只读）
    L2: Episodic Buffer — 最近 N 个事件（自动滚动）
    L3: Semantic Store — 向量数据库，支持语义检索
    """
    
    def __init__(self, persist_dir: Path):
        self.prefix = self._load_prefix()      # 从 PROJECT.md + 用户偏好
        self.episodic = deque(maxlen=50)        # 最近 50 个事件
        self.semantic = ChromaDB()              # 向量数据库（或 sqlite-vss）
    
    def recall(self, query: str, k: int = 5) -> list:
        """语义检索相关记忆"""
        return self.semantic.query(query, k=k)
    
    def add(self, text: str, metadata: dict):
        """添加新记忆，自动嵌入向量"""
        self.episodic.append({'text': text, 'meta': metadata})
        self.semantic.add(text, metadata)
```

**技术选型**：
- 轻量方案：`sqlite-vss`（SQLite 向量扩展，纯 Python，无外部依赖）
- 或 `chromadb`（更成熟，但需额外安装）
- 嵌入模型：`sentence-transformers/all-MiniLM-L6-v2`（本地，无 API 成本）

#### 4.2.2 记忆类型扩展

| 记忆类型 | 存储位置 | 内容 | 检索方式 |
|---------|---------|------|---------|
| **项目规范** | `.kimi-x/PROJECT.md` | 技术栈、规范、API 位置 | 全文读取 |
| **用户偏好** | `~/.kimi/kimi-x-desktop/memories/user.json` | 喜欢的代码风格、常用命令 | 向量检索 |
| **对话历史** | `~/.kimi/kimi-x-desktop/memories/chat/` | 与 Agent 的每次对话 | 向量检索 |
| **代码片段** | `~/.kimi/kimi-x-desktop/memories/code/` | 用户常复用的代码模式 | 向量检索 |
| **错误模式** | `~/.kimi/kimi-x-desktop/memories/errors/` | 用户反复犯的错 | 向量检索 |
| **反馈历史** | `~/.kimi/kimi-x-desktop/feedback/` | 👍👎 记录 | 时间线 |

#### Phase 1 交付物
| 新增文件 | 功能 |
|---------|------|
| `memory_engine.py` | 三层记忆架构 |
| `embedding.py` | 本地嵌入模型封装 |
| `memories/` 目录 | 自动创建各类记忆存储 |

---

### Phase 2: 推理引擎（3-4 周）
**目标：让壳拥有「本地大脑」，不再完全依赖 iframe 里的 kimi web**

#### 4.3.1 架构决策：本地 LLM vs API

| 方案 | 优点 | 缺点 | 建议 |
|------|------|------|------|
| 本地 LLM (Ollama) | 零成本、离线、隐私 | 需要 GPU/大内存、速度慢 | 高配电脑可选 |
| Moonshot API | 与 kimi 生态一致、速度快 | 有成本、需联网 | **默认方案** |
| 混合模式 | 简单任务本地、复杂任务 API | 架构复杂 | 长期目标 |

**推荐**：先接入 Moonshot API（与 Kimi CLI 一致），后续支持 Ollama 作为降级方案。

#### 4.3.2 Agent 推理循环

```python
# 新增: agent_core.py
class AgentCore:
    """
    Agent 核心推理引擎
    
    循环：感知 → 记忆检索 → 推理 → 决策 → 行动 → 反馈
    """
    
    def __init__(self, memory: MemoryEngine, llm_client: LLMClient):
        self.memory = memory
        self.llm = llm_client
        self.tool_registry = ToolRegistry()
    
    def perceive(self, event: dict) -> dict:
        """感知层：处理原始事件，提取关键信息"""
        # 文件修改 → 提取变更摘要
        # git 状态变化 → 判断是否需要行动
        # 用户输入 → 理解意图
        return {'intent': '...', 'urgency': 0.8, 'context': {...}}
    
    def think(self, perception: dict) -> dict:
        """推理层：LLM 驱动思考"""
        # 检索相关记忆
        relevant = self.memory.recall(perception['intent'])
        
        # 构建 prompt
        prompt = self._build_agent_prompt(perception, relevant)
        
        # 调用 LLM
        response = self.llm.chat(prompt)
        
        return {
            'thought': response.reasoning,
            'decision': response.decision,  # 'act', 'wait', 'ask_user'
            'action_plan': response.tool_calls,
        }
    
    def act(self, plan: list) -> list:
        """行动层：执行工具调用"""
        results = []
        for tool_call in plan:
            tool = self.tool_registry.get(tool_call['name'])
            result = tool.run(**tool_call['arguments'])
            results.append(result)
        return results
    
    def learn(self, perception: dict, thought: dict, results: list):
        """学习层：从结果中更新记忆"""
        # 记录这次交互
        self.memory.add(f"用户{perception['intent']}，Agent决定{thought['decision']}，结果{results}")
        
        # 如果用户给了反馈，强化学习
        if perception.get('feedback'):
            self.memory.update_weight(perception['intent'], perception['feedback'])
```

#### 4.3.3 工具注册系统

```python
# 新增: tools/registry.py
class ToolRegistry:
    """Agent 可用工具注册表"""
    
    def __init__(self):
        self._tools = {}
    
    def register(self, name: str, func: Callable, schema: dict):
        self._tools[name] = {'func': func, 'schema': schema}
    
    def get(self, name: str) -> Callable:
        return self._tools[name]['func']
    
    def list(self) -> list:
        return [{'name': n, 'schema': t['schema']} for n, t in self._tools.items()]

# 内置工具
registry = ToolRegistry()
registry.register('read_file', read_file, {
    'description': '读取文件内容',
    'parameters': {'path': {'type': 'string', 'description': '文件路径'}}
})
registry.register('write_file', write_file, {...})
registry.register('run_shell', run_shell, {...})
registry.register('git_status', git_status, {...})
registry.register('web_search', web_search, {...})
registry.register('ask_user', ask_user, {...})
```

#### 4.3.4 与现有 iframe 的关系

**关键设计**：Agent Core 和 iframe 里的 kimi web 是互补关系，不是竞争关系。

```
用户输入 ──→ Agent Core（本地快速推理）
               ├── 简单任务 → 直接执行（不打扰用户）
               ├── 复杂任务 → 转发到 iframe（kimi web 处理）
               └── 需要确认 → 面板弹窗询问
```

**Agent Core 负责**：
- 监控类任务（文件变更提醒、git 状态提醒）
- 快速查询（读文件、查状态、简单搜索）
- 预处理（把用户模糊意图转化为清晰指令再转发 kimi）

**kimi web 负责**：
- 复杂编码任务
- 多轮深度对话
- 需要大量上下文理解的任务

#### Phase 2 交付物
| 新增文件 | 功能 |
|---------|------|
| `agent_core.py` | Agent 推理循环（感知→推理→行动→学习） |
| `llm_client.py` | Moonshot API 客户端 + Ollama 降级 |
| `tools/registry.py` | 工具注册表 |
| `tools/filesystem.py` | 文件操作工具 |
| `tools/shell.py` | Shell 执行工具 |
| `tools/git.py` | Git 操作工具 |
| `tools/web.py` | Web 搜索工具 |
| `tools/user.py` | 用户交互工具（弹窗确认） |

---

### Phase 3: 自主行动（4-6 周）
**目标：Agent 能在后台主动做事，不等待用户指令**

#### 4.4.1 后台守护循环

```python
# 新增: agent_daemon.py
class AgentDaemon(QThread):
    """
    Agent 后台守护线程
    
    持续运行，每隔一段时间检查环境状态，主动决策是否行动
    """
    
    def __init__(self, agent_core: AgentCore, sensors: SensorSuite):
        super().__init__()
        self.agent = agent_core
        self.sensors = sensors
        self._running = True
    
    def run(self):
        while self._running:
            # 1. 收集传感器数据
            perceptions = self.sensors.collect()
            
            # 2. 过滤：只有重要事件才触发推理
            important = [p for p in perceptions if p['urgency'] > 0.6]
            
            for p in important:
                # 3. Agent 推理
                thought = self.agent.think(p)
                
                if thought['decision'] == 'act':
                    # 4. 执行行动
                    results = self.agent.act(thought['action_plan'])
                    
                    # 5. 通知用户（通过面板气泡）
                    self.notify_user(p, thought, results)
                
                elif thought['decision'] == 'ask_user':
                    # 需要确认，弹窗
                    self.ask_user(p, thought)
            
            # 每 10 秒检查一次
            time.sleep(10)
```

#### 4.4.2 主动场景示例

| 场景 | 触发条件 | Agent 行动 | 通知方式 |
|------|---------|-----------|---------|
| **未提交提醒** | git dirty + idle > 5min | 建议 `git add && git commit` | 面板气泡 |
| **测试失败** | 文件保存后 pytest 失败 | 显示错误摘要，建议修复 | 面板红色告警 |
| **依赖更新** | requirements.txt 变更 | 提醒 `pip install -r` | 面板气泡 |
| **大文件提交** | git add 包含 >10MB 文件 | 警告，建议 gitignore | 弹窗确认 |
| **长时间未保存** | 编辑器有变更 + idle > 10min | 提醒保存 | 面板气泡 |
| **API 密钥泄露** | 检测到代码中有 `ghp_`/`sk-` | 严重警告，建议移除 | 弹窗 + 日志 |

#### 4.4.3 面板可视化升级

```
┌──────────────────────────────────────┐
│ 🧠 Agent 状态                         │
│   模式: 监控中 ●                      │
│   待处理: 2 项                        │
│   今日行动: 15 次                     │
├──────────────────────────────────────┤
│ 📋 主动建议                           │
│   ⚠️ 有 3 个文件未提交                │
│   💡 检测到 models.py 变更，建议迁移  │
│   ✅ 刚刚自动格式化了 utils.py        │
├──────────────────────────────────────┤
│ (原有 DeepIntent 面板内容...)         │
└──────────────────────────────────────┘
```

#### Phase 3 交付物
| 新增文件 | 功能 |
|---------|------|
| `agent_daemon.py` | 后台守护线程 |
| `sensors/` | 传感器套件（git、文件、时间、网络） |
| `notifier.py` | 用户通知系统（气泡、弹窗、日志） |
| `panel.js` | 新增 Agent 状态和建议区域 |

---

## 五、技术选型与依赖

### 5.1 新增依赖

```
# Phase 0
watchdog>=3.0          # 文件系统监控

# Phase 1
sqlite-vss>=0.1        # 向量数据库（SQLite 扩展）
sentence-transformers>=2.3  # 本地嵌入模型
# 或 chromadb>=0.4     # 备选方案

# Phase 2
openai>=1.0            # Moonshot API 兼容客户端
httpx>=0.25            # 异步 HTTP

# Phase 3 (可选)
plyer>=2.1             # 跨平台桌面通知
```

### 5.2 硬件要求变化

| 阶段 | 额外内存 | 额外 CPU | 额外磁盘 | 说明 |
|------|---------|---------|---------|------|
| Phase 0 | 0 | 低 | 0 | watchdog 轻量 |
| Phase 1 | +200MB | 中 | +100MB | 向量数据库 |
| Phase 2 | +500MB | 高* | +500MB | *仅当使用本地 LLM |
| Phase 3 | +100MB | 低 | +10MB | 守护线程 |

**注**：如果使用 Moonshot API（推荐），Phase 2 无额外 CPU 负担。

---

## 六、风险评估与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 向量数据库安装失败 | 中 | 高 | 提供纯 SQLite 降级方案 |
| Moonshot API 成本过高 | 低 | 中 | 支持 Ollama 本地 LLM 降级 |
| 后台守护误报过多 | 中 | 中 | 可调阈值 + 用户反馈抑制 |
| 架构过度复杂 | 高 | 高 | **严格遵守分阶段，每阶段独立可用** |
| 与 iframe kimi web 冲突 | 低 | 高 | Agent Core 和 kimi web 明确分工 |

---

## 七、实施优先级

### 立即开始（本周）
1. ✅ 项目记忆（PROJECT.md）— **已做完**
2. ✅ 反馈持久化 — **已做完**
3. ✅ GitHub 配置检测 — **已做完**

### Phase 0（下周）
4. 文件系统监控（watchdog）
5. Git 状态传感器
6. 用户行为追踪

### Phase 1（2-3 周后）
7. 向量记忆引擎
8. 语义检索
9. 记忆类型扩展

### Phase 2（1-2 月后）
10. LLM 客户端（Moonshot API）
11. 工具注册系统
12. Agent 推理循环

### Phase 3（2-3 月后）
13. 后台守护线程
14. 主动场景实现
15. 面板可视化升级

---

## 八、一句话总结

> **当前 Kimi-X Desktop 是一个「有感知能力的容器」。要做成 Agent，需要依次补齐：感知层（文件/git/行为监控）→ 记忆层（向量语义检索）→ 推理层（本地 LLM + 工具调用）→ 自主层（后台守护 + 主动行动）。预计 3 个月完成全阶段，每阶段独立可用。**

---

*方案生成于 2026-05-26，基于 Kimi-X Desktop v1.0 代码分析。*
