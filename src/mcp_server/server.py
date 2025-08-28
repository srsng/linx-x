import asyncio
import logging

import anyio
import click

from . import application
from .consts import consts
from .session import session_manager
from .context import current_session_id
from .config.config import load_config_from_headers

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(consts.LOGGER_NAME)
logger.info("Starting MCP server")

SAMPLE_RESOURCES = {
    "greeting": "Hello! This is a MCP Server for music.",
    "help": "This server provides a few resources and tools for music.",
    "about": "This is the MCP server implementation.",
}


@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> int:
    app = application.server

    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.requests import Request
        from starlette.responses import JSONResponse

        sse = SseServerTransport("/messages/")

        async def handle_sse(request: Request):
            # 从HTTP headers提取认证信息
            headers = dict(request.headers)
            config, error_msg = load_config_from_headers(headers)

            if not config:
                logger.error(f"Header validation failed: {error_msg}")
                return JSONResponse(status_code=401, content={"error": error_msg})

            # 创建会话并预加载音乐文件
            session_id = await session_manager.create_session(
                access_key=config.access_key,
                secret_key=config.secret_key,
                endpoint_url=config.endpoint_url,
                region_name=config.region_name,
                buckets=config.buckets,
            )

            logger.info(f"Created session {session_id} for SSE connection")

            try:
                # 先设置上下文变量，再建立和运行连接，确保后续回调都能读取到
                token = current_session_id.set(session_id)
                try:
                    async with sse.connect_sse(
                        request.scope, request.receive, request._send
                    ) as streams:
                        await app.run(
                            streams[0], streams[1], app.create_initialization_options()
                        )
                finally:
                    current_session_id.reset(token)
            finally:
                # 清理会话
                session_manager.remove_session(session_id)
                logger.info(f"Cleaned up session {session_id}")

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        import uvicorn

        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)

    return 0


if __name__ == "__main__":
    asyncio.run(main())
