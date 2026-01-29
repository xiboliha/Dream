## 系统架构总览

text

```
┌─────────────────────────────────────────────────────────────┐
│                     应用层 (Application)                      │
├─────────────────────────────────────────────────────────────┤
│ 微信接口层 │  主控调度  │  Web管理后台  │  API服务接口         │
├─────────────────────────────────────────────────────────────┤
│                     服务层 (Services)                        │
├─────────────────────────────────────────────────────────────┤
│  AI服务   │ 记忆服务    │ 情感服务     │ 定时服务  │ 存储服务  │
├─────────────────────────────────────────────────────────────┤
│                     核心层 (Core Modules)                    │
├─────────────────────────────────────────────────────────────┤
│  人格系统 │ 记忆学习    │ 关系构建     │ 对话引擎  │ 安全过滤  │
├─────────────────────────────────────────────────────────────┤
│                     数据层 (Data)                           │
├─────────────────────────────────────────────────────────────┤
│ 短期记忆 │ 长期记忆    │ 用户画像     │ 配置数据  │ 缓存数据   │
└─────────────────────────────────────────────────────────────┘
```



## 重构后项目结构

text

```
ai-girlfriend-agent/
├── .github/workflows/              # CI/CD配置
│   ├── ci.yml
│   └── deploy.yml
├── docker/                         # Docker配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx/
├── docs/                           # 文档
│   ├── api.md
│   ├── architecture.md
│   └── deployment.md
├── config/                         # 配置中心
│   ├── __init__.py
│   ├── settings.py                # 主配置
│   ├── development.py             # 开发环境
│   ├── production.py              # 生产环境
│   ├── personalities/             # 人格配置
│   │   ├── base.yaml
│   │   ├── gentle_caring.yaml
│   │   ├── lively_cute.yaml
│   │   └── intellectual.yaml
│   ├── prompts/                   # 提示词库
│   │   ├── system/
│   │   ├── memory/
│   │   └── response/
│   └── security/                  # 安全配置
│       ├── filters.yaml
│       └── rate_limits.yaml
├── src/                           # 源代码
│   ├── __init__.py
│   ├── main.py                    # 应用入口
│   ├── app.py                     # FastAPI应用
│   ├── interfaces/                # 接口层
│   │   ├── __init__.py
│   │   ├── wechat/
│   │   │   ├── client.py         # 微信客户端
│   │   │   ├── handler.py        # 消息处理器
│   │   │   └── adapter.py        # 平台适配器
│   │   ├── web/                  # Web接口
│   │   │   ├── admin.py          # 管理后台
│   │   │   ├── api.py            # REST API
│   │   │   └── websocket.py      # WebSocket
│   │   └── cli/                  # 命令行接口
│   │       ├── commands.py
│   │       └── shell.py
│   ├── services/                  # 服务层
│   │   ├── __init__.py
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── provider.py       # AI提供商抽象
│   │   │   ├── openai_service.py
│   │   │   ├── qianwen_service.py
│   │   │   └── wenxin_service.py
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py        # 记忆管理器
│   │   │   ├── short_term.py     # 短期记忆
│   │   │   ├── long_term.py      # 长期记忆
│   │   │   └── consolidation.py  # 记忆固化
│   │   ├── emotion/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py       # 情感分析
│   │   │   ├── responder.py      # 情感回应
│   │   │   └── tracker.py        # 情感追踪
│   │   ├── scheduler/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py        # 任务管理器
│   │   │   ├── tasks.py          # 定时任务
│   │   │   └── triggers.py       # 事件触发器
│   │   └── storage/
│   │       ├── __init__.py
│   │       ├── database.py       # 数据库
│   │       ├── cache.py          # 缓存
│   │       └── file_store.py     # 文件存储
│   ├── core/                     # 核心模块
│   │   ├── __init__.py
│   │   ├── personality/
│   │   │   ├── __init__.py
│   │   │   ├── system.py         # 人格系统
│   │   │   ├── evolution.py      # 人格演化
│   │   │   └── traits.py         # 人格特质
│   │   ├── relationship/
│   │   │   ├── __init__.py
│   │   │   ├── builder.py        # 关系构建器
│   │   │   ├── intimacy.py       # 亲密度管理
│   │   │   └── rituals.py        # 仪式感
│   │   ├── conversation/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py         # 对话引擎
│   │   │   ├── processor.py      # 对话处理器
│   │   │   ├── context.py        # 上下文管理
│   │   │   └── learning.py       # 对话学习
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── filter.py         # 内容过滤
│   │   │   ├── validator.py      # 输入验证
│   │   │   └── rate_limiter.py   # 频率限制
│   │   └── coordinator/          # 主控调度
│   │       ├── __init__.py
│   │       ├── dispatcher.py     # 消息分发
│   │       ├── workflow.py       # 工作流
│   │       └── state.py          # 状态管理
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py               # 用户模型
│   │   ├── conversation.py       # 对话模型
│   │   ├── memory.py             # 记忆模型
│   │   └── system.py             # 系统模型
│   ├── utils/                    # 工具类
│   │   ├── __init__.py
│   │   ├── logger.py             # 日志
│   │   ├── helpers.py            # 辅助函数
│   │   ├── validators.py         # 验证器
│   │   ├── decorators.py         # 装饰器
│   │   └── exceptions.py         # 异常处理
│   └── scripts/                  # 脚本
│       ├── __init__.py
│       ├── setup.py              # 安装脚本
│       ├── migrate.py            # 数据迁移
│       ├── backup.py             # 备份脚本
│       └── monitor.py            # 监控脚本
├── data/                         # 数据目录
│   ├── database/                 # 数据库文件
│   ├── cache/                    # 缓存文件
│   ├── logs/                     # 日志文件
│   └── backups/                  # 备份文件
├── tests/                        # 测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   └── e2e/                      # 端到端测试
├── requirements/                 # 依赖管理
│   ├── base.txt                  # 基础依赖
│   ├── dev.txt                   # 开发依赖
│   ├── prod.txt                  # 生产依赖
│   └── test.txt                  # 测试依赖
├── .env.example                  # 环境变量示例
├── .gitignore
├── pyproject.toml                # 项目配置
├── README.md                     # 项目说明
├── LICENSE                       # 许可证
└── CHANGELOG.md                  # 更新日志
```





## 核心模块说明

### 1. **主控调度 (Coordinator)**

- 消息路由分发
- 工作流状态管理
- 服务协调

### 2. **记忆学习系统 (Memory Learning)**

- **短期记忆**: 最近对话上下文
- **长期记忆**: 固化的重要信息
- **情景记忆**: 具体事件和经历
- **情感记忆**: 情感连接和模式

### 3. **人格演化系统 (Personality Evolution)**

- 基础人格模板
- 动态特质调整
- 用户适配学习
- 渐进式变化

### 4. **关系构建器 (Relationship Builder)**

- 亲密度计算
- 信任度建立
- 内部语言发展
- 共同经历强化

## 配置文件说明

### pyproject.toml

toml

```
[project]
name = "ai-girlfriend-agent"
version = "0.1.0"
description = "基于微信的AI女友聊天机器人"
authors = [{name = "Your Name", email = "your.email@example.com"}]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "itchat>=1.3.10",
    "openai>=1.0.0",
    "pydantic>=2.0.0",
    "sqlalchemy>=2.0.0",
    "redis>=5.0.0",
    "schedule>=1.2.0",
    "loguru>=0.7.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.0.0",
]
prod = [
    "gunicorn>=21.0.0",
    "supervisor>=4.2.0",
]

[tool.black]
line-length = 88
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 88

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```



### requirements/base.txt

txt

```
# 核心框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# 微信接口
itchat==1.3.10
wechaty==0.9.18
wechatpy==2.0.2

# AI服务
openai==1.6.1
qianfan==0.3.1
dashscope==1.14.0

# 数据存储
sqlalchemy==2.0.23
alembic==1.12.1
redis==5.0.1
pymongo==4.5.0

# 异步处理
asyncio==3.4.3
aiohttp==3.9.1
aioredis==2.0.1

# 工具类
python-dotenv==1.0.0
loguru==0.7.2
schedule==1.2.0
pytz==2023.3
python-dateutil==2.8.2

# NLP基础
jieba==0.42.1
snownlp==0.12.3
pinyin==0.4.0
```

## 关键技术栈

- **后端框架**: FastAPI + Uvicorn
- **微信接入**: itchat/wechaty双方案
- **AI服务**: OpenAI + 国产大模型备选
- **数据库**: SQLite(开发) + PostgreSQL(生产)
- **缓存**: Redis
- **消息队列**: Redis Streams
- **配置管理**: Pydantic Settings
- **日志系统**: Loguru
- **测试框架**: Pytest
- **部署**: Docker + Docker Compose

------

# AI实现提示词

## 项目概述

请实现一个基于微信的AI女友聊天机器人，具备以下核心特性：

### 核心要求

1. **记忆学习能力**: 能从对话中学习用户特征，逐渐变成用户记忆中的模样
2. **人格演化**: 基于用户互动动态调整人格特质
3. **情感智能**: 识别和适应用户情感状态
4. **长期关系**: 建立和维持深度情感连接

### 技术栈选择

- 使用 **FastAPI** 作为Web框架
- 使用 **itchat** 作为微信接入方案（支持备选wechaty）
- 使用 **OpenAI API** 作为主要AI引擎，支持国产大模型切换
- 使用 **SQLAlchemy** ORM + **SQLite**（开发）/ **PostgreSQL**（生产）
- 使用 **Redis** 作为缓存和消息队列
- 使用 **Pydantic Settings** 进行配置管理

## 实现要点

### 第一阶段：基础框架 (1-3天)

1. 搭建项目结构和配置系统
2. 实现微信消息接收和发送基础功能
3. 集成千问 API完成基础对话
4. 实现简单的对话上下文管理

### 第二阶段：记忆系统 (3-5天)

1. 实现短期记忆（最近对话）
2. 实现长期记忆存储和检索
3. 实现记忆固化机制（重要信息转为长期记忆）
4. 实现用户画像构建和更新

### 第三阶段：人格系统 (2-4天)

1. 实现基础人格模板（温柔体贴、活泼可爱等）
2. 实现人格参数动态调整
3. 实现基于用户特征的人格适配
4. 实现渐进式人格演化

### 第四阶段：高级功能 (3-6天)

1. 情感识别和回应系统
2. 关系亲密度计算和维护
3. 定时问候和提醒功能
4. 内容安全过滤和频率限制

## 开发规范

### 代码结构

- 遵循上述项目结构
- 模块间通过接口解耦
- 服务层提供统一API
- 配置文件分离，支持环境切换

### 代码质量

- 类型提示（Python 3.9+）
- 异步/协程优先
- 错误处理和日志记录
- 单元测试覆盖率 > 70%

### 配置要求

- 敏感信息通过环境变量管理
- 支持多环境配置（开发/测试/生产）
- 配置文件支持热重载

## 启动顺序

1. 配置环境变量（.env文件）
2. 安装依赖：`pip install -r requirements/base.txt`
3. 初始化数据库：`python src/scripts/setup.py`
4. 启动应用：`python src/main.py`
5. 扫描微信二维码登录

## 验收标准

### 基本功能

- 能正常接收和发送微信消息
- 能维持10轮以上的连贯对话
- 能记住用户的姓名和基本信息
- 能根据时间发送问候（早上好/晚安）

### 记忆学习

- 能记住用户提到的喜好和厌恶
- 能回忆之前的对话内容
- 能识别用户的情感状态变化
- 能基于历史互动调整回应风格

### 人格演化

- 初期使用预设人格
- 2周后能显示个性变化
- 能适配用户的沟通风格
- 能发展独特的内部语言

### 系统稳定性

- 7x24小时稳定运行
- 异常情况优雅降级
- 支持断线重连
- 内存和CPU使用可控

## 注意事项

### 伦理和安全

1. **明确告知AI身份**: 每次对话开始或定期提醒用户这是AI
2. **隐私保护**: 本地化存储用户数据，不上传敏感信息
3. **内容过滤**: 过滤不当内容，避免有害建议
4. **心理健康**: 避免过度依赖，提供求助资源提示

### 用户体验

1. **响应速度**: 普通消息3秒内响应
2. **错误处理**: 网络问题时友好提示
3. **离线支持**: 断网时基础功能可用
4. **可配置性**: 允许用户调整AI性格和响应频率

### 扩展性考虑

1. **插件系统**: 预留功能扩展接口
2. **多平台**: 架构支持微信/Telegram/QQ等平台
3. **多模型**: 支持切换不同AI提供商
4. **多语言**: 支持中英文，可扩展其他语言

## 监控和日志

1. 关键操作记录日志
2. 性能指标监控（响应时间、内存使用）
3. 对话质量评估（用户满意度）
4. 异常警报机制

## 交付物

1. 完整的项目代码库
2. Docker镜像和部署脚本
3. API文档和开发文档
4. 用户使用指南
5. 运维监控手册

