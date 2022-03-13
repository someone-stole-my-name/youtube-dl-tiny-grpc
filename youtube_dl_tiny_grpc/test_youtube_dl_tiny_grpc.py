#!/usr/bin/env python3

import grpc
import youtube_dl_tiny_grpc_pb2
import youtube_dl_tiny_grpc_pb2_grpc
import sys

from google.protobuf.json_format import ParseDict

TEST_MATRIX = [
    {
        "meta": "Youtube Channel ID",
        "message": ParseDict(
            {"url":"https://www.youtube.com/channel/UCZJbZ-0Dxdj5ETtJqcJQO2g", "options":{ "playlistend": 5 }},
            youtube_dl_tiny_grpc_pb2.ExtractInfoRequest()),
        "expected_responses": 5
    },
    {
        "meta": "Youtube Channel Short",
        "message": ParseDict(
            {"url":"https://www.youtube.com/c/unboxtherapy", "options":{ "playlistend": 5 }},
            youtube_dl_tiny_grpc_pb2.ExtractInfoRequest()),
        "expected_responses": 5
    },
    {
        "meta": "Youtube Playlist ID",
        "message": ParseDict(
            {"url":"https://www.youtube.com/playlist?list=PLbpi6ZahtOH7WFEYxB4kUB2QwsshALAwy", "options":{ "playlistend": 5 }},
            youtube_dl_tiny_grpc_pb2.ExtractInfoRequest()),
        "expected_responses": 5
    },
]

def send_message(stub: youtube_dl_tiny_grpc_pb2_grpc.YoutubeDLStub):
    for test_case in TEST_MATRIX:
        responses = stub.ExtractInfo(test_case["message"])
        try:
            assert len(list(responses)) == test_case["expected_responses"]
        except AssertionError:
            print(f"{test_case['meta']} failed: {len(list(responses))} != {test_case['expected_responses']}")
            raise

def run():
    with grpc.insecure_channel(f"{sys.argv[1]}:50051") as channel:
        stub = youtube_dl_tiny_grpc_pb2_grpc.YoutubeDLStub(channel)
        send_message(stub)

if __name__ == '__main__':
    run()
