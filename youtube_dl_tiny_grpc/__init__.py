#!/usr/bin/env python3
# coding: utf-8
from setproctitle import setproctitle
import logging
import asyncio

from .options import (
    parse_opts,
)

from .youtube_dl_tiny_grpc import (Server)

_PROGNAME = 'youtube-dl-tiny-grpc'

def main(argv=None):
    setproctitle(_PROGNAME)
    logging.basicConfig()
    args = parse_opts(argv)
    loop = asyncio.get_event_loop()
    server = Server(args.__dict__)
    try:
        loop.run_until_complete(server.run())
    except:
        pass
    finally:
        loop.run_until_complete(*server.cleanup)
        loop.stop()

__all__ = ['main']
