# 🍳 杜堡堡小厨房 — 家庭菜谱管理系统

一个轻量级的家庭菜谱管理 Web 应用，支持菜谱管理、点餐下单、冰箱库存管理等功能，还集成了 AI 自动生成菜品图片。

## ✨ 功能特性

- **菜谱管理** — 创建、编辑、删除菜谱，支持食材、步骤、难度、烹饪时间、份量等详细信息
- **分类管理** — 预设分类（顿顿有肉、荤素搭配、时蔬、糖水、其他），支持自定义和排序
- **图片管理** — 支持手动上传图片或通过 AI 自动生成菜品图片（Pollinations.ai）
- **随机推荐** — 一键随机推荐菜品，支持按分类筛选
- **点餐下单** — 按日期和餐次（早/午/晚）下单，自动统计月销量
- **冰箱库存** — 管理家中食材，支持分类、数量、保质期等信息
- **搜索功能** — 全文搜索菜名、描述、食材
- **发现页面** — 统计概览、热门菜品排行、最新菜谱

## 🛠 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3 + Flask |
| 数据库 | SQLite |
| 前端 | 单页应用 (SPA)，纯 HTML/CSS/JS |
| AI 图片 | Pollinations.ai（免费，无需 API Key）|
| 文件上传 | Werkzeug，最大 16MB |

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装

```bash
# 克隆项目
git clone <repo-url> recipe-app
cd recipe-app

# 安装依赖
pip install flask

# 运行
python app.py
```

服务启动后访问 `http://localhost:8083`。

### 命令行参数

默认监听 `0.0.0.0:8083`，可在 `app.py` 末尾修改端口。

## 📁 项目结构

```
recipe-app/
├── app.py              # 主程序（Flask 后端 + API）
├── templates/
│   └── index.html      # 前端 SPA 页面
├── uploads/            # 上传和 AI 生成的图片
├── recipes.db          # SQLite 数据库（自动创建）
├── .gitignore
└── README.md
```

## 📡 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/categories` | 获取所有分类 |
| POST | `/api/categories` | 创建分类 |
| PUT | `/api/categories/<id>` | 更新分类 |
| DELETE | `/api/categories/<id>` | 删除分类 |
| POST | `/api/categories/reorder` | 重排分类 |
| GET | `/api/recipes` | 获取菜谱列表（支持 `category` 和 `search` 参数）|
| POST | `/api/recipes` | 创建菜谱 |
| GET | `/api/recipes/<id>` | 获取单个菜谱 |
| PUT | `/api/recipes/<id>` | 更新菜谱 |
| DELETE | `/api/recipes/<id>` | 删除菜谱 |
| GET | `/api/random` | 随机推荐一道菜 |
| POST | `/api/generate-image` | AI 生成菜品图片 |
| GET | `/api/orders` | 获取订单列表 |
| POST | `/api/orders` | 创建订单 |
| DELETE | `/api/orders/<id>` | 删除订单 |
| GET | `/api/fridge` | 获取冰箱库存 |
| POST | `/api/fridge` | 添加库存 |
| PUT | `/api/fridge/<id>` | 更新库存 |
| DELETE | `/api/fridge/<id>` | 删除库存 |
| GET | `/api/discover` | 发现页统计数据 |

## 📝 备注

- 数据库文件 `recipes.db` 会在首次运行时自动创建
- `uploads/` 目录存放用户上传和 AI 生成的图片
- AI 图片生成使用 Pollinations.ai 免费服务，无需配置 API Key
# test
