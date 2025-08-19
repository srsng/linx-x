#!/usr/bin/env python3
"""
多租户功能测试脚本
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiTenantTester:
    """多租户功能测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def test_sse_connection(self, headers: Dict[str, str]) -> bool:
        """测试SSE连接"""
        try:
            response = await self.client.get(
                f"{self.base_url}/sse",
                headers={
                    "Accept": "text/event-stream",
                    **headers
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.info(f"SSE connection successful with headers: {list(headers.keys())}")
                return True
            else:
                logger.error(f"SSE connection failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"SSE connection error: {e}")
            return False
    
    async def test_multiple_clients(self):
        """测试多个客户端并发连接"""
        # 模拟不同客户端的认证信息
        clients = [
            {
                "name": "Client 1",
                "headers": {
                    "X-AK": "client1-ak",
                    "X-SK": "client1-sk",
                    "X-ENDPOINT-URL": "https://s3.test-region.qiniucs.com",
                    "X-REGION-NAME": "test-region",
                    "X-BUCKETS": "client1-bucket1,client1-bucket2"
                }
            },
            {
                "name": "Client 2", 
                "headers": {
                    "X-AK": "client2-ak",
                    "X-SK": "client2-sk",
                    "X-ENDPOINT-URL": "https://s3.test-region.qiniucs.com",
                    "X-REGION-NAME": "test-region",
                    "X-BUCKETS": "client2-bucket1"
                }
            },
            {
                "name": "Client 3",
                "headers": {
                    "X-AK": "client3-ak",
                    "X-SK": "client3-sk",
                    "X-ENDPOINT-URL": "https://s3.test-region.qiniucs.com",
                    "X-REGION-NAME": "test-region",
                    "X-BUCKETS": "client3-bucket1,client3-bucket2,client3-bucket3"
                }
            }
        ]
        
        logger.info("Testing multiple client connections...")
        
        # 并发测试所有客户端
        tasks = []
        for client in clients:
            task = self.test_single_client(client)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 分析结果
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"{clients[i]['name']} failed: {result}")
            elif result:
                success_count += 1
                logger.info(f"{clients[i]['name']} succeeded")
            else:
                logger.error(f"{clients[i]['name']} failed")
        
        logger.info(f"Test completed: {success_count}/{len(clients)} clients succeeded")
        return success_count == len(clients)
    
    async def test_single_client(self, client: Dict[str, Any]) -> bool:
        """测试单个客户端连接"""
        logger.info(f"Testing {client['name']}...")
        return await self.test_sse_connection(client['headers'])
    
    async def test_invalid_auth(self):
        """测试无效认证"""
        logger.info("Testing invalid authentication...")
        
        # 测试缺少认证头
        result1 = await self.test_sse_connection({})
        
        # 测试无效的认证信息
        result2 = await self.test_sse_connection({
            "X-AK": "invalid-ak",
            "X-SK": "invalid-sk"
        })
        
        # 应该都失败
        if not result1 and not result2:
            logger.info("Invalid authentication test passed")
            return True
        else:
            logger.error("Invalid authentication test failed")
            return False
    
    async def cleanup(self):
        """清理资源"""
        await self.client.aclose()


async def main():
    """主测试函数"""
    tester = MultiTenantTester()
    
    try:
        logger.info("Starting multi-tenant tests...")
        
        # 测试无效认证
        auth_test = await tester.test_invalid_auth()
        
        # 测试多客户端并发
        multi_client_test = await tester.test_multiple_clients()
        
        # 输出结果
        logger.info("=" * 50)
        logger.info("Test Results:")
        logger.info(f"Invalid Auth Test: {'PASS' if auth_test else 'FAIL'}")
        logger.info(f"Multi-Client Test: {'PASS' if multi_client_test else 'FAIL'}")
        logger.info("=" * 50)
        
        if auth_test and multi_client_test:
            logger.info("All tests passed! 🎉")
        else:
            logger.error("Some tests failed! ❌")
            
    except Exception as e:
        logger.error(f"Test execution error: {e}")
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
