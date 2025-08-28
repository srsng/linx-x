# Music MCP Server

## 概述

基于七牛云存储构建的音乐网盘 MCP Server，为用户提供智能化的音乐文件管理体验。

### 多租户特性

- **独立认证**：每个客户端使用自己的 ak、sk
- **会话隔离**：每个连接独立的会话上下文
- **并发安全**：多个客户端同时访问不会相互干扰
- **动态配置**：通过 HTTP headers 传递认证信息

## 功能特性

### 音乐文件管理

- **音乐目录浏览**：获取所有音乐存储目录列表
- **音乐文件列表**：获取和展示音乐文件，支持分页浏览
- **音乐文件上传**：支持本地音乐文件上传到云端
- **音乐播放链接**：生成安全的音乐文件播放URL
- **格式支持**：支持 MP3、FLAC、WAV、AAC、OGG 等主流音频格式

### 智能搜索与过滤

- **文件名搜索**：根据音乐文件名快速定位
- **路径过滤**：按目录结构筛选音乐文件
- **格式筛选**：按音频格式类型过滤文件

### 性能优化

- **预加载缓存**：连接时自动预加载所有音乐文件信息
- **分页展示**：大量音乐文件的高效分页显示
- **并发处理**：多目录并发扫描，快速构建音乐库

## 环境要求

- Python 3.12 或更高版本
- uv 包管理器

如果还没有安装 uv，可以使用以下命令安装：

```bash
# Mac，推荐使用 brew 安装
brew install uv


# Linux & Mac
# 1. 安装
curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. 安装完成后，请确保将软件包安装路径（包含 uv 和 uvx 可执行文件的目录）添加到系统的 PATH 环境变量中。
# 假设安装包路径为 /Users/xxx/.local/bin（见安装执行输出）
### 临时生效（当前会话），在当前终端中执行以下命令：
export PATH="/Users/xxx/.local/bin:$PATH"
### 永久生效（推荐），在当前终端中执行以下命令：
echo 'export PATH="/Users/xxx/.local/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile


# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

具体安装方式参考 [uv 安装](https://docs.astral.sh/uv/getting-started/installation/#pypi)

## 启动

1. 克隆仓库

  <!-- ```bash

  ``` -->

2. 创建并激活虚拟环境：

  ```bash
  uv venv
  source .venv/bin/activate  # Linux/macOS
  # 或
  .venv\Scripts\activate  # Windows
  ```

3. 安装依赖：

  ```bash
  uv pip install -e .
  ```

4. 启动

```bash
uv --directory . run music-mcp-server --transport sse --port 8000
```

5. 连接

4. 配置

本音乐网盘服务器采用会话感知模式，通过HTTP头部传递认证信息，无需配置环境变量。
客户端连接时需要在HTTP头部提供以下认证信息：

- `X-AK`: 七牛云Access Key
- `X-SK`: 七牛云Secret Key  
- `X-REGION-NAME`: 音乐存储区域名称
- `X-BUCKETS`: 音乐存储桶列表（逗号分隔，如：music-library,albums,playlists）

## 开发

扩展功能，首先在 core 目录下新增一个业务包目录（eg: 存储 -> storage），在此业务包目录下完成功能拓展。
在业务包目录下的 `__init__.py` 文件中定义 load 函数用于注册业务工具或者资源，最后在 `core` 目录下的 `__init__.py`
中调用此 load 函数完成工具或资源的注册。

```shell
core
├── __init__.py # 各个业务工具或者资源加载
└── storage # 存储业务目录
    ├── __init__.py # 加载存储工具或者资源
    ├── resource.py # 存储资源扩展
    ├── storage.py # 存储工具类
    └── tools.py # 存储工具扩展
```
