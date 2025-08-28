import logging
from typing import Any, Dict, List, Optional

from mcp import types

from .storage import StorageService
from ...consts import consts
from ...tools import tools
from ...session import get_session_context

logger = logging.getLogger(consts.LOGGER_NAME)

# 常量定义
DEFAULT_MAX_KEYS = 100
MAX_ALLOWED_KEYS = 500
DEFAULT_URL_EXPIRES = 3600  # 1小时


class SessionAwareToolImpl:
    """会话感知的音乐存储工具实现"""

    # @tools.tool_meta(
    #     types.Tool(
    #         name="get_music_directories",
    #         description="获取当前用户的所有音乐目录列表。",
    #         inputSchema={
    #             "type": "object",
    #             "properties": {
    #                 "prefix": {
    #                     "type": "string",
    #                     "description": "音乐目录前缀。列出的音乐目录将根据此前缀进行过滤，仅输出匹配前缀的音乐目录。",
    #                 },
    #             },
    #             "required": [],
    #         },
    #     )
    # )
    # async def get_music_directories(
    #     self, session_id: Optional[str] = None, **kwargs: Any
    # ) -> List[types.TextContent]:
    #     try:
    #         async with get_session_context(session_id) as session_config:
    #             storage = StorageService.from_session_config(session_config)
    #             buckets = await storage.list_buckets(**kwargs)
    #             return [types.TextContent(type="text", text=str(buckets))]
    #     except Exception as e:
    #         logger.error(f"获取音乐目录失败: {e}")
    #         return [types.TextContent(type="text", text=f"获取音乐目录失败: {str(e)}")]

    def _filter_music_files(
        self,
        music_files: List[Dict[str, Any]],
        bucket: Optional[str] = None,
        prefix: str = "",
        start_after: str = "",
    ) -> List[Dict[str, Any]]:
        """过滤音乐文件列表

        Args:
            music_files: 原始音乐文件列表
            bucket: 目录过滤条件
            prefix: 文件名前缀过滤条件
            start_after: 分页起始位置

        Returns:
            过滤后的音乐文件列表
        """
        filtered_files = []

        for obj in music_files:
            # bucket过滤
            if bucket and obj.get("Bucket") != bucket:
                continue

            # prefix过滤
            if prefix and not obj.get("Key", "").startswith(prefix):
                continue

            # start_after过滤（用于分页）
            if start_after and obj.get("Key", "") <= start_after:
                continue

            filtered_files.append(obj)

        return filtered_files

    def _validate_and_normalize_params(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """验证和标准化参数

        Args:
            kwargs: 原始参数字典

        Returns:
            标准化后的参数字典
        """
        max_keys = kwargs.get("max_keys", DEFAULT_MAX_KEYS)

        # 限制max_keys的范围
        if max_keys > MAX_ALLOWED_KEYS:
            max_keys = MAX_ALLOWED_KEYS
        elif max_keys < 1:
            max_keys = DEFAULT_MAX_KEYS

        return {
            "bucket": kwargs.get("bucket"),
            "max_keys": max_keys,
            "prefix": kwargs.get("prefix", ""),
            "start_after": kwargs.get("start_after", ""),
        }

    @tools.tool_meta(
        types.Tool(
            name="get_music_list",
            description="获取音乐文件列表, 可以使用`prefix`根据路径过滤, 返回音乐文件的key（名称，路径，还可以用于获取下载url）列表。",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_keys": {
                        "type": "integer",
                        "description": "最大返回的文件对象数量，默认为100，最大为500",
                    },
                    "prefix": {
                        "type": "string",
                        "description": "音乐文件名前缀过滤。只返回路径以此前缀开头的音乐文件。",
                    },
                    "start_after": {
                        "type": "string",
                        "description": "分页起始位置。从指定的音乐文件名之后开始列出，用于实现分页浏览。",
                    },
                },
                "required": [],
            },
        )
    )
    async def get_music_list(
        self, session_id: Optional[str] = None, **kwargs: Any
    ) -> List[types.TextContent]:
        try:
            from ...session import session_manager

            # 验证和标准化参数
            params = self._validate_and_normalize_params(kwargs)

            # 从音乐缓存中获取文件列表
            music_cache = session_manager.get_music_cache()
            music_files = music_cache._session_music_cache.get(session_id, [])

            if not music_files:
                return [types.TextContent(type="text", text="暂无音乐文件")]

            # 过滤文件
            filtered_files = self._filter_music_files(
                music_files,
                bucket=params["bucket"],
                prefix=params["prefix"],
                start_after=params["start_after"],
            )

            # 限制返回数量
            max_keys = params["max_keys"]
            if len(filtered_files) > max_keys:
                filtered_files = filtered_files[:max_keys]

            return [types.TextContent(type="text", text=str(filtered_files))]

        except Exception as e:
            logger.error(f"获取音乐文件列表失败: {e}")
            return [
                types.TextContent(type="text", text=f"获取音乐文件列表失败: {str(e)}")
            ]

    def _create_music_url_info(
        self, obj: Dict[str, Any], key: str, url: str, mime_type: str
    ) -> Dict[str, Any]:
        """创建音乐URL信息字典

        Args:
            obj: 音乐文件对象
            key: 文件key
            url: 播放URL
            mime_type: MIME类型

        Returns:
            包含完整信息的字典
        """
        return {
            "bucket": obj["Bucket"],
            "key": key,
            "url": url,
            "size": obj.get("Size", 0),
            "mime_type": mime_type,
        }

    @tools.tool_meta(
        types.Tool(
            name="get_music_url",
            description="使用通过get_music_list获取到的音乐文件key，获取指定音乐文件的播放URL。可以使用此URL直接在音乐播放器中播放音乐，无需下载完整文件。",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "音乐对应的key，通过get_music_list获得。",
                    },
                    # "disable_ssl": {
                    #     "type": "boolean",
                    #     "description": "Whether to disable HTTPS, default to use HTTPS",
                    # },
                    # "expires": {
                    #     "type": "integer",
                    #     "description": "URL过期时间（秒），默认3600秒（1小时）",
                    #     "default": 3600,
                    # },
                },
                "required": ["key"],
            },
        )
    )
    async def get_music_url(
        self, session_id: Optional[str] = None, **kwargs: Any
    ) -> List[types.TextContent]:
        """获取音乐文件播放URL

        根据文件key生成可直接播放的URL，支持多个同名文件。

        Args:
            session_id: 会话ID，用于多租户隔离
            **kwargs: 包含key和expires参数

        Returns:
            包含URL信息的文本内容
        """
        try:
            from ...session import session_manager

            # 参数验证
            key = kwargs.get("key")
            if not key:
                return [types.TextContent(type="text", text="缺少必需参数: key")]

            expires = kwargs.get("expires", DEFAULT_URL_EXPIRES)

            async with get_session_context(session_id) as session_config:
                storage = StorageService.from_session_config(session_config)
                music_cache = session_manager.get_music_cache()

                # 在缓存中查找所有匹配的音乐文件
                matching_files = music_cache.find_music_by_key(session_id, key)

                if not matching_files:
                    return [
                        types.TextContent(type="text", text=f"未找到音乐文件: {key}")
                    ]

                urls = []
                for obj in matching_files:
                    bucket_name = obj["Bucket"]
                    try:
                        # 生成播放URL
                        url = storage.get_object_url(
                            bucket=bucket_name, key=key, expires=expires
                        )

                        # 获取MIME类型
                        mime_type = music_cache._get_music_mime_type(key)

                        # 创建URL信息
                        url_info = self._create_music_url_info(obj, key, url, mime_type)
                        urls.append(url_info)

                    except Exception as e:
                        logger.warning(
                            f"为bucket {bucket_name}, key {key}生成URL失败: {e}"
                        )
                        continue

                if not urls:
                    return [
                        types.TextContent(type="text", text=f"无法生成播放URL: {key}")
                    ]

                return [types.TextContent(type="text", text=str(urls))]

        except Exception as e:
            logger.error(f"获取音乐URL失败: {e}")
            return [types.TextContent(type="text", text=f"获取音乐URL失败: {str(e)}")]

    # @tools.tool_meta(
    #     types.Tool(
    #         name="get_object",
    #         description="从指定的音乐目录下获取指定的音乐文件内容。",
    #         inputSchema={
    #             "type": "object",
    #             "properties": {
    #                 "bucket": {
    #                     "type": "string",
    #                     "description": _BUCKET_DESC,
    #                 },
    #                 "key": {
    #                     "type": "string",
    #                     "description": "Key of the object to get.",
    #                 },
    #             },
    #             "required": ["bucket", "key"],
    #         },
    #     )
    # )
    # async def get_object(
    #     self, session_id: str | None = None, **kwargs
    # ) -> list[ImageContent] | list[TextContent]:
    #     async with get_session_context(session_id) as session_config:
    #         storage = StorageService.from_session_config(session_config)
    #         response = await storage.get_object(**kwargs)
    #         file_content = response["Body"]
    #         content_type = response.get("ContentType", "application/octet-stream")

    #         # 根据内容类型返回不同的响应
    #         if content_type.startswith("image/"):
    #             base64_data = base64.b64encode(file_content).decode("utf-8")
    #             return [
    #                 types.ImageContent(
    #                     type="image_url",
    #                     image_url=f"data:{content_type};base64,{base64_data}",
    #                 )
    #             ]
    #         else:
    #             text_content = file_content.decode("utf-8", errors="ignore")
    #             return [types.TextContent(type="text", text=text_content)]

    # @tools.tool_meta(
    #     types.Tool(
    #         name="upload_object",
    #         description="Upload a file to Qiniu Cloud bucket. You can upload a local file or provide file content directly.",
    #         inputSchema={
    #             "type": "object",
    #             "properties": {
    #                 "bucket": {
    #                     "type": "string",
    #                     "description": _BUCKET_DESC,
    #                 },
    #                 "key": {
    #                     "type": "string",
    #                     "description": "Key of the object to upload.",
    #                 },
    #                 "file_path": {
    #                     "type": "string",
    #                     "description": "Local file path to upload.",
    #                 },
    #                 "content": {
    #                     "type": "string",
    #                     "description": "File content to upload directly.",
    #                 },
    #             },
    #             "required": ["bucket", "key"],
    #         },
    #     )
    # )
    # async def upload_object(
    #     self, session_id: str | None = None, **kwargs
    # ) -> list[types.TextContent]:
    #     async with get_session_context(session_id) as session_config:
    #         storage = StorageService.from_session_config(session_config)
    #         result = await storage.upload_object(**kwargs)
    #         return [types.TextContent(type="text", text=str(result))]


def register_session_aware_tools() -> None:
    """注册会话感知的音乐存储工具"""
    impl = SessionAwareToolImpl()

    # 注册对外提供的工具
    tools.auto_register_tools(
        [
            impl.get_music_list,  # 音乐文件列表工具
            impl.get_music_url,  # 音乐URL生成工具
        ]
    )

    logger.info("音乐存储工具注册完成")
