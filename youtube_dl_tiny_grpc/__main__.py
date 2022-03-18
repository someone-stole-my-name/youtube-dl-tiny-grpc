#!/usr/bin/env python3
# $ python -m youtube_dl_tiny_grpc

import sys

if __package__ is None and not hasattr(sys, 'frozen'):
    # direct call of __main__.py
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

# pylint: disable=wrong-import-position
import youtube_dl_tiny_grpc

if __name__ == '__main__':
    youtube_dl_tiny_grpc.main()
