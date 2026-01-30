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
