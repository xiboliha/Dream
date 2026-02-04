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

---

## 开发待办清单 (TODO)

> 最后更新: 2026-02-04

### 高优先级 - 核心体验 (P0)

| 状态 | 功能 | 说明 | 难度 |
|------|------|------|------|
| [ ] | 对话上下文理解优化 | AI经常忽略上下文，回复不连贯（如"骗你的"→"说啥"） | 中 |
| [ ] | 更多对话场景示例 | 丰富few-shot示例，覆盖更多日常场景 | 低 |
| [ ] | 记忆系统优化 | glm-4.7 JSON输出不稳定，记忆提取经常失败 | 中 |
| [x] | 情绪状态追踪 | 根据对话内容动态调整AI情绪状态 | 中 |

### 中优先级 - 功能增强 (P1)

| 状态 | 功能 | 说明 | 难度 |
|------|------|------|------|
| [ ] | 本地模型集成 | 集成qwen1.5-4b等本地模型，降低API成本 | 高 |
| [ ] | 微调数据收集 | 收集高质量对话数据用于模型微调 | 中 |
| [ ] | 搜索结果缓存 | 避免重复搜索，提升响应速度 | 低 |
| [ ] | 更多搜索引擎备选 | 添加Google/DuckDuckGo作为备选 | 中 |
| [ ] | 图片理解能力 | 支持用户发送图片，AI能理解并回复 | 高 |

### 低优先级 - 体验优化 (P2)

| 状态 | 功能 | 说明 | 难度 |
|------|------|------|------|
| [x] | WebSocket实时推送 | 已实现，支持主动消息推送和心跳 | 中 |
| [ ] | 语音消息支持 | TTS/STT集成 | 高 |
| [ ] | 更多人格配置 | 添加更多可切换的人格模板 | 低 |
| [ ] | 日志文件持久化 | 日志写入文件，支持历史查询 | 低 |
| [ ] | 移动端适配 | 优化聊天界面的移动端体验 | 低 |

### 技术债务

| 状态 | 项目 | 说明 |
|------|------|------|
| [x] | 清理测试文件 | 删除 `bing_test.html`, `sogou_debug.html` 等临时文件 |
| [x] | 单元测试 | 添加核心功能的单元测试 |
| [x] | 错误处理 | 完善异常捕获和用户友好的错误提示 |
| [x] | 配置管理 | 敏感配置从代码中分离 |

### 已完成

| 完成日期 | 功能 | 说明 |
|----------|------|------|
| 2026-02-04 | AI情绪状态追踪 | AI根据用户情绪动态调整自身情绪，影响回复风格 |
| 2026-02-04 | 情绪监控系统 | 情绪监控页面，支持查看和手动设置AI情绪 |
| 2026-02-04 | 技术债务清理 | 清理测试文件、完善错误处理、配置管理优化、单元测试 |
| 2026-02-03 | 网络搜索功能 | 必应搜索集成，支持关键词触发 |
| 2026-02-03 | 对话示例优化 | 添加连续对话示例，优化回复语气 |
| 2026-02-02 | 多消息回复 | 支持连发多条消息，模拟真人聊天 |
| 2026-02-02 | 主动消息系统 | 定时问候、空闲检测 |
| 2026-01-30 | RAG系统 | Qdrant向量检索 |
| 2026-01-30 | 监控系统 | 日志查看、统计 |

---

## 开发日志

### 2026-02-04 会话记录（续）

#### AI情绪状态追踪功能

1. **AIEmotionState 系统**
   - 创建 `src/services/emotion/ai_emotion_state.py`
   - 定义9种AI情绪状态：happy, content, caring, playful, worried, sad, annoyed, shy, excited
   - 实现情绪转换规则（用户情绪→AI情绪）
   - 情绪强度追踪和衰减机制

2. **情绪转换逻辑**
   - 用户开心 → AI开心
   - 用户难过/生气/焦虑 → AI关心
   - 用户表达爱意 → AI害羞
   - 用户兴奋 → AI兴奋
   - 用户惊讶 → AI俏皮

3. **对话引擎集成**
   - 修改 `src/core/conversation/engine.py`
   - 分析用户消息情绪
   - 根据用户情绪更新AI情绪状态
   - 将AI情绪注入系统提示词

4. **情绪监控API**
   - `GET /emotion/state/{user_id}` - 获取AI情绪状态
   - `GET /emotion/history/{user_id}` - 获取情绪历史
   - `POST /emotion/set/{user_id}` - 手动设置情绪（测试用）
   - `GET /emotion/all` - 获取所有用户情绪状态
   - `GET /emotion/moods` - 获取可用情绪类型
   - `GET /emotion-monitor` - 情绪监控页面

5. **情绪监控页面**
   - 创建 `src/interfaces/web/emotion_monitor.html`
   - 实时显示AI当前情绪和强度
   - 情绪历史记录查看
   - 手动设置情绪功能（测试用）
   - 情绪分布统计

#### 关键文件修改

- `src/services/emotion/ai_emotion_state.py` - 新建，AI情绪状态管理
- `src/services/emotion/__init__.py` - 导出新类
- `src/core/conversation/engine.py` - 集成情绪分析和AI情绪
- `src/app.py` - 添加情绪监控API
- `src/interfaces/web/emotion_monitor.html` - 新建，情绪监控页面

#### 新增API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/emotion/state/{user_id}` | GET | 获取AI情绪状态 |
| `/emotion/history/{user_id}` | GET | 获取情绪历史 |
| `/emotion/set/{user_id}` | POST | 手动设置情绪 |
| `/emotion/all` | GET | 所有用户情绪状态 |
| `/emotion/moods` | GET | 可用情绪类型 |
| `/emotion-monitor` | GET | 情绪监控页面 |

#### AI情绪类型

| 情绪 | 英文 | 描述 |
|------|------|------|
| 开心 | happy | 说话带着愉悦和活力 |
| 满足 | content | 心情平静满足，说话温和自然 |
| 关心 | caring | 温柔体贴，想要安慰和照顾对方 |
| 俏皮 | playful | 喜欢开玩笑和调侃 |
| 担心 | worried | 关切对方的情况 |
| 难过 | sad | 说话比较低落 |
| 小生气 | annoyed | 撒娇式地抱怨 |
| 害羞 | shy | 说话比较含蓄 |
| 兴奋 | excited | 语气更加热情 |

### 2026-02-04 会话记录

#### 主要完成工作

1. **技术债务清理**
   - 删除临时测试文件（bing_test.html, sogou_debug.html等9个文件）
   - 清理git未跟踪的调试文件

2. **错误处理系统完善**
   - 增强 `src/utils/exceptions.py` 异常类
   - 为所有异常添加 `status_code`, `error_code`, `user_message` 属性
   - 添加 `to_dict()` 方法用于API响应
   - 新增异常类：`RAGServiceError`, `SearchServiceError`, `ServiceUnavailableError`, `ValidationError`
   - 在 `src/app.py` 添加全局异常处理器
   - 更新所有API端点使用自定义异常

3. **配置管理优化**
   - 更新 `config/settings.py` 添加配置验证器
   - 添加 `validate_log_level()` 和 `validate_rag_backend()` 验证
   - 配置错误使用 `ConfigurationError` 异常
   - 添加 `is_production()` 和 `is_development()` 辅助方法
   - 更新 `.env.example` 添加缺失的配置项（RAG、定时任务等）

4. **单元测试扩展**
   - 扩展 `tests/unit/test_utils.py` 异常测试
   - 添加新异常类的测试用例
   - 测试 `to_dict()` 方法和属性

5. **文档更新**
   - 更新 `CLAUDE.md` 添加TODO维护规则
   - 更新 `cclogs/claude.md` TODO清单

#### 关键文件修改

- `src/utils/exceptions.py` - 增强异常类
- `src/app.py` - 全局异常处理器，更新API端点
- `config/settings.py` - 配置验证，辅助方法
- `.env.example` - 添加缺失配置项
- `CLAUDE.md` - 添加TODO维护规则
- `tests/unit/test_utils.py` - 扩展异常测试

#### 新增异常类

| 异常类 | HTTP状态码 | 错误码 | 用途 |
|--------|-----------|--------|------|
| `RAGServiceError` | 503 | RAG_SERVICE_ERROR | RAG服务不可用 |
| `SearchServiceError` | 503 | SEARCH_SERVICE_ERROR | 搜索服务不可用 |
| `ServiceUnavailableError` | 503 | SERVICE_UNAVAILABLE | 服务未初始化 |
| `ValidationError` | 400 | VALIDATION_ERROR | 输入验证失败 |
