# Claude Code 项目指南

## 项目信息
- 项目名称: AI Girlfriend Agent (Nuyoah)
- GitHub: https://github.com/xiboliha/Dream
- 文档位置: `cclogs/claude.md`

## 重要规则

### 1. 对话记录
每次会话结束前，必须更新 `cclogs/claude.md` 文档的"开发日志"部分，记录：
- 日期和会话主题
- 完成的主要工作
- 修改的关键文件
- 待优化项

### 2. 项目文档同步
当项目结构或功能发生重大变化时，同步更新 `cclogs/claude.md` 的相关章节：
- 项目结构
- 核心功能
- API接口
- 环境配置

### 3. Git 提交规范
- 使用中文提交信息
- 格式: `feat/fix/docs: 简要描述`
- 提交前确认所有更改已测试

## 快速启动

```bash
# 启动 Qdrant
docker start qdrant

# 启动服务
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

## 常用路径

| 用途 | 路径 |
|------|------|
| 主配置 | `config/settings.py` |
| 系统提示词 | `config/prompts/system/base_prompt.txt` |
| 对话数据集 | `config/knowledge/dialogue_dataset.json` |
| 聊天页面 | `src/interfaces/web/chat.html` |
| 监控页面 | `src/interfaces/web/monitor.html` |
| 日志系统 | `src/utils/logger.py` |
| 项目文档 | `cclogs/claude.md` |

## 当前状态

- AI模型: glm-4.7 (阿里云百炼)
- RAG后端: Qdrant
- 服务端口: 8000
