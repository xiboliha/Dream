# AI Girlfriend Agent

基于微信的AI女友聊天机器人，具备记忆学习、人格演化和情感智能能力。

## 功能特性

- **记忆学习系统**: 从对话中学习用户特征，建立长期记忆
- **人格演化**: 基于用户互动动态调整人格特质
- **情感智能**: 识别和适应用户情感状态
- **关系系统**: 亲密度追踪，关系阶段演进
- **多AI支持**: 支持OpenAI、通义千问等多种AI服务
- **多接口**: 支持微信、CLI命令行、REST API三种接口

## 快速开始

### 环境要求

- Python 3.9+
- Redis (可选，用于缓存，不安装会使用内存缓存)

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd ai-girlfriend-agent

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

2. 编辑 `.env` 文件，配置必要的API密钥：
```ini
# 选择AI服务提供商 (openai 或 qianwen)
AI_PROVIDER=qianwen

# 通义千问配置 (推荐国内用户使用)
QIANWEN_API_KEY=sk-your-qianwen-api-key

# 或者使用 OpenAI
# AI_PROVIDER=openai
# OPENAI_API_KEY=sk-your-openai-api-key
```

### 运行

项目提供三种运行模式：

#### 1. 微信模式 (默认)
```bash
# Windows:
run.bat wechat
# 或直接:
python src/main.py

# Linux/Mac:
./run.sh wechat
```
首次运行会显示微信登录二维码，使用微信扫码登录即可。

#### 2. CLI命令行模式 (测试用)
```bash
# Windows:
run.bat cli
# 或:
python src/interfaces/cli/shell.py

# Linux/Mac:
./run.sh cli
```
无需微信，直接在命令行中与AI对话，适合开发测试。

#### 3. REST API模式
```bash
# Windows:
run.bat api
# 或:
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000

# Linux/Mac:
./run.sh api
```
启动后访问 http://localhost:8000/docs 查看API文档。

### 初始化设置
```bash
# Windows:
run.bat setup
# Linux/Mac:
./run.sh setup
```

## 项目结构

```
ai-girlfriend-agent/
├── config/                     # 配置文件
│   ├── settings.py            # 主配置
│   ├── personalities/         # 人格配置 (YAML)
│   │   ├── gentle_caring.yaml # 温柔体贴型
│   │   ├── lively_cute.yaml   # 活泼可爱型
│   │   └── intellectual.yaml  # 知性优雅型
│   ├── prompts/               # 提示词模板
│   │   ├── system/           # 系统提示词
│   │   └── memory/           # 记忆提取提示词
│   └── security/              # 安全配置
│       ├── filters.yaml      # 内容过滤规则
│       └── rate_limits.yaml  # 频率限制
├── src/                        # 源代码
│   ├── main.py                # 微信模式入口
│   ├── app.py                 # FastAPI应用
│   ├── interfaces/            # 接口层
│   │   ├── wechat/           # 微信接口
│   │   ├── cli/              # 命令行接口
│   │   └── web/              # Web接口 (预留)
│   ├── services/              # 服务层
│   │   ├── ai/               # AI服务 (OpenAI/千问)
│   │   ├── memory/           # 记忆服务
│   │   ├── emotion/          # 情感分析
│   │   ├── scheduler/        # 定时任务
│   │   └── storage/          # 存储服务
│   ├── core/                  # 核心模块
│   │   ├── conversation/     # 对话引擎
│   │   ├── personality/      # 人格系统
│   │   ├── relationship/     # 关系系统
│   │   ├── security/         # 安全过滤
│   │   └── coordinator/      # 主控调度
│   ├── models/                # 数据模型
│   └── utils/                 # 工具类
├── data/                       # 数据目录
│   ├── database/             # SQLite数据库
│   ├── cache/                # 缓存文件
│   └── logs/                 # 日志文件
├── tests/                      # 测试
│   ├── unit/                 # 单元测试
│   └── integration/          # 集成测试
├── docker/                     # Docker配置
├── requirements/               # 依赖管理
│   ├── base.txt              # 基础依赖
│   ├── dev.txt               # 开发依赖
│   └── prod.txt              # 生产依赖
├── run.bat                     # Windows启动脚本
├── run.sh                      # Linux/Mac启动脚本
└── pyproject.toml              # 项目配置
```

## 核心模块详解

### 1. 记忆系统

记忆系统是本项目的核心，分为三层：

- **短期记忆**: 保存最近20条对话上下文，用于维持对话连贯性
- **长期记忆**: 固化重要信息（用户姓名、偏好、重要事件等）
- **记忆固化**: AI自动评估短期记忆的重要性，将重要信息转为长期记忆

记忆类型：
- `fact`: 事实信息（姓名、年龄、职业等）
- `preference`: 偏好信息（喜欢/不喜欢的事物）
- `event`: 事件记忆（重要日期、经历）
- `relationship`: 关系信息（家人、朋友）
- `emotion`: 情感记忆

### 2. 人格系统

预设三种人格类型，每种人格有不同的特质配置：

| 人格类型 | 特点 | 适合场景 |
|---------|------|---------|
| 温柔体贴 (gentle_caring) | 高共情、高耐心、善于安慰 | 需要情感支持时 |
| 活泼可爱 (lively_cute) | 高活力、爱用表情、幽默 | 日常闲聊、娱乐 |
| 知性优雅 (intellectual) | 理性、有深度、善于分析 | 讨论问题、求建议 |

人格会根据用户互动逐渐演化适配用户的沟通风格。

### 3. 关系系统

关系分为6个阶段，随着互动逐渐升级：

1. **陌生人** (0-10): 正式称呼，保持距离
2. **熟人** (10-30): 开始熟悉
3. **朋友** (30-50): 可以使用昵称
4. **好朋友** (50-70): 主动关心
5. **挚友** (70-90): 深度信任
6. **灵魂伴侣** (90-100): 完全默契

### 4. 情感分析

自动识别用户情绪并调整回应方式：
- 开心时一起分享喜悦
- 难过时给予安慰陪伴
- 焦虑时提供理性分析
- 愤怒时帮助平复情绪

### 5. 安全机制

- **内容过滤**: 过滤敏感话题，保护用户
- **频率限制**: 防止滥用
- **心理健康保护**: 检测危机关键词，提供求助资源
- **AI身份提醒**: 定期提醒用户这是AI

## API接口

启动API模式后，主要接口：

| 接口 | 方法 | 说明 |
|-----|------|-----|
| `/health` | GET | 健康检查 |
| `/chat` | POST | 发送消息 |
| `/users/{id}/status` | GET | 获取用户关系状态 |
| `/users/{id}/memories` | GET | 获取用户记忆 |
| `/users/{id}/greeting` | POST | 获取问候语 |
| `/personalities` | GET | 获取可用人格列表 |

详细文档访问: http://localhost:8000/docs

## Docker部署

```bash
cd docker
docker-compose up -d
```

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

### 代码格式化
```bash
# 格式化代码
black src/
isort src/

# 类型检查
mypy src/
```

### 添加新人格

在 `config/personalities/` 目录下创建新的YAML文件：

```yaml
name: my_personality
display_name: 我的人格
description: 自定义人格描述

traits:
  warmth: 0.7
  empathy: 0.8
  playfulness: 0.5
  # ... 其他特质

language_style:
  formality: 0.4
  emoji_usage: 0.6
  pet_names: true

expressions:
  greetings:
    - "你好呀~"
    - "嗨~"
```

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
- **微信接入**: itchat-uos
- **AI服务**: OpenAI API / 阿里云DashScope
- **数据库**: SQLAlchemy + SQLite/PostgreSQL
- **缓存**: Redis (可选)
- **日志**: Loguru
- **测试**: Pytest

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
