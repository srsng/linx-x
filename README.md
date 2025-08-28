# Music MCP Server

## 概述

基于云存储构建的音乐网盘 MCP Server，为用户提供智能化的音乐文件管理体验。

### 多租户特性

- **独立认证**：每个客户端独立验证
- **会话隔离**：每个连接独立的会话上下文
- **并发安全**：多个客户端同时访问不会相互干扰
- **动态配置**：通过 HTTP headers 传递认证信息

## 工具

1. 音乐文件列表 `list_music`
    - 描述: 获取音乐文件列表，可以使用`prefix`根据路径过滤，返回音乐文件的key（名称，路径，还可以用于获取下载url）列表
    - 参数:
      - `max_keys` 最大返回的文件对象数量，默认为100，最大为500
      - `prefix` 音乐文件名前缀过滤。只返回路径以此前缀开头的音乐文件
      - `start_after` 分页起始位置。从指定的音乐文件名之后开始列出，用于实现分页浏览
    - 输出: 音乐文件列表，包含`Bucket`, `Key`, `Size`等信息

2. 音乐播放链接 `get_music_url`
    - 描述: 使用通过`list_music`获取到的音乐文件key，获取指定音乐文件的播放URL。可以使用此URL直接在音乐播放器中播放音乐，无需下载完整文件
    - 参数:
      - `key` 音乐对应的key，通过`list_music`获得
      - `expires` 链接有效期，单位秒，默认3600秒
    - 输出: 播放URL信息，包含`bucket`, `key`, `url`, `size`, `mime_type`等

## 环境要求

- uv

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

## 部署

任意支持MCP协议的客户端（如Claude for Desktop、Cursor、Cherry Studio 和 Cline等）都可以简单且快速的接入音乐网盘MCP Server。

在传输方式上，音乐网盘MCP Server支持：

- HTTP 远程传输
  - [Server-Sent Events](https://en.wikipedia.org/wiki/Server-sent_events)（SSE）

1. 克隆仓库并进入目录

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

4. 启动服务器

```bash
uv --directory . run music-mcp-server --transport sse --port 8000
```

### 配置

本音乐网盘服务器采用会话感知模式，通过HTTP头部传递认证信息，无需配置环境变量。
客户端连接时需要在HTTP头部提供以下认证信息：

- `X-AK`: 七牛云Access Key
- `X-SK`: 七牛云Secret Key  
- `X-REGION-NAME`: 音乐存储区域名称
- `X-BUCKETS`: 音乐存储桶列表（逗号分隔，如：music-library,albums,playlists）

### Cursor 平台远程接入音乐网盘MCP Server示例

对于SSE接入，需在配置文件中添加

```json
{
  "mcpServers": {
    "music-mcp-server-SSE": {
      "url": "http://localhost:8000/sse",
      "headers": {
        "X-AK": "your-access-key",
        "X-SK": "your-secret-key",
        "X-REGION-NAME": "your-region",
        "X-BUCKETS": "bucket1,bucket2"
      }
    }
  }
}
```

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
