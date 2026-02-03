# AI Girlfriend Agent (Nuyoah) 项目文档

## 项目概述

AI女友聊天机器人系统，基于FastAPI构建，支持多种AI模型、RAG向量检索、记忆管理和个性化对话。

## 技术栈

- **后端框架**: FastAPI + Uvicorn
- **AI模型**: 阿里云百炼 (glm-4.7)
- **向量数据库**: Qdrant (支持百万级对话)
- **嵌入模型**: text-embedding-v3 (DashScope)
- **缓存**: Redis
- **数据库**: SQLite
- **前端**: 原生HTML/CSS/JS

## 项目结构

```
aigf/
├── config/                     # 配置文件
│   ├── settings.py            # 主配置
│   ├── knowledge/             # 知识库
│   │   ├── dialogue_dataset.json    # RAG对话数据集
│   │   └── dialogue_examples.json   # 对话示例
│   ├── personalities/         # 人格配置
│   │   ├── gentle_caring.yaml      # 温柔体贴
│   │   ├── intellectual.yaml       # 知性优雅
│   │   └── lively_cute.yaml        # 活泼可爱
│   └── prompts/               # 提示词
│       ├── system/base_prompt.txt  # 系统提示词
│       └── memory/            # 记忆提取提示词
├── src/
│   ├── app.py                 # FastAPI主应用
│   ├── core/                  # 核心模块
│   │   ├── conversation/      # 对话引擎
│   │   ├── personality/       # 人格系统
│   │   └── relationship/      # 关系构建
│   ├── services/              # 服务层
│   │   ├── ai/               # AI服务
│   │   │   ├── qianwen_service.py  # 阿里云百炼
│   │   │   ├── embedding_service.py # 嵌入服务
│   │   │   └── ...
│   │   ├── knowledge/        # 知识服务
│   │   │   ├── rag_service.py     # RAG服务
│   │   │   ├── qdrant_store.py    # Qdrant存储
│   │   │   └── vector_store.py    # FAISS存储
│   │   ├── memory/           # 记忆管理
│   │   └── storage/          # 存储服务
│   ├── interfaces/           # 接口层
│   │   └── web/
│   │       ├── chat.html     # 聊天页面
│   │       ├── monitor.html  # 监控页面
│   │       └── assets/       # 静态资源
│   └── utils/                # 工具类
│       └── logger.py         # 日志系统
├── data/                     # 数据目录
│   ├── database/            # SQLite数据库
│   ├── logs/                # 日志文件
│   └── vector_store/        # 向量索引
├── .env                     # 环境变量 (不提交)
├── .env.example             # 环境变量示例
└── requirements/            # 依赖文件
```

## 核心功能

### 1. 对话系统
- 基于glm-4.7模型的自然对话
- 人格化回复（低功耗女生人设）
- 情绪分析与响应

### 2. RAG向量检索
- 支持FAISS（小规模）和Qdrant（大规模）
- 相似对话检索增强回复质量
- 支持百万级对话数据

### 3. 记忆系统
- 短期记忆：对话上下文
- 长期记忆：用户信息提取与存储

### 4. 监控系统
- 实时日志查看
- 对话记录统计
- 错误日志追踪

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 聊天页面 |
| `/monitor` | GET | 监控页面 |
| `/chat` | POST | 发送消息 |
| `/health` | GET | 健康检查 |
| `/logs` | GET | 获取日志 |
| `/logs/chats` | GET | 对话记录 |
| `/logs/errors` | GET | 错误日志 |
| `/logs/stats` | GET | 统计信息 |
| `/rag/dialogues` | POST | 添加对话 |
| `/rag/search` | GET | 搜索对话 |
| `/rag/stats` | GET | RAG统计 |

## 环境配置

```bash
# .env 配置示例
AI_PROVIDER=qianwen
DASHSCOPE_API_KEY=your_api_key
AI_MODEL=glm-4.7

RAG_BACKEND=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=dialogues
```

## 启动方式

```bash
# 启动Qdrant (Docker)
docker run -d -p 6333:6333 -p 6334:6334 docker.m.daocloud.io/qdrant/qdrant:latest

# 启动服务
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

## 访问地址

- 聊天页面: http://127.0.0.1:8000
- 监控页面: http://127.0.0.1:8000/monitor
- API文档: http://127.0.0.1:8000/docs

## GitHub仓库

https://github.com/xiboliha/Dream

---

## 开发日志

### 2026-01-30 会话记录

#### 主要完成工作

1. **模型切换**
   - 从qwen-turbo切换到glm-4.7
   - 保持使用阿里云百炼API

2. **回复优化**
   - 修复回复开头带"..."的问题
   - 添加当前时间感知功能

3. **RAG系统实现**
   - 创建50条对话数据集
   - 实现FAISS本地向量存储
   - 实现Qdrant大规模向量存储
   - 添加RAG API接口

4. **Qdrant集成**
   - Docker部署Qdrant
   - 修复UUID格式问题
   - 修复search API兼容性

5. **界面优化**
   - 自定义头像（AI: 粉发动漫女孩, 用户: 蓝色小熊）
   - 修复ngrok穿透后API地址问题

6. **监控系统**
   - 创建日志存储系统
   - 添加日志API接口
   - 创建监控Web页面
   - 实时统计和日志查看

7. **错误修复**
   - 修复记忆提取JSON解析错误
   - 将非关键错误降级为DEBUG级别

#### 关键文件修改

- `config/settings.py` - RAG/Qdrant配置
- `config/prompts/system/base_prompt.txt` - 禁止"..."开头
- `src/utils/logger.py` - 日志存储系统
- `src/app.py` - 监控API接口
- `src/interfaces/web/monitor.html` - 监控页面
- `src/interfaces/web/chat.html` - API地址修复
- `src/services/knowledge/qdrant_store.py` - UUID转换
- `src/services/memory/manager.py` - JSON解析优化

#### 待优化项

- [ ] 记忆提取功能（glm-4.7 JSON输出不稳定）
- [ ] 日志文件持久化
- [ ] 更多人格配置

### 2026-02-02 会话记录

#### 主要完成工作

1. **多条消息回复功能**
   - 实现 `_split_multi_messages()` 方法，智能拆分回复
   - 支持兴奋/生气等情绪时连发多条消息
   - 模拟真人聊天的分段发送效果
   - API 返回 `messages` 数组，包含每条消息的独立延迟

2. **定时任务系统**
   - 创建 `ProactiveMessageService` 主动消息服务
   - 支持5个时间点的定时问候：
     - 08:00 早安
     - 12:00 午饭提醒
     - 14:00 午睡结束
     - 18:00 晚饭提醒
     - 22:00 晚安
   - 配置项在 `config/settings.py` 中可调整

3. **空闲检测功能**
   - 跟踪用户最后活动时间
   - 30分钟无回复时主动发消息
   - 防止消息轰炸（最小间隔控制）
   - 多种空闲提醒模板

4. **前端更新**
   - 支持多条消息依次显示，带打字指示器
   - 添加主动消息轮询（30秒间隔）
   - 用户交互时自动更新活动状态

5. **新增API接口**
   - `GET /users/{user_id}/proactive` - 获取主动消息
   - `POST /users/{user_id}/activity` - 更新用户活动
   - `GET /proactive/settings` - 获取主动消息设置

#### 关键文件修改

- `src/core/conversation/engine.py` - 多条消息拆分逻辑
- `src/services/proactive/message_service.py` - 主动消息服务（新建）
- `src/app.py` - 集成主动消息服务，新增API
- `src/interfaces/web/chat.html` - 多消息显示，主动消息轮询
- `config/settings.py` - 新增定时任务时间配置

#### 新增文件

- `src/services/proactive/__init__.py`
- `src/services/proactive/message_service.py`

#### API变更

| 接口 | 方法 | 说明 |
|------|------|------|
| `/users/{user_id}/proactive` | GET | 获取主动消息 |
| `/users/{user_id}/activity` | POST | 更新用户活动 |
| `/proactive/settings` | GET | 主动消息设置 |

#### ChatResponse 新增字段

```json
{
  "response": "完整回复",
  "messages": [
    {"content": "第一条", "typing_delay": 1.2},
    {"content": "第二条", "typing_delay": 0.8}
  ],
  ...
}
```

#### 待优化项

- [ ] 本地模型集成（qwen1.5-4b）
- [ ] 微调数据收集
- [ ] WebSocket 替代轮询（实时推送）

### 2026-02-03 会话记录

#### 主要完成工作

1. **网络搜索功能修复**
   - 搜狗搜索触发验证码，切换到必应中国 (cn.bing.com)
   - 重写 `_parse_bing_results()` 解析必应HTML结构
   - 正确提取标题、摘要和URL
   - 搜索结果注入AI上下文，生成自然回复

2. **对话质量优化**
   - 添加"连续对话示例"到系统提示词
   - 增强AI对上下文的理解能力
   - 优化回复语气，避免攻击性用语（如"穷鬼"→"没钱还想什么呢"）
   - 添加被骗/没钱/价格等场景的对话示例

3. **工具系统**
   - 新增 `src/services/tools/search.py` 网络搜索工具
   - 支持关键词触发搜索（"帮我搜"、"查一下"等）
   - 搜索结果格式化后提供给AI参考

#### 关键文件修改

- `src/services/tools/search.py` - 从搜狗切换到必应，重写解析逻辑
- `config/prompts/system/base_prompt.txt` - 添加连续对话示例，优化回复风格
- `src/core/conversation/engine.py` - 集成搜索工具
- `src/services/tools/__init__.py` - 导出搜索工具

#### 新增文件

- `src/services/tools/search.py` - 网络搜索工具

#### 搜索触发关键词

- "搜一下"、"搜索一下"、"查一下"、"帮我查"
- "是什么"、"是谁"、"怎么回事"
- "怎么做"、"如何"
- "最新新闻"、"最近消息"

#### 待优化项

- [ ] 搜索结果缓存
- [ ] 更多搜索引擎备选
- [ ] 对话上下文理解进一步优化
