# Web3 社交聊天应用

一个基于 Python Flask 的 Web3 社交聊天平台，集成实时聊天、社交互动和内容分享功能于一体的现代化 Web 应用。

## 项目介绍

本项目是一个结合 Web3 理念的社交聊天应用，致力于提供安全、高效的社交体验：

- 💬 实时聊天系统：基于 WebSocket 的即时通讯
- 👥 用户社交系统：好友关系、用户关注
- 📝 内容分享平台：支持发布文章、图片等内容
- 🎯 个性化推荐：基于用户兴趣的内容推荐
- 🔒 安全性保障：数据加密、用户认证

## 技术栈

### 后端
- Python 3.13
- Flask 框架
- Flask-SocketIO：WebSocket 支持
- SQLite：数据持久化
- Redis：缓存和会话管理
- JWT：用户认证

### 前端
- HTML5/CSS3
- JavaScript (原生)
- WebSocket API
- CSS Grid/Flexbox 布局

## 环境要求

- Python >= 3.8
- Redis >= 6.0
- SQLite3
- 现代浏览器（支持 WebSocket）

## 快速开始

### 1. 克隆项目

```bash
git clone [项目地址]
cd web3-social-chat
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 环境配置

创建并配置 `.env` 文件：

```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
REDIS_HOST=localhost
REDIS_PORT=6379
DATABASE_URL=sqlite:///instance/site.db
```

### 4. 初始化数据库

```bash
flask db init
flask db migrate
flask db upgrade
```

### 5. 启动服务

```bash
# 开发环境
flask run

# 生产环境
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app
```

访问 http://localhost:5000 开始使用

## 项目结构

```
backend/
├─ app.py              # 应用入口和路由配置
├─ database.py         # 数据库模型和配置
├─ chat/               # 聊天功能模块
│  └─ websocket_manager.py  # WebSocket 管理器
├─ config/             # 配置文件目录
│  └─ redis_config.py  # Redis 配置
├─ static/             # 静态资源
│  ├─ css/            # 样式文件
│  │  ├─ chatroom.css   # 聊天室样式
│  │  ├─ homepage.css   # 主页样式
│  │  ├─ profile.css    # 个人资料样式
│  │  └─ style.css      # 通用样式
│  ├─ js/             # JavaScript 文件
│  │  ├─ chatroom.js    # 聊天室逻辑
│  │  ├─ homepage.js    # 主页交互
│  │  └─ profile.js     # 个人资料管理
│  └─ image/          # 图片资源
├─ templates/          # HTML 模板
│  ├─ base.html         # 基础模板
│  ├─ chat.html         # 聊天页面
│  ├─ homepage.html     # 主页
│  └─ profile.html      # 个人资料页
└─ utils.py           # 工具函数
```

## 核心功能

### 1. 实时聊天
- 私聊和群聊支持
- 消息实时推送
- 在线状态显示
- 消息历史记录
- 文件传输功能

### 2. 用户系统
- 邮箱/手机号注册
- JWT 身份认证
- 个人资料管理
- 头像上传
- 好友关系管理

### 3. 社交功能
- 发布动态
- 评论与点赞
- 内容分享
- 用户关注
- 消息通知

## API 接口

### 用户相关
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/auth/register | POST | 用户注册 |
| /api/auth/login | POST | 用户登录 |
| /api/user/profile | GET/PUT | 获取/更新用户资料 |

### 聊天相关
| 接口 | 方法 | 描述 |
|------|------|------|
| /ws/chat | WebSocket | 聊天连接 |
| /api/chat/history | GET | 获取聊天历史 |
| /api/chat/rooms | GET | 获取聊天室列表 |

### 社交相关
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/posts | GET/POST | 获取/发布动态 |
| /api/comments | GET/POST | 评论管理 |
| /api/likes | POST | 点赞功能 |

## 开发指南

### 代码规范
- 遵循 PEP 8 编码规范
- 使用 Python 类型注解
- 编写详细的函数文档
- 保持代码简洁清晰

### Git 提交规范
```
feat: 新功能
fix: 修复问题
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建过程或辅助工具的变动
```

## 部署指南

### 1. 服务器要求
- Linux 服务器（推荐 Ubuntu 20.04+）
- Python 3.8+
- Redis 服务
- Nginx 服务器

### 2. 部署步骤
1. 配置 Python 虚拟环境
2. 安装项目依赖
3. 配置 Nginx 反向代理
4. 使用 Supervisor 管理进程
5. 配置 SSL 证书（推荐）

### 3. 监控和维护
- 使用 Supervisor 监控进程
- 配置日志记录
- 定期数据备份
- 性能监控

## 测试

```bash
# 运行所有测试
python -m pytest

# 运行特定测试
python -m pytest test/test_chat.py
```

## 常见问题

1. WebSocket 连接失败
   - 检查防火墙设置
   - 确认 Redis 服务状态
   - 验证客户端 WebSocket 支持

2. 数据库连接问题
   - 检查数据库配置
   - 确认数据库权限
   - 验证连接字符串

## 更新日志

### v1.0.0 (2024-03)
- 初始版本发布
- 基础聊天功能
- 用户系统实现
- 社交功能上线

## 维护者

- 开发团队：Web3 Social Team
- 联系邮箱：contact@web3social.com
- 项目仓库：[GitHub 地址]

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
