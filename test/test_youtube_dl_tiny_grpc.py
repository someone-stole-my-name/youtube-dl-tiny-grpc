#!/usr/bin/env python3
from google.protobuf.json_format import ParseDict, MessageToDict
import grpc
import os
import asyncio
import sys
import logging
import socket
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from youtube_dl_tiny_grpc import (Server)
from youtube_dl_tiny_grpc.protobuf import youtube_dl_tiny_grpc_pb2_grpc
from youtube_dl_tiny_grpc.protobuf import youtube_dl_tiny_grpc_pb2

TEST_MATRIX = [
    {
        "meta": "Youtube Channel ID",
        "message": ParseDict(
            message=youtube_dl_tiny_grpc_pb2.ExtractInfoRequest(),
            js_dict={
                "url":     "https://www.youtube.com/channel/UCZJbZ-0Dxdj5ETtJqcJQO2g",
                "options": {"playlistend": 2}
            }),
        "expected_responses": 2
    },
    {
        "meta": "Youtube Playlist ID",
        "message": ParseDict(
            message=youtube_dl_tiny_grpc_pb2.ExtractInfoRequest(),
            js_dict={
                "url":     "https://www.youtube.com/playlist?list=PLbpi6ZahtOH7WFEYxB4kUB2QwsshALAwy",
                "options": {"playlistend": 2}
            }),
        "expected_responses": 2
    },
    {
        "meta": "Youtube Channel Short",
        "message": ParseDict(
            message=youtube_dl_tiny_grpc_pb2.ExtractInfoRequest(),
            js_dict={
                "url":     "https://www.youtube.com/c/unboxtherapy",
                "options": {"playlistend": 2}
            }),
        "expected_responses": 2
    },
]


async def run_tests(port: int) -> None:
    async with grpc.aio.insecure_channel(f"localhost:{port}") as channel:
        stub = youtube_dl_tiny_grpc_pb2_grpc.YoutubeDLStub(channel)
        for test_case in TEST_MATRIX:
            response_count = 0

            async for response in stub.ExtractInfo(test_case['message']):
                response_count = response_count + 1
                response_dict = MessageToDict(response)
                assert len(response_dict['requestedFormats']) > 0
                for format in response_dict['requestedFormats']:
                    assert len(format['url']) > 0

            try:
                assert response_count == test_case["expected_responses"]
            except AssertionError:
                print(
                    f"{test_case['meta']} failed: {response_count} != {test_case['expected_responses']}")
                raise


def run():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        loop = asyncio.get_event_loop()
        server = Server({"grpc_port": s.getsockname()[1]})
        server_task = loop.create_task(server.run())
        loop.run_until_complete(run_tests(s.getsockname()[1]))
        server_task.cancel()
        loop.stop()


if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    run()
