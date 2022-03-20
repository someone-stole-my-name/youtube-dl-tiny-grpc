from __future__ import annotations
import asyncio
import json
import logging
import random

from google.protobuf.json_format import MessageToDict, ParseDict
import grpc
from youtube_dl import YoutubeDL

from .cache import Cache, gen_key
from .protobuf.youtube_dl_tiny_grpc_pb2 import ExtractInfoRequest, ExtractInfoResponse
from .protobuf.youtube_dl_tiny_grpc_pb2_grpc import (
    YoutubeDLServicer as YoutubeDLServerBase,
)
from .util import ProcessPoolExecutor

# Offload all youtube_dl processing to a separate process in this pool
# Idea from https://github.com/grpc/grpc/issues/16001
_YOUTUBE_DL_PROCESS_POOL: ProcessPoolExecutor | None = None

# Default options for youtube-dl itself
_YOUTUBE_DL_DEFAULT_OPTS = {}

# The cache ssot
_YOUTUBE_DL_CACHE: Cache | None = None

# List of proxies to use in youtube-dl
_YOUTUBE_DL_PROXY_LIST: list | None = None

log = logging.getLogger(__name__)


def configure(
        default_opts: dict,
        process_pool: ProcessPoolExecutor,
        cache: Cache | None,
        proxy_list) -> None:
    global _YOUTUBE_DL_DEFAULT_OPTS
    global _YOUTUBE_DL_PROCESS_POOL
    global _YOUTUBE_DL_PROXY_LIST
    global _YOUTUBE_DL_CACHE
    _YOUTUBE_DL_DEFAULT_OPTS = default_opts
    _YOUTUBE_DL_PROCESS_POOL = process_pool
    _YOUTUBE_DL_PROXY_LIST = proxy_list
    _YOUTUBE_DL_CACHE = cache


def shutdown_pool() -> None:
    global _YOUTUBE_DL_PROCESS_POOL
    if isinstance(_YOUTUBE_DL_PROCESS_POOL, ProcessPoolExecutor):
        log.info("stopping process pool")
        _YOUTUBE_DL_PROCESS_POOL.shutdown(False)
    else:
        log.warning("cannot stop a non existent process pool")


class YoutubeDLServer(YoutubeDLServerBase):
    """Provides methods that implement functionality of YoutubeDL server."""

    def __init__(self):
        self.cache = _YOUTUBE_DL_CACHE

    @staticmethod
    def _extract_info(
            url: str,
            opts: dict = {},
            retries: int = 0,
            proxy: list = [],
            proxy_timeout: int = 30) -> dict:
        """Wrapper around youtube-dl's extract_info method
        to handle retries with proxy rotation."""
        count = retries
        real_ydl_opts = opts

        if proxy:
            r_proxy = random.choice(proxy)
            real_ydl_opts['proxy'] = r_proxy
            real_ydl_opts['socket_timeout'] = proxy_timeout

        try:
            ydl = YoutubeDL(real_ydl_opts)
            info = ydl.extract_info(url, False)
            return info
        except Exception as e:
            if count <= 0:
                raise e
            count = count - 1
            return YoutubeDLServer._extract_info(url, opts, count, proxy,
                                                 proxy_timeout)

    async def ExtractInfo(
            self,
            request: ExtractInfoRequest,
            context: grpc.aio.ServicerContext
    ) -> ExtractInfoResponse:
        if request.url == "" or not isinstance(request.url, str):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                                "invalid URL")

        ydl_custom_opts = MessageToDict(
            request.options,
            including_default_value_fields=False,
            preserving_proto_field_name=True
        )

        ydl_opts = {
            **_YOUTUBE_DL_DEFAULT_OPTS,
            **ydl_custom_opts,
        }

        info = None
        if self.cache is not None:
            cached_ok = await self.cache.get(
                await gen_key(request.url, json.dumps(ydl_opts))
            )
            if cached_ok:
                info = json.loads(cached_ok)

        if info is None:
            real_ydl_opts = ydl_opts

            loop = asyncio.get_event_loop()
            try:
                info = await loop.run_in_executor(
                    _YOUTUBE_DL_PROCESS_POOL,
                    self._extract_info,
                    request.url,
                    real_ydl_opts,
                    5,
                    _YOUTUBE_DL_PROXY_LIST)
            except Exception as e:
                log.exception(e)
                await context.abort(
                    grpc.StatusCode.INTERNAL,
                    "unknown error occurred while extracting info",
                )

            json_info = json.dumps(info)

            if self.cache is not None:
                await self.cache.set(
                    await gen_key(request.url, json.dumps(ydl_opts)),
                    json_info
                )

            # FIXME: Yes, this is a hack.
            # youtube_dl sometimes returns tuples for some repeated fields
            # and ParseDict doesn't like that.
            info = json.loads(json_info)

        try:
            entries = info['entries'][0]['entries']
            for entry in entries:
                yield ParseDict(
                    entry,
                    ExtractInfoResponse(),
                    ignore_unknown_fields=True)
        except KeyError:
            try:
                entries = info['entries']
                for entry in entries:
                    yield ParseDict(
                        entry,
                        ExtractInfoResponse(),
                        ignore_unknown_fields=True)
            except KeyError:
                yield ParseDict(
                    info,
                    ExtractInfoResponse(),
                    ignore_unknown_fields=True)
