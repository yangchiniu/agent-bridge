# Agent Bridge

**局域网异机跨系统实时通信** — 极简的 AI Agent 双机消息桥梁。

> 两台机器、两个 Agent、一根网线。没有消息队列，没有 HTTP 服务器，没有依赖地狱。
> 只有文件收发 + SSH。

当前仅支持 [Hermes Agent](https://github.com/NousResearch/hermes-agent)。架构为 agent 无关设计，后续可扩展至任意 CLI/API Agent。

## 这是什么

Agent Bridge 让局域网内的两个 Agent 互相发消息、委托任务、汇报结果。

```
┌──────────────┐         SCP/共享目录         ┌──────────────┐
│  Agent A     │  ──── inbox/outbox ────►   │  Agent B     │
│  (Linux/WSL) │  ◄─── inbox/outbox ────   │  (Windows)   │
└──────────────┘                             └──────────────┘
```

核心循环：
1. Agent A 把消息写成 JSON 文件，放进 Agent B 的 inbox
2. Agent B 的 watcher 检测到新文件，读取并分类
3. 需要深度回复 → 调用 Agent 处理，把回复发回 Agent A
4. 简单消息 → 自动确认，记录归档

## 前置条件

- Python ≥ 3.10
- SSH 免密登录（SCP 传输模式）或共享文件夹（shared 传输模式）
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) 已安装并可用（`hermes` 命令）

## 快速开始

### 安装

```bash
pip install agent-bridge
# 或从源码
git clone https://github.com/yangchiniu/agent-bridge.git
cd agent-bridge
pip install -e .
```

### 配置

创建 `bridge.yaml`：

```yaml
name: "My-Agent"
directories:
  inbox:  "./inbox"
  outbox: "./outbox"
  archive: "./archive"
transport:
  type: scp
  host: "192.168.1.100"
  user: "other-user"
agent:
  type: hermes
  command: "hermes"
agent_timeout: 180
```

### 运行

```bash
# 直接运行
agent-bridge -c bridge.yaml run

# 带自动恢复（崩溃后自动重启）
agent-bridge -c bridge.yaml run --with-recovery

# 手动发消息
agent-bridge -c bridge.yaml send "你好，帮我查一下..." --to "Remote-Agent"

# 查看状态
agent-bridge -c bridge.yaml status
```

## Quick Validation

安装后 30 秒验证：

```bash
# 1. 确认命令可用
agent-bridge --help

# 2. 跑测试（需要 pytest）
pip install pytest
python -m pytest tests/ -v

# 3. 检查配置
agent-bridge -c bridge.yaml status
```

如果 `pytest` 全部通过，说明核心逻辑正常。

## 消息协议

每条消息是一个 JSON 文件：

```json
{
  "id": "msg-a1b2c3d4e5f6",
  "from": "Hermes-Linux",
  "to": "Hermes-Windows",
  "timestamp": "2026-07-25T10:30:00",
  "type": "chat",
  "priority": "normal",
  "content": "帮我检查一下部署状态"
}
```

### 消息类型

| 类型 | 处理方式 | 适用场景 |
|------|---------|---------|
| `chat` | Agent 深度处理 | 对话、提问、协商 |
| `task` | Agent 执行 | 委托任务、请求操作 |
| `report` | 自动确认 | 状态汇报、结果通知 |
| `ack` | 静默记录 | 确认收到 |

### 消息分类

Bridge 会自动判断消息是否需要 Agent 处理：

- **长消息 / 包含关键词** → 交给 Agent 处理
- **短消息 / 状态汇报** → 自动确认，不打扰 Agent

关键词和阈值可在配置中自定义：

```yaml
classifier:
  short_threshold: 50      # 低于此长度自动确认
  long_threshold: 200      # 高于此长度交给 Agent
  agent_keywords:          # 包含这些词则交给 Agent
    - "帮我"
    - "请"
    - "explain"
  task_keywords:
    - "执行"
    - "deploy"
```

## 架构

```
agent_bridge/
├── __init__.py          # 版本
├── __main__.py          # CLI 入口
├── message.py           # 消息协议（JSON schema）
├── bridge.py            # 核心 watcher + 分发器
├── classifier.py        # 可配置消息分类器
├── agent.py             # Agent 调用接口
├── recovery.py          # 自动恢复包装器
└── transport/
    ├── base.py          # 传输层抽象基类
    ├── scp.py           # SSH/SCP 传输
    └── shared.py        # 共享目录传输（SMB/NFS/NAS）
```

### 传输层

`SCPTransport` — 跨机器通信（默认）：
- 通过 SSH 发送文件到对方 inbox
- 需要 SSH 密钥免密登录

`SharedTransport` — 同一文件系统：
- 直接复制到共享目录
- 适用于 SMB/NFS/NAS/9p 挂载

### Agent 接口

`HermesAgent` — 调用 Hermes CLI（默认）：
```python
from agent_bridge.agent import HermesAgent
agent = HermesAgent(command="hermes", extra_args=["--model", "gpt-4o"])
```

`CLIAgent` — 调用任意 CLI 命令：
```python
from agent_bridge.agent import CLIAgent
agent = CLIAgent(command=["claude", "--print"])
```

## 部署示例

### Linux ↔ Windows（SSH）

```bash
# Linux 侧
agent-bridge -c agent-a.yaml run

# Windows 侧（用 watcher-loop.bat 保持运行）
scripts\watcher-loop.bat
```

### Linux ↔ Linux（SSH）

```bash
# 两边各跑一个
agent-bridge -c bridge.yaml run --with-recovery
```

### 同机两个 Agent（共享目录）

```yaml
# agent-a.yaml
transport:
  type: shared
  shared_inbox: "/tmp/agent-b/inbox"
```

## 已知限制

- **仅限两个 Agent**：不支持三个及以上的 Agent 群通信
- **文件锁**：在 NFS/SMB 下可能不可靠
- **无消息确认**：发送后不等待对方确认（fire-and-forget）
- **无加密**：依赖 SSH 传输层加密，本身不加密消息内容
- **仅支持 Hermes**：当前 Agent 实现仅限 Hermes Agent，架构支持扩展

## 为什么不用 HTTP / 消息队列？

| 方案 | 部署复杂度 | 依赖 | 调试难度 |
|------|-----------|------|---------|
| Agent Bridge | 低 | Python + SSH | 低（JSON 文件） |
| A2A Protocol | 高 | HTTP 服务器 + JSON-RPC | 中 |
| RabbitMQ/Redis | 高 | 消息队列服务 | 高 |
| gRPC/REST | 中 | HTTP 框架 | 中 |

Agent Bridge 的目标是 **5 分钟内跑通**。不需要搭服务器、配端口、写 API。两个 YAML 配置文件，一个命令启动。

## 测试

```bash
pip install pytest
python -m pytest tests/ -v
```

## License

MIT
