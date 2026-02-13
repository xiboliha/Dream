# AI Girlfriend Agent (Nuyoah)

基于 FastAPI 的 AI 女友聊天机器人系统，具备智能对话、记忆学习、情感分析和 RAG 向量检索能力。

## 功能特性

- **智能对话系统**: 基于 glm-4.7 模型的自然对话，支持上下文理解和反转识别
- **RAG 向量检索**: 使用 Qdrant 向量数据库，支持百万级对话检索增强
- **记忆学习系统**: 短期记忆（对话上下文）+ 长期记忆（用户信息提取与存储）
- **情感智能**: AI 情绪状态追踪，根据用户情绪动态调整回复风格
- **主动消息系统**: 定时问候、空闲检测，模拟真人聊天体验
- **监控系统**: 实时日志查看、对话记录统计、错误追踪
- **Web 界面**: 现代化聊天界面和监控面板

## 快速开始

### 环境要求

- Python 3.9+
- Docker (用于运行 Qdrant)
- Redis (可选，用于缓存)

### 安装

```bash
# 克隆项目
git clone https://github.com/xiboliha/Dream.git
cd Dream

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements/base.txt
```

### 配置

1. 复制环境变量示例文件：
```bash
# Windows:
copy .env.example .env
# Linux/Mac:
cp .env.example .env
```

2. 编辑 `.env` 文件，配置必要的 API 密钥：
```ini
# AI 服务提供商
AI_PROVIDER=qianwen
AI_MODEL=glm-4.7

# 阿里云百炼 API
DASHSCOPE_API_KEY=your_api_key_here

# RAG 向量数据库
RAG_BACKEND=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=dialogues

# Redis (可选)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 启动服务

1. **启动 Qdrant 向量数据库**：
```bash
docker run -d -p 6333:6333 -p 6334:6334 \
  --name qdrant \
  docker.m.daocloud.io/qdrant/qdrant:latest
```

2. **启动 FastAPI 服务**：
```bash
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --reload
```

3. **访问应用**：
- 聊天页面: http://127.0.0.1:8000
- 监控页面: http://127.0.0.1:8000/monitor
- 情绪监控: http://127.0.0.1:8000/emotion-monitor
- API 文档: http://127.0.0.1:8000/docs

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
│   │   │   ├── engine.py           # 对话引擎
│   │   │   └── context_analyzer.py # 上下文分析器
│   │   ├── personality/       # 人格系统
│   │   └── relationship/      # 关系构建
│   ├── services/              # 服务层
│   │   ├── ai/               # AI服务
│   │   │   ├── qianwen_service.py  # 阿里云百炼
│   │   │   └── embedding_service.py # 嵌入服务
│   │   ├── knowledge/        # 知识服务
│   │   │   ├── rag_service.py     # RAG服务
│   │   │   ├── qdrant_store.py    # Qdrant存储
│   │   │   └── vector_store.py    # FAISS存储
│   │   ├── memory/           # 记忆管理
│   │   ├── emotion/          # 情绪分析
│   │   │   ├── analyzer.py        # 情绪分析器
│   │   │   └── ai_emotion_state.py # AI情绪状态
│   │   ├── proactive/        # 主动消息
│   │   ├── tools/            # 工具服务
│   │   │   └── search.py          # 网络搜索
│   │   └── storage/          # 存储服务
│   ├── interfaces/           # 接口层
│   │   └── web/
│   │       ├── chat.html     # 聊天页面
│   │       ├── monitor.html  # 监控页面
│   │       ├── emotion_monitor.html # 情绪监控
│   │       └── assets/       # 静态资源
│   └── utils/                # 工具类
│       ├── logger.py         # 日志系统
│       └── exceptions.py     # 异常处理
├── data/                     # 数据目录
│   ├── database/            # SQLite数据库
│   ├── logs/                # 日志文件
│   └── vector_store/        # 向量索引
├── tests/                    # 测试
│   ├── unit/                # 单元测试
│   └── integration/         # 集成测试
├── cclogs/                   # 开发日志
│   └── claude.md            # 项目文档和开发记录
├── .env                     # 环境变量 (不提交)
├── .env.example             # 环境变量示例
└── requirements/            # 依赖文件
    ├── base.txt            # 基础依赖
    ├── dev.txt             # 开发依赖
    └── prod.txt            # 生产依赖
```

## 核心模块详解

### 1. 智能对话系统

**上下文分析器 (ContextAnalyzer)**：
- 分析消息对上下文的依赖程度
- 计算消息重要性评分
- 检测话题变化
- 智能选择相关上下文
- 检测对历史消息的引用

**对话引擎 (ConversationEngine)**：
- 动态调整上下文窗口大小
- 集成 RAG 向量检索增强回复
- 支持多条消息连发（模拟真人聊天）
- 情绪感知和反转理解

### 2. 记忆系统

记忆系统分为两层：

- **短期记忆**: 保存最近对话上下文，维持对话连贯性
- **长期记忆**: 自动提取并固化重要信息（用户姓名、偏好、重要事件等）

**记忆类型**：
- `fact`: 事实信息（姓名、年龄、职业等）
- `preference`: 偏好信息（喜欢/不喜欢的事物）
- `event`: 事件记忆（重要日期、经历）
- `relationship`: 关系信息（家人、朋友）
- `emotion`: 情感记忆
- `habit`: 习惯信息

**JSON 解析容错**：
- 7 层 fallback 解析策略
- 智能括号匹配
- 自动修复常见格式问题
- 记忆提取成功率 90%+

### 3. RAG 向量检索

**Qdrant 向量数据库**：
- 支持百万级对话存储
- 相似对话检索增强回复质量
- 自动向量化和索引
- 支持语义搜索

**检索策略**：
- 根据用户消息检索相似对话
- 动态调整检索数量（5-10 条）
- 结合上下文依赖度优化检索

### 4. 情感智能

**情绪分析 (EmotionAnalyzer)**：
- 识别用户情绪（开心、难过、生气、焦虑等）
- 分析情绪强度
- 检测情绪变化

**AI 情绪状态 (AIEmotionState)**：
- 9 种 AI 情绪状态：happy, content, caring, playful, worried, sad, annoyed, shy, excited
- 根据用户情绪动态调整 AI 情绪
- 情绪影响回复风格和语气
- 情绪强度追踪和衰减机制

### 5. 主动消息系统

**定时问候**：
- 08:00 早安
- 12:00 午饭提醒
- 14:00 午睡结束
- 18:00 晚饭提醒
- 22:00 晚安

**空闲检测**：
- 30 分钟无回复时主动发消息
- 防止消息轰炸（最小间隔控制）
- 多种空闲提醒模板

### 6. 网络搜索

**必应搜索集成**：
- 关键词触发搜索（"搜一下"、"查一下"等）
- 自动解析搜索结果
- 搜索结果注入 AI 上下文
- 生成自然回复

## API 接口

主要接口：

| 接口 | 方法 | 说明 |
|-----|------|-----|
| `/` | GET | 聊天页面 |
| `/monitor` | GET | 监控页面 |
| `/emotion-monitor` | GET | 情绪监控页面 |
| `/health` | GET | 健康检查 |
| `/chat` | POST | 发送消息 |
| `/logs` | GET | 获取日志 |
| `/logs/chats` | GET | 对话记录 |
| `/logs/errors` | GET | 错误日志 |
| `/logs/stats` | GET | 统计信息 |
| `/rag/dialogues` | POST | 添加对话到 RAG |
| `/rag/search` | GET | 搜索对话 |
| `/rag/stats` | GET | RAG 统计 |
| `/emotion/state/{user_id}` | GET | 获取 AI 情绪状态 |
| `/emotion/history/{user_id}` | GET | 获取情绪历史 |
| `/users/{user_id}/proactive` | GET | 获取主动消息 |
| `/users/{user_id}/activity` | POST | 更新用户活动 |

详细文档访问: http://127.0.0.1:8000/docs

## 开发指南

### 安装开发依赖
```bash
pip install -r requirements/dev.txt
```

### 运行测试
```bash
# 运行所有测试
pytest

# 运行并显示覆盖率
pytest --cov=src tests/

# 只运行单元测试
pytest tests/unit/
```

### Git 工作流

项目采用 Git Flow 工作流：

```
main (生产分支)
├── develop (开发主分支)
│   ├── feature/context-optimization (上下文优化)
│   ├── feature/memory-system (记忆系统)
│   ├── feature/local-model (本地模型)
│   ├── feature/image-understanding (图片理解)
│   ├── feature/search-cache (搜索缓存)
│   └── feature/voice-support (语音支持)
```

**开发流程**：
1. 从 `develop` 创建 feature 分支
2. 在 feature 分支上开发
3. 通过 Pull Request 合并到 `develop`
4. 测试通过后合并到 `main`

## 注意事项

### 伦理和安全

1. **AI身份透明**: 系统会定期提醒用户这是AI
2. **隐私保护**: 所有数据本地存储，不上传
3. **内容安全**: 自动过滤不当内容
4. **心理健康**: 检测到危机信号时提供专业求助资源

### 使用建议

- 本项目仅供学习和娱乐使用
- 请勿过度依赖AI陪伴
- 遇到心理问题请寻求专业帮助

## 常见问题

**Q: 微信登录失败怎么办？**
A: 确保网络正常，尝试删除 `data/cache/wechat` 目录后重新登录。

**Q: AI回复很慢怎么办？**
A: 检查网络连接和API密钥配置，可以尝试切换AI服务提供商。

**Q: 如何清除记忆？**
A: 删除 `data/database/aigf.db` 文件即可重置所有数据。

**Q: 支持群聊吗？**
A: 目前只支持私聊，群聊功能在规划中。

## 技术栈

- **后端框架**: FastAPI + Uvicorn
- **AI 模型**: 阿里云百炼 (glm-4.7)
- **向量数据库**: Qdrant
- **嵌入模型**: text-embedding-v3 (DashScope)
- **数据库**: SQLAlchemy + SQLite
- **缓存**: Redis (可选)
- **日志**: Loguru
- **测试**: Pytest

## 项目文档

详细的开发日志和技术文档请查看：
- [项目文档](cclogs/claude.md) - 完整的开发历程、功能说明和 API 文档

## GitHub 仓库

https://github.com/xiboliha/Dream

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

开发流程：
1. Fork 本仓库
2. 创建 feature 分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: 添加某个功能'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request
