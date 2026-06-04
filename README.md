# 🤖 值班机器人管理平台

钉钉自定义机器人桌面管理工具，支持外网/内网双模式、多机器人配置、消息流编排、Excel 数据处理、定时消息发送、系统托盘常驻。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| **🎯 定时消息** | 选择机器人 + 输入消息内容 + 设置时间和重复规则（每天/工作日/每周），开关控制启停 |
| **📢 值班消息** | 多选机器人 + 值班表 + 可选附加消息 + @所有人，支持手动发送和定时任务 |
| **💬 消息流** | 工作流方式编排消息（自定义文本 → 数据处理结果 → 发送），支持保存复用 |
| **📊 数据处理** | 上传 Excel → 编排数据流步骤（6 大类 25 种节点）→ 执行预览，支持保存数据流 |
| **⚙️ 功能配置** | 机器人 Webhook 管理（内外网切换 + 加签）+ 表格上传与文件管理 |
| **📨 发送日志** | 统一查看所有发送记录，按来源区分，支持清空 |
| **📝 调试日志** | 后端运行日志实时查看，自动刷新 + 导出 TXT |
| **🖥️ 系统托盘** | 关闭窗口后托盘常驻，定时任务持续运行，侧边栏可折叠 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | HTML/CSS/JS（单文件） |
| 桌面壳 | [Eel](https://github.com/python-eel/Eel)（Python ↔ JS WebSocket 桥接） |
| 托盘 | pystray + Pillow |
| 后端 | Python 3.10+ |
| 数据处理 | 纯 Python + openpyxl（无 pandas/numpy 依赖，打包体积 < 30MB） |
| 定时调度 | APScheduler |
| 数据库 | SQLite（`~/.dutybot/dutybot.db`） |
| 消息推送 | 钉钉 Webhook（Markdown + 加签，兼容内外网） |
| 打包 | PyInstaller（+ UPX 压缩） |

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- Chrome 或 Chromium 浏览器

### 2. 安装依赖

```bash
cd dutyBot
pip install -r requirements.txt
```

### 3. 启动应用

```bash
python main.py
```

应用自动打开桌面窗口，系统托盘出现蓝色图标。关闭窗口后应用不会退出，定时任务持续运行。

---

## 使用指南

### 定时消息

1. 点击左侧 **「定时消息」**
2. 勾选目标机器人
3. 输入消息内容（支持 Markdown）
4. 设置执行时间和重复规则（每天 / 工作日 / 每周）
5. 可选开启 @所有人，点击 **「添加」**

任务列表中通过开关控制启停，支持删除。

### 值班消息

1. 点击左侧 **「值班消息」**
2. 勾选目标机器人（支持全选/反选/取消）
3. 选择值班信息表
4. 可选填写附加消息（将拼接在值班信息后）
5. 可选开启 @所有人，点击 **「立即发送」**
6. 点击 **「+ 添加任务」** 可创建定时值班通知

> 值班表来源：数据库中的值班表 + 已上传的 Excel 文件

### 消息流

1. 点击左侧 **「消息流」**
2. 添加步骤，选择类型：
   - **自定义文本**：输入 Markdown 消息内容
   - **数据处理结果**：选择上传文件 + 已保存的数据流，自动执行并导出表格
   - **发送消息**：选择机器人 + @所有人开关
3. 点击 **「预览」** 查看拼接后的消息
4. 点击 **「▶ 执行发送」** 一键发送
5. 保存消息流，下次加载后更换文件即可复用

### 数据处理

1. 在「功能配置 → 表格上传」中上传 Excel 文件
2. 点击左侧 **「数据处理」**，选择已上传的文件
3. 编排数据流步骤（6 大类 25 种节点）：
   - 文本操作（筛选、替换、截取等）
   - 数值操作（筛选、四则运算、取整、聚合）
   - 日期操作（格式化、提取）
   - 列操作（删除、重命名、拆分、合并、跨列计算）
   - 行操作（去重、排序、空值填充）
   - 高级操作（分组聚合、透视表）
4. 点击 **「执行数据流」**，在弹窗中预览结果
5. 支持保存数据流并复用

### 功能配置

- **机器人配置**：管理钉钉 Webhook，切换外网/内网模式，输入 Access Token 和加签 Secret
- **表格上传**：上传 `.xlsx` 文件，解析预览数据，管理已上传文件列表

### 发送日志

统一查看所有发送记录，按时间倒序排列，彩色标签区分「值班消息」和「消息流」来源。

### 调试日志

深色终端风格实时日志，支持自动刷新（3 秒间隔）和导出 TXT。

### 系统托盘

- 关闭窗口 → 托盘常驻，定时任务继续运行
- 右键托盘图标 → 显示窗口 / 退出应用
- 侧边栏底部按钮 → 折叠/展开侧边栏

---

## 项目结构

```
dutyBot/
├── main.py                 # 应用入口（窗口 + 托盘 + 单实例锁）
├── config.py               # 全局配置
├── database.py             # 数据库初始化
├── models.py               # 数据访问层
├── bot_manager.py          # 机器人 CRUD
├── duty_table_manager.py   # 值班表管理
├── message_sender.py       # 钉钉消息发送 + 加签
├── scheduler_manager.py    # 定时任务调度
├── eel_bridge.py           # Eel 前后端桥接
├── node_registry.py        # 数据处理节点注册（25 种节点，纯 Python）
├── workflow_engine.py      # 数据流执行引擎
├── utils.py                # 工具函数
├── generate_robot_icon.py  # 托盘图标生成
├── requirements.txt        # Python 依赖
├── README.md               # 本文件
└── web/
    ├── console.html        # 前端界面
    ├── robot.png           # 托盘图标
    └── message.png         # 消息图标
```

---

## 数据存储

所有数据存储在 `~/.dutybot/` 目录下：

| 文件 | 说明 |
|------|------|
| `dutybot.db` | SQLite 数据库（机器人、值班表、定时任务、数据流、消息流、发送日志） |
| `logs/dutybot.log` | 应用运行日志 |
| `uploads/` | 上传的 xlsx 文件缓存 |

---

## 打包部署

### Windows

```cmd
:: 1. 安装依赖
pip install -r requirements.txt

:: 2. 下载 UPX（https://github.com/upx/upx/releases），解压到 C:\tools\upx

:: 3. 打包
pyinstaller --onefile --windowed ^
    --upx-dir=C:\tools\upx ^
    --add-data "web;web" ^
    --name dutyBot ^
    main.py
```

> 打包后 exe 体积约 **22-28 MB**（含 UPX 压缩），远低于同类工具的 150MB+。

### macOS

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 UPX: brew install upx

# 3. 打包
pyinstaller --onefile --windowed \
    --upx-dir=/opt/homebrew/bin \
    --add-data "web:web" \
    --name dutyBot \
    main.py
```
