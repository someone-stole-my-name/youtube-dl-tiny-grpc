import asyncio
import json

import grpc
from google.protobuf.json_format import MessageToDict, ParseDict
from youtube_dl import YoutubeDL

from .protobuf.youtube_dl_tiny_grpc_pb2 import (ExtractInfoRequest,
                                                ExtractInfoResponse)
from .protobuf.youtube_dl_tiny_grpc_pb2_grpc import \
    YoutubeDLServicer as YoutubeDLServerBase
from .util import ProcessPoolExecutor

# Offload all youtube_dl processing to a separate process in this pool
# Idea from https://github.com/grpc/grpc/issues/16001
_YOUTUBE_DL_PROCESS_POOL: ProcessPoolExecutor = None
_YOUTUBE_DL_DEFAULT_OPTS = {}


def configure(default_opts: dict, process_pool: ProcessPoolExecutor) -> None:
    global _YOUTUBE_DL_DEFAULT_OPTS
    global _YOUTUBE_DL_PROCESS_POOL
    _YOUTUBE_DL_PROCESS_POOL = process_pool
    _YOUTUBE_DL_DEFAULT_OPTS = default_opts


def shutdown_pool() -> None:
    global _YOUTUBE_DL_PROCESS_POOL
    _YOUTUBE_DL_PROCESS_POOL.shutdown(False)


class YoutubeDLServer(YoutubeDLServerBase):
    """Provides methods that implement functionality of YoutubeDL server."""

    def _ExtractInfo(self, url: str, opts: dict) -> dict:
        ydl = YoutubeDL(opts)
        info = ydl.extract_info(url, False)
        return info

    async def ExtractInfo(
        self,
        request: ExtractInfoRequest,
        context: grpc.aio.ServicerContext
    ) -> ExtractInfoResponse:

        if request.url == "" or not isinstance(request.url, str):
            context.set_details("Invalid URL")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            yield ExtractInfoResponse()

        ydl_custom_opts = MessageToDict(
            request.options, including_default_value_fields=False, preserving_proto_field_name=True)
        ydl_opts = {**_YOUTUBE_DL_DEFAULT_OPTS, **ydl_custom_opts}
        ydl_opts['simulate'] = True

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(_YOUTUBE_DL_PROCESS_POOL, self._ExtractInfo, request.url, ydl_opts)

        # FIXME: Yes, this is a hack. youtube_dl sometimes returns tuples for some repeated fields and ParseDict doesn't like that.
        info = json.loads(json.dumps(info))
        try:
            entries = info['entries'][0]['entries']
            for entry in entries:
                yield ParseDict(entry, ExtractInfoResponse(), ignore_unknown_fields=True)
        except KeyError:
            try:
                entries = info['entries']
                for entry in entries:
                    yield ParseDict(entry, ExtractInfoResponse(), ignore_unknown_fields=True)
            except:
                yield ParseDict(info, ExtractInfoResponse(), ignore_unknown_fields=True)
