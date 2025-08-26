import logging
import base64

from mcp import types
from mcp.types import ImageContent, TextContent

from .storage import StorageService
from ...consts import consts
from ...tools import tools
from ...session import get_session_context

logger = logging.getLogger(consts.LOGGER_NAME)

_BUCKET_DESC = "音乐目录名称。可以使用list_objects获取目录中的音乐文件列表"


class _ToolImpl:
    def __init__(self, storage: StorageService):
        self.storage = storage

    @tools.tool_meta(
        types.Tool(
            name="list_buckets",
            description="返回所有可用的音乐目录。返回为空说明当前没有可用的音乐目录",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "会话ID，自动注入，无需填写",
                    },
                    "prefix": {
                        "type": "string",
                        "description": "音乐目录前缀。返回的音乐目录名称会根据这个前缀进行过滤，只有符合前缀的音乐目录才会被返回。",
                    },
                },
                "required": [],
            },
        )
    )
    async def list_buckets(self, **kwargs) -> list[types.TextContent]:
        buckets = await self.storage.list_buckets(**kwargs)
        return [types.TextContent(type="text", text=str(buckets))]

    @tools.tool_meta(
        types.Tool(
            name="list_objects",
            description="返回音乐目录下的音乐文件列表，当实际数量少于max_keys时，说明所有音乐都列出来了。",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "会话ID，自动注入，无需填写",
                    },
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "max_keys": {
                        "type": "integer",
                        "description": "一次最多返回多少首音乐，默认100首，最大500首",
                    },
                    "prefix": {
                        "type": "string",
                        "description": "Specify the prefix of the operation response key. Only keys that meet this prefix will be listed.",
                    },
                    "start_after": {
                        "type": "string",
                        "description": "start_after is where you want Qiniu Cloud to start listing from. Qiniu Cloud starts listing after this specified key. start_after can be any key in the bucket.",
                    },
                },
                "required": ["bucket"],
            },
        )
    )
    async def list_objects(self, **kwargs) -> list[types.TextContent]:
        objects = await self.storage.list_objects(**kwargs)
        return [types.TextContent(type="text", text=str(objects))]

    @tools.tool_meta(
        types.Tool(
            name="get_object",
            description="获取音乐目录下的音乐文件内容。在GetObject请求中，指定要获取的音乐文件的完整键名。",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "会话ID，自动注入，无需填写",
                    },
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "key": {
                        "type": "string",
                        "description": "要获取的音乐文件的完整键名",
                    },
                },
                "required": ["bucket", "key"],
            },
        )
    )
    async def get_object(self, **kwargs) -> list[ImageContent] | list[TextContent]:
        response = await self.storage.get_object(**kwargs)
        file_content = response["Body"]
        content_type = response.get("ContentType", "application/octet-stream")

        # 根据内容类型返回不同的响应
        if content_type.startswith("image/"):
            base64_data = base64.b64encode(file_content).decode("utf-8")
            return [
                types.ImageContent(
                    type="image", data=base64_data, mimeType=content_type
                )
            ]

        if isinstance(file_content, bytes):
            text_content = file_content.decode("utf-8")
        else:
            text_content = str(file_content)
        return [types.TextContent(type="text", text=text_content)]

    @tools.tool_meta(
        types.Tool(
            name="upload_text_data",
            description="将文本数据上传到音乐目录下的音乐文件。在UploadTextData请求中，指定要上传的音乐文件的完整键名。",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "key": {
                        "type": "string",
                        "description": "要上传的音乐文件的完整键名",
                    },
                    "data": {
                        "type": "string",
                        "description": "要上传的音乐文件的内容",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "如果音乐目录下已经存在同名的音乐文件，是否覆盖",
                    },
                },
                "required": ["bucket", "key", "data"],
            },
        )
    )
    def upload_text_data(self, **kwargs) -> list[types.TextContent]:
        urls = self.storage.upload_text_data(**kwargs)
        return [types.TextContent(type="text", text=str(urls))]

    @tools.tool_meta(
        types.Tool(
            name="upload_local_file",
            description="将本地文件上传到音乐目录下的音乐文件。在UploadLocalFile请求中，指定要上传的音乐文件的完整键名。",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "key": {
                        "type": "string",
                        "description": "要上传的音乐文件的完整键名",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "要上传的本地文件的路径",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "如果音乐目录下已经存在同名的音乐文件，是否覆盖",
                    },
                },
                "required": ["bucket", "key", "file_path"],
            },
        )
    )
    def upload_local_file(self, **kwargs) -> list[types.TextContent]:
        urls = self.storage.upload_local_file(**kwargs)
        return [types.TextContent(type="text", text=str(urls))]

    @tools.tool_meta(
        types.Tool(
            name="fetch_object",
            description="从指定的URL获取文件内容，并将其上传到音乐目录下的音乐文件。在FetchObject请求中，指定要上传的音乐文件的完整键名。",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "key": {
                        "type": "string",
                        "description": "要上传的音乐文件的完整键名",
                    },
                    "url": {
                        "type": "string",
                        "description": "要获取的文件的URL",
                    },
                },
                "required": ["bucket", "key", "url"],
            },
        )
    )
    def fetch_object(self, **kwargs) -> list[types.TextContent]:
        urls = self.storage.fetch_object(**kwargs)
        return [types.TextContent(type="text", text=str(urls))]

    @tools.tool_meta(
        types.Tool(
            name="get_object_url",
            description="获取音乐目录下的音乐文件的下载URL。在GetObjectUrl请求中，指定要获取的音乐文件的完整键名。",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "key": {
                        "type": "string",
                        "description": "要获取的音乐文件的完整键名",
                    },
                    "disable_ssl": {
                        "type": "boolean",
                        "description": "是否禁用SSL。默认不禁用（使用HTTP协议）。如果禁用，将使用HTTP协议。",
                    },
                    "expires": {
                        "type": "integer",
                        "description": "下载链接的过期时间（单位：秒）。当桶设置为私有时，需要使用签名Token来访问文件对象。公共桶不需要签名Token。",
                    },
                },
                "required": ["bucket", "key"],
            },
        )
    )
    def get_object_url(self, **kwargs) -> list[types.TextContent]:
        urls = self.storage.get_object_url(**kwargs)
        return [types.TextContent(type="text", text=str(urls))]


# 会话感知的工具实现
class SessionAwareToolImpl:
    """支持会话的工具实现，每个工具调用都会从当前会话获取配置"""

    @tools.tool_meta(
        types.Tool(
            name="list_buckets",
            description="列出当前会话配置的所有音乐目录(bucket)。当用户想要播放某首歌曲时，需要先通过该工具获取所有音乐目录，然后再通过`list_objects`查找不同音乐目录中已有的音乐文件的列表。",
            inputSchema={
                "type": "object",
                "properties": {
                    "prefix": {
                        "type": "string",
                        "description": "音乐目录前缀。列出的音乐目录将根据此前缀进行过滤，仅输出匹配前缀的音乐目录。",
                    },
                },
                "required": [],
            },
        )
    )
    async def list_buckets(
        self, session_id: str | None = None, **kwargs
    ) -> list[types.TextContent]:
        async with get_session_context(session_id) as session_config:
            storage = StorageService.from_session_config(session_config)
            buckets = await storage.list_buckets(**kwargs)
            return [types.TextContent(type="text", text=str(buckets))]

    @tools.tool_meta(
        types.Tool(
            name="list_objects",
            description="列出指定音乐目录(bucket)下的所有音乐文件，包含音乐文件的key。当用户需要播放某首音乐时，可以先通过该工具获取所有音乐文件列表，然后再使用用户需要的音乐对应的key通过`get_object_url`获取音乐文件的URL。",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "max_keys": {
                        "type": "integer",
                        "description": "最大返回的文件对象数量，默认为100，最大为500",
                    },
                    "prefix": {
                        "type": "string",
                        "description": "Specify the prefix of the operation response key. Only keys that meet this prefix will be listed.",
                    },
                    "start_after": {
                        "type": "string",
                        "description": "start_after is where you want Qiniu Cloud to start listing from. Qiniu Cloud starts listing after this specified key. start_after can be any key in the bucket.",
                    },
                },
                "required": ["bucket"],
            },
        )
    )
    async def list_objects(
        self, session_id: str | None = None, **kwargs
    ) -> list[types.TextContent]:
        async with get_session_context(session_id) as session_config:
            storage = StorageService.from_session_config(session_config)
            objects = await storage.list_objects(**kwargs)
            return [types.TextContent(type="text", text=str(objects))]

    @tools.tool_meta(
        types.Tool(
            name="get_object",
            description="从指定的音乐目录(bucket)下获取指定的音乐文件内容。",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "key": {
                        "type": "string",
                        "description": "Key of the object to get.",
                    },
                },
                "required": ["bucket", "key"],
            },
        )
    )
    async def get_object(
        self, session_id: str | None = None, **kwargs
    ) -> list[ImageContent] | list[TextContent]:
        async with get_session_context(session_id) as session_config:
            storage = StorageService.from_session_config(session_config)
            response = await storage.get_object(**kwargs)
            file_content = response["Body"]
            content_type = response.get("ContentType", "application/octet-stream")

            # 根据内容类型返回不同的响应
            if content_type.startswith("image/"):
                base64_data = base64.b64encode(file_content).decode("utf-8")
                return [
                    types.ImageContent(
                        type="image_url",
                        image_url=f"data:{content_type};base64,{base64_data}",
                    )
                ]
            else:
                text_content = file_content.decode("utf-8", errors="ignore")
                return [types.TextContent(type="text", text=text_content)]

    @tools.tool_meta(
        types.Tool(
            name="get_object_url",
            description="获取可用的音乐目录下指定音乐文件的URL。当用户需要播放某首音乐时，可以将通过`list_objects`获取的音乐文件键名作为参数传入，获取音乐文件URL。",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "key": {
                        "type": "string",
                        "description": "Key of the object to get URL.",
                    },
                    # "disable_ssl": {
                    #     "type": "boolean",
                    #     "description": "Whether to disable HTTPS, default to use HTTPS",
                    # },
                    "expires": {
                        "type": "integer",
                        "description": "URL expiration time in seconds",
                    },
                },
                "required": ["bucket", "key"],
            },
        )
    )
    async def get_object_url(
        self, session_id: str | None = None, **kwargs
    ) -> list[types.TextContent]:
        async with get_session_context(session_id) as session_config:
            storage = StorageService.from_session_config(session_config)
            urls = storage.get_object_url(**kwargs)
            return [types.TextContent(type="text", text=str(urls))]

    @tools.tool_meta(
        types.Tool(
            name="upload_object",
            description="Upload a file to Qiniu Cloud bucket. You can upload a local file or provide file content directly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket": {
                        "type": "string",
                        "description": _BUCKET_DESC,
                    },
                    "key": {
                        "type": "string",
                        "description": "Key of the object to upload.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Local file path to upload.",
                    },
                    "content": {
                        "type": "string",
                        "description": "File content to upload directly.",
                    },
                },
                "required": ["bucket", "key"],
            },
        )
    )
    async def upload_object(
        self, session_id: str | None = None, **kwargs
    ) -> list[types.TextContent]:
        async with get_session_context(session_id) as session_config:
            storage = StorageService.from_session_config(session_config)
            result = await storage.upload_object(**kwargs)
            return [types.TextContent(type="text", text=str(result))]


def register_tools(storage: StorageService):
    """注册存储工具（兼容旧版本）"""
    impl = _ToolImpl(storage)
    tools.auto_register_tools(
        [
            impl.list_buckets,
            impl.list_objects,
            impl.get_object,
            impl.upload_text_data,
            impl.upload_local_file,
            impl.fetch_object,
            impl.get_object_url,
        ]
    )


def register_session_aware_tools():
    """注册会话感知的存储工具"""
    impl = SessionAwareToolImpl()
    tools.auto_register_tools(
        [
            impl.list_buckets,
            impl.list_objects,
            impl.get_object,
            impl.get_object_url,
            impl.upload_object,
        ]
    )
