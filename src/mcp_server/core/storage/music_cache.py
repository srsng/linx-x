"""音乐文件缓存模块

提供音乐文件的缓存管理功能，包括：
- 预加载音乐文件到内存缓存
- 支持会话级别的文件隔离
- 提供音乐文件查询和分页功能
"""

import asyncio
import logging
from typing import Any, Dict, List, Set
from mcp import types

from .storage import StorageService
from ...consts import consts
from ...session import SessionConfig

logger = logging.getLogger(consts.LOGGER_NAME)

# 常量定义
MAX_OBJ_PER_BUCKET = 3000
MAX_CONCURRENT_BUCKETS = 3
DEFAULT_PAGE_SIZE = 300

# 支持的音乐文件扩展名
MUSIC_EXTENSIONS: Set[str] = {
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".ogg",
    ".wma",
    ".m4a",
    ".opus",
    ".ape",
    ".dsd",
    ".dsf",
    ".dff",
}

# MIME类型映射
MIME_TYPE_MAP: Dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "wma": "audio/x-ms-wma",
    "m4a": "audio/mp4",
    "opus": "audio/opus",
    "ape": "audio/x-ape",
    "dsd": "audio/dsd",
    "dsf": "audio/dsf",
    "dff": "audio/dff",
}


class MusicCache:
    """音乐文件缓存管理器"""

    def __init__(self) -> None:
        """初始化音乐缓存管理器"""
        # 每个session_id对应一个音乐文件列表
        self._session_music_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_lock = asyncio.Lock()

    def _is_valid_music_object(self, obj: Dict[str, Any]) -> bool:
        """检查对象是否为有效的音乐文件

        Args:
            obj: 存储对象信息

        Returns:
            是否为有效的音乐文件
        """
        # 检查是否有Key字段
        if "Key" not in obj:
            return False

        key = obj["Key"]

        # 过滤掉目录（以/结尾）
        if key.endswith("/"):
            return False

        # 过滤掉空文件
        if obj.get("Size", 0) <= 0:
            return False

        # 检查是否为音乐文件
        return self._is_music_file(key)

    async def _process_bucket(
        self,
        storage: StorageService,
        bucket: Dict[str, Any],
        semaphore: asyncio.Semaphore,
    ) -> List[Dict[str, Any]]:
        """处理单个bucket，提取其中的音乐文件

        Args:
            storage: 存储服务实例
            bucket: bucket信息
            semaphore: 并发控制信号量

        Returns:
            该bucket中的音乐文件列表
        """
        async with semaphore:
            bucket_name = bucket["Name"]
            logger.debug(f"处理音乐目录: {bucket_name}")

            bucket_music_files = []

            try:
                # 获取该bucket下的所有对象
                objects = await storage.list_objects(
                    bucket_name, max_keys=MAX_OBJ_PER_BUCKET
                )

                for obj in objects:
                    if self._is_valid_music_object(obj):
                        # 为对象添加bucket和url信息
                        obj_with_bucket = obj.copy()
                        obj_with_bucket["Bucket"] = bucket_name

                        # 获取URL
                        key = obj_with_bucket["Key"]
                        try:
                            object_urls = storage.get_object_url(bucket_name, key)

                            if object_urls:
                                # 默认选择第一个URL
                                obj_with_bucket["URL"] = object_urls[0].get(
                                    "object_url"
                                )
                        except Exception as url_exc:
                            logger.warning(f"无法获取文件 {key} 的URL: {url_exc}")
                            obj_with_bucket["URL"] = None

                        bucket_music_files.append(obj_with_bucket)

                logger.info(
                    f"从bucket {bucket_name} 加载了 {len(bucket_music_files)} 个音乐文件"
                )

            except Exception as e:
                logger.error(f"处理音乐目录 {bucket_name} 时出错: {str(e)}")

            return bucket_music_files

    async def preload_music_files(
        self, session_id: str, session_config: SessionConfig
    ) -> int:
        """预加载指定会话的所有音乐文件

        Args:
            session_id: 会话ID
            session_config: 会话配置

        Returns:
            加载的音乐文件数量

        Raises:
            Exception: 预加载失败时抛出异常
        """
        async with self._cache_lock:
            logger.info(f"开始为会话 {session_id} 预加载音乐文件")

            try:
                storage = StorageService.from_session_config(session_config)

                # 获取所有bucket
                buckets = await storage.list_buckets()
                logger.debug(f"找到 {len(buckets)} 个音乐目录")

                if not buckets:
                    logger.warning(f"会话 {session_id} 没有找到任何音乐目录")
                    self._session_music_cache[session_id] = []
                    return 0

                # 限制并发处理bucket的数量
                semaphore = asyncio.Semaphore(MAX_CONCURRENT_BUCKETS)

                # 并发处理所有bucket
                bucket_results = await asyncio.gather(
                    *[
                        self._process_bucket(storage, bucket, semaphore)
                        for bucket in buckets
                    ],
                    return_exceptions=True,
                )

                # 合并所有bucket的音乐文件
                music_files = []
                for result in bucket_results:
                    if isinstance(result, list):
                        music_files.extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"处理bucket时发生异常: {result}")

                # 缓存音乐文件列表
                self._session_music_cache[session_id] = music_files
                logger.info(
                    f"为会话 {session_id} 预加载了 {len(music_files)} 个音乐文件"
                )

                return len(music_files)

            except Exception as e:
                logger.error(f"预加载音乐文件失败: {str(e)}")
                # 确保即使失败也有一个空的缓存
                self._session_music_cache[session_id] = []
                raise

    def _is_music_file(self, filename: str) -> bool:
        """判断文件是否为音乐文件

        Args:
            filename: 文件路径/键名

        Returns:
            是否为音乐文件
        """
        if not filename or not isinstance(filename, str):
            return False

        return any(filename.lower().endswith(ext) for ext in MUSIC_EXTENSIONS)

    def _get_music_mime_type(self, filename: str) -> str:
        """根据文件扩展名获取MIME类型

        Args:
            filename: 文件名

        Returns:
            对应的MIME类型，默认为audio/mpeg
        """
        if not filename or "." not in filename:
            return "audio/mpeg"

        ext = filename.lower().split(".")[-1]
        return MIME_TYPE_MAP.get(ext, "audio/mpeg")

    def get_music_files(
        self, session_id: str, offset: int = 0, limit: int = DEFAULT_PAGE_SIZE
    ) -> List[types.Resource]:
        """获取指定会话的音乐文件列表，支持分页

        Args:
            session_id: 会话ID
            offset: 偏移量，从0开始
            limit: 返回的最大文件数量，默认为DEFAULT_PAGE_SIZE

        Returns:
            音乐文件资源列表
        """
        music_files = self._session_music_cache.get(session_id, [])

        # 分页处理
        start_idx = offset
        end_idx = min(offset + limit, len(music_files))
        paginated_files = music_files[start_idx:end_idx]

        # 转换为Resource格式
        resources = []
        for obj in paginated_files:
            object_key = obj["Key"]
            bucket_name = obj["Bucket"]
            mime_type = self._get_music_mime_type(object_key)
            resource = types.Resource(
                uri=f"s3://{bucket_name}/{object_key}",
                name=object_key,
                mimeType=mime_type,
                description=f"音乐文件: {object_key} (大小: {obj.get('Size', 0)} 字节)",
                url=obj.get("URL"),
            )
            resources.append(resource)

        logger.debug(
            f"返回会话 {session_id} 的音乐文件: {len(resources)} 个 (总共 {len(music_files)} 个)"
        )
        return resources

    def find_music_by_key(self, session_id: str, key: str) -> List[Dict[str, Any]]:
        """根据文件key查找音乐文件，可能在多个bucket中存在

        Args:
            session_id: 会话ID
            key: 文件键名

        Returns:
            匹配的音乐文件信息列表
        """
        music_files = self._session_music_cache.get(session_id, [])
        matches = []

        for obj in music_files:
            if obj["Key"] == key:
                matches.append(obj)

        logger.debug(
            f"在会话 {session_id} 中找到 {len(matches)} 个匹配的音乐文件: {key}"
        )
        return matches

    def get_total_count(self, session_id: str) -> int:
        """获取指定会话的音乐文件总数

        Args:
            session_id: 会话ID

        Returns:
            音乐文件总数
        """
        return len(self._session_music_cache.get(session_id, []))

    def clear_session_cache(self, session_id: str) -> bool:
        """清除指定会话的缓存

        Args:
            session_id: 会话ID

        Returns:
            是否成功清除缓存
        """
        if session_id in self._session_music_cache:
            del self._session_music_cache[session_id]
            logger.info(f"清除会话 {session_id} 的音乐文件缓存")
            return True
        return False

    def get_cached_sessions(self) -> List[str]:
        """获取所有已缓存的会话ID

        Returns:
            已缓存的会话ID列表
        """
        return list(self._session_music_cache.keys())


# 全局音乐缓存管理器实例
music_cache = MusicCache()
