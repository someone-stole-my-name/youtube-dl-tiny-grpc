from __future__ import annotations

import asyncio
import gzip
import logging
from hashlib import md5
from typing import Any

import aioredis

log = logging.getLogger(__name__)


def _md5_str(_str: str) -> str:
    return md5(_str.encode("utf-8")).hexdigest()


async def gen_key(v: str, *args: str) -> str:
    loop = asyncio.get_running_loop()
    unique_key = await loop.run_in_executor(None, _md5_str, v)
    for arg in args:
        unique_key = unique_key + await loop.run_in_executor(None,
                                                             _md5_str,
                                                             arg)
    unique_key = await loop.run_in_executor(None, _md5_str,
                                            unique_key)
    return unique_key


class Cache(object):
    def __init__(self, uri: str, ttl: int):
        log.info("Initializing!")
        self.uri = uri
        self.ttl = ttl
        self.redis = aioredis.from_url(
                self.uri,
                decode_responses=False
        )

    async def is_online(self) -> bool:
        try:
            await self.redis.ping()
        except aioredis.exceptions.ConnectionError:
            log.error(f"cannot connect to redis: {self.uri}")
            return False
        except Exception as e:
            log.exception(e)
            return False
        return True

    async def get(self, key: str) -> Any | None:
        if not await self.is_online():
            return None

        async with self.redis as redis_client:
            cached_ok = await redis_client.get(key)
            if cached_ok:
                return gzip.decompress(cached_ok).decode("utf-8")
        return None

    async def set(self, key: str, content: str) -> None:
        if not await self.is_online():
            return None

        async with self.redis as redis_client:
            await redis_client.set(
                    key,
                    gzip.compress(content.encode("utf-8")),
                    ex=self.ttl
            )
        return None
