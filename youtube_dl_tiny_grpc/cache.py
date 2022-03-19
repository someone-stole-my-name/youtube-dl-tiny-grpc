from __future__ import annotations

import asyncio
import gzip
import logging
from hashlib import md5
from typing import Any

from aioredis import from_url
from aioredis.exceptions import ConnectionError

log = logging.getLogger(__name__)


def _md5_str(_str: str) -> str:
    return md5(_str.encode("utf-8"), usedforsecurity=False).hexdigest()


async def gen_key(val: str, *args: str) -> str:
    """ Generate a unique key from the given arguments. """
    loop = asyncio.get_running_loop()
    unique_key = await loop.run_in_executor(None, _md5_str, val)
    for arg in args:
        unique_key = unique_key + await loop.run_in_executor(None,
                                                             _md5_str,
                                                             arg)
    unique_key = await loop.run_in_executor(None, _md5_str,
                                            unique_key)
    return unique_key


class Cache(object):
    """ Wrapper around aioredis to manage cache. """

    def __init__(self, uri: str, ttl: int):
        log.info("Initializing!")
        self.uri = uri
        self.ttl = ttl
        self.redis = from_url(
            self.uri,
            decode_responses=False
        )

    async def _is_online(self) -> bool:
        """ Check if the redis server is online. """
        try:
            await self.redis.ping()
        except ConnectionError:
            log.error('cannot connect to redis: %s', self.uri)
            return False
        except Exception as ex:  # pylint: disable=broad-except
            log.exception(ex)
            return False
        return True

    async def get(self, key: str) -> Any | None:
        """ Get the content of the given key. """
        if not await self._is_online():
            return None

        async with self.redis as redis_client:
            cached_ok = await redis_client.get(key)
            if cached_ok:
                return gzip.decompress(cached_ok).decode("utf-8")
        return None

    async def set(self, key: str, content: str) -> None:
        """ Set the content of the given key. """
        if not await self._is_online():
            return None

        async with self.redis as redis_client:
            await redis_client.set(
                key,
                gzip.compress(content.encode("utf-8")),
                ex=self.ttl
            )
        return None
