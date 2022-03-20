#!/usr/bin/env python3
# coding: utf-8

from setproctitle import setproctitle
import logging
import asyncio
import errno
import os

from .util import port_is_in_use

from .options import (
    parse_opts,
)

from .youtube_dl_tiny_grpc import (Server)

_PROGNAME = 'youtube-dl-tiny-grpc'
_LOG_FORMAT = '%(levelname)s - %(asctime)s - %(name)s - %(process)d - %(' \
              'message)s'


def main(argv=None):
    setproctitle(_PROGNAME)
    args = parse_opts(argv)

    if args.__dict__['debug']:
        logging.basicConfig(level='DEBUG', format=_LOG_FORMAT)
    elif args.__dict__['verbose']:
        logging.basicConfig(level='INFO', format=_LOG_FORMAT)
    else:
        logging.basicConfig()

    loop = asyncio.get_event_loop()

    if port_is_in_use(args.grpc_port):
        raise Exception(os.strerror(errno.EADDRINUSE))

    server = Server(args.__dict__)
    try:
        loop.run_until_complete(server.run())
    except:  # noqa: E722
        pass
    finally:
        loop.run_until_complete(*server.cleanup)
        loop.stop()


__all__ = ['main']
