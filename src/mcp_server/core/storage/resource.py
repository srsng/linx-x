import logging
import base64

from mcp import types
from urllib.parse import unquote

from mcp.server.lowlevel.helper_types import ReadResourceContents

from .storage import StorageService
from ...consts import consts
from ...resource import resource
from ...resource.resource import ResourceContents
from ...session import get_session_context
from ...context import current_session_id

logger = logging.getLogger(consts.LOGGER_NAME)


class _SessionAwareResourceProvider(resource.ResourceProvider):
    def __init__(self):
        super().__init__("s3")

    async def list_resources(
        self, prefix: str = "", max_keys: int = 300, **kwargs
    ) -> list[types.Resource]:
        """
        List cached music files as resources with pagination
        Args:
            prefix: Prefix filter for resource names
            max_keys: Returns the maximum number of keys (default 300)
        """
        from ...session import session_manager

        resources = []
        logger.debug("Starting to list cached music resources")

        session_id = current_session_id.get()
        if not session_id:
            logger.warning("No session_id found in context")
            return resources

        try:
            music_cache = session_manager.get_music_cache()

            # 获取分页参数
            offset = kwargs.get("offset", 0)

            # 从缓存中获取音乐文件列表
            music_resources = music_cache.get_music_files(
                session_id, offset=offset, limit=max_keys
            )

            for music_resource in music_resources:
                # 应用前缀过滤
                if prefix and not music_resource.name.startswith(prefix):
                    continue

                resources.append(music_resource)

            logger.debug(f"Listed {len(resources)} music resources from cache")

        except Exception as e:
            logger.error(f"Error listing music resources from cache: {str(e)}")

        logger.info(f"Returning {len(resources)} music resources")
        return resources

    async def read_resource(self, uri: types.AnyUrl, **kwargs) -> ResourceContents:
        """
        Read content from an S3 resource and return structured response

        Returns:
            Dict containing 'contents' list with uri, mimeType, and text for each resource
        """
        uri_str = str(uri)
        logger.debug(f"Reading resource: {uri_str}")

        if not uri_str.startswith("s3://"):
            raise ValueError("Invalid S3 URI")

        # Parse the S3 URI
        path = uri_str[5:]  # Remove "s3://"
        path = unquote(path)  # Decode URL-encoded characters
        parts = path.split("/", 1)

        if len(parts) < 2:
            raise ValueError("Invalid S3 URI format")

        bucket = parts[0]
        key = parts[1]

        session_id = current_session_id.get()
        async with get_session_context(session_id) as session_config:
            storage = StorageService.from_session_config(session_config)
            response = await storage.get_object(bucket, key)
            file_content = response["Body"]

            content_type = response.get("ContentType", "application/octet-stream")
            # 根据内容类型返回不同的响应
            if content_type.startswith("image/"):
                file_content = base64.b64encode(file_content).decode("utf-8")

            return [ReadResourceContents(mime_type=content_type, content=file_content)]


def register_resource_provider():
    resource_provider = _SessionAwareResourceProvider()
    resource.register_resource_provider(resource_provider)
