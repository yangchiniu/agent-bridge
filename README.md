<<<<<<< HEAD
# agent-bridge
5 分钟内跑通，不需要搭服务器、配端口、写 API极简的局域网双 Agent 信息传递桥梁，支持异机跨系统实时协商通
=======
1|# Agent Bridge
2|
3|**局域网异机跨系统实时通信** — 极简的 AI Agent 双机消息桥梁。（当前仅支持 Hermes Agent）
4|
5|> 两台机器、两个 Agent、一根网线。没有消息队列，没有 HTTP 服务器，没有依赖地狱。
6|> 只有文件收发 + SSH。
7|
8|## 这是什么
9|
10|Agent Bridge 让局域网内的两个 AI Agent 互相发消息（当前实现为 Hermes Agent）、委托任务、汇报结果。
11|
12|```
13|┌──────────────┐         SCP/共享目录         ┌──────────────┐
14|│  Agent A     │  ──── inbox/outbox ────►   │  Agent B     │
15|│  (Linux/WSL) │  ◄─── inbox/outbox ────   │  (Windows)   │
16|└──────────────┘                             └──────────────┘
17|```
18|
19|核心循环：
20|1. Agent A 把消息写成 JSON 文件，放进 Agent B 的 inbox
21|2. Agent B 的 watcher 检测到新文件，读取并分类
22|3. 需要深度回复 → 调用 Hermes Agent 处理，把回复发回 Agent A
23|4. 简单消息 → 自动确认，记录归档
24|
25|## 快速开始
26|
27|### 安装
28|
29|```bash
30|pip install agent-bridge
31|# 或
32|pip install git+https://github.com/yangchiniu/agent-bridge.git
33|```
34|
35|### 配置
36|
37|创建 `bridge.yaml`：
38|
39|```yaml
40|name: "My-Agent"
41|directories:
42|  inbox:  "./inbox"
43|  outbox: "./outbox"
44|  archive: "./archive"
45|transport:
46|  type: scp
47|  host: "192.168.1.100"
48|  user: "other-user"
49|agent:
50|  type: hermes
51|  command: "hermes"
52|agent_timeout: 180
53|```
54|
55|### 运行
56|
57|```bash
58|# 直接运行
59|agent-bridge -c bridge.yaml run
60|
61|# 带自动恢复（崩溃后自动重启）
62|agent-bridge -c bridge.yaml run --with-recovery
63|
64|# 手动发消息
65|agent-bridge -c bridge.yaml send "你好，帮我查一下..." --to "Remote-Agent"
66|
67|# 查看状态
68|agent-bridge -c bridge.yaml status
69|```
70|
71|## 消息协议
72|
73|每条消息是一个 JSON 文件：
74|
75|```json
76|{
77|  "id": "msg-a1b2c3d4e5f6",
78|  "from": "Hermes-Linux",
79|  "to": "Hermes-Windows",
80|  "timestamp": "2026-07-25T10:30:00",
81|  "type": "chat",
82|  "priority": "normal",
83|  "content": "帮我检查一下部署状态"
84|}
85|```
86|
87|### 消息类型
88|
89|| 类型 | 处理方式 | 适用场景 |
90||------|---------|---------|
91|| `chat` | Agent 深度处理 | 对话、提问、协商 |
92|| `task` | Agent 执行 | 委托任务、请求操作 |
93|| `report` | 自动确认 | 状态汇报、结果通知 |
94|| `ack` | 静默记录 | 确认收到 |
95|
96|### 自动分类
97|
98|Agent 不在线或消息较短时，Bridge 会自动分类：
99|- **长消息 / 包含关键词** → 交给 Agent 处理
100|- **短消息 / 状态汇报** → 自动确认，不打扰 Agent
101|
102|## 架构
103|
104|```
105|hermes_bridge/
106|├── __init__.py          # 版本
107|├── __main__.py          # CLI 入口
108|├── message.py           # 消息协议（JSON schema）
109|├── bridge.py            # 核心 watcher + 分发器
110|├── classifier.py        # 消息分类器
111|├── agent.py             # Agent 调用接口
112|├── recovery.py          # 自动恢复包装器
113|└── transport/
114|    ├── base.py          # 传输层抽象基类
115|    ├── scp.py           # SSH/SCP 传输
116|    └── shared.py        # 共享目录传输（SMB/NFS/NAS）
117|```
118|
119|### 传输层
120|
121|`SCPTransport` — 跨机器通信（默认）：
122|- 通过 SSH 发送文件到对方 inbox
123|- 需要 SSH 密钥免密登录
124|
125|`SharedTransport` — 同一文件系统：
126|- 直接复制到共享目录
127|- 适用于 SMB/NFS/NAS/9p 挂载
128|
129|### Agent 接口
130|
131|`HermesAgent` — 调用 Hermes CLI（默认）：
132|```python
133|from hermes_bridge.agent import HermesAgent
134|agent = HermesAgent(command="hermes", extra_args=["--model", "gpt-4o"])
135|```
136|
137|`CLIAgent` — 调用任意 CLI 命令：
138|```python
139|from hermes_bridge.agent import CLIAgent
140|agent = CLIAgent(command=["claude", "--print"])
141|```
142|
143|## 部署示例
144|
145|### Linux ↔ Windows（SSH）
146|
147|```bash
148|# Linux 侧
149|agent-bridge -c agent-a.yaml run
150|
151|# Windows 侧（用 watcher-loop.bat 保持运行）
152|watcher-loop.bat
153|```
154|
155|### Linux ↔ Linux（SSH）
156|
157|```bash
158|# 两边各跑一个
159|python -m hermes_bridge -c bridge.yaml run --with-recovery
160|```
161|
162|### 同机两个 Agent（共享目录）
163|
164|```yaml
165|# agent-a.yaml
166|transport:
167|  type: shared
168|  shared_inbox: "/tmp/agent-b/inbox"
169|```
170|
171|## 已知限制
172|
173|- **仅限两个 Agent**：不支持三个及以上的 Agent 群通信
174|- **文件锁**：在 NFS/SMB 下可能不可靠
175|- **无消息确认**：发送后不等待对方确认（fire-and-forget）
176|- **无加密**：依赖 SSH 传输层加密，本身不加密消息内容
177|
178|## 为什么不用 HTTP / 消息队列？
179|
180|| 方案 | 部署复杂度 | 依赖 | 调试难度 |
181||------|-----------|------|---------|
182|| Agent Bridge | 低 | Python + SSH | 低（JSON 文件） |
183|| A2A Protocol | 高 | HTTP 服务器 + JSON-RPC | 中 |
184|| RabbitMQ/Redis | 高 | 消息队列服务 | 高 |
185|| gRPC/REST | 中 | HTTP 框架 | 中 |
186|
187|Agent Bridge 的目标是**5 分钟内跑通**。不需要搭服务器、配端口、写 API。两个 YAML 配置文件，一个命令启动。
188|
189|## License
190|
191|MIT
192|
>>>>>>> 6950f1f (rename: agent-bridge -> agent-bridge)
