# youtube-dl-tiny-grpc

A tiny slice of `youtube-dl` exposed over gRPC

## Install

To install it locally you can use `pip`, type:

```
pip install --upgrade youtube-dl-tiny-grpc
```

Alternatively, you can use the provided container:

```
docker pull ghcr.io/someone-stole-my-name/youtube-dl-tiny-grpc:latest
```

## Description

`youtube-dl-tiny-grpc` is a tiny gRPC server that exposes the `extract_info` method of `youtube-dl` over the wire, ready to be consumer by other processes with no startup time and caching support.

## Options

All options can be set from environment variables using its name in uppercase and replacing hyphens with underscores.

```
youtube-dl-tiny-grpc [-h] [--grpc-port GRPC_PORT]
                            [--grpc-graceful-shutdown-timeout GRPC_GRACEFUL_SHUTDOWN_TIMEOUT]
                            [--grpc-no-reflection]
                            [--grpc-compression-algorithm {none,deflate,gzip}]
                            [--youtube-dl-max-workers YOUTUBE_DL_MAX_WORKERS]
                            [--youtube-dl-verbose] [--youtube-dl-no-quiet]
                            [--version] [--verbose]
```

### gRPC
```
  --grpc-port GRPC_PORT
                        Port to listen on (default: 50051)
  --grpc-graceful-shutdown-timeout GRPC_GRACEFUL_SHUTDOWN_TIMEOUT
                        Graceful shutdown timeout (default: 60)
  --grpc-no-reflection  Disable gRPC server reflection (default: False)
  --grpc-compression-algorithm {none,deflate,gzip}
                        Compression algorithm for the server (default: gzip)
```
### `youtube-dl`

```
  --youtube-dl-max-workers YOUTUBE_DL_MAX_WORKERS
                        Max number of workers to use for youtube-dl (default: 8)
  --youtube-dl-verbose  Verbose output for youtube-dl (default: False)
  --youtube-dl-no-quiet
                        Disable quiet output for youtube-dl (default: True)
```

## Examples

Some examples using `grpcurl`, see the proto spec for a list of fields in the response:

```
grpcurl -d '
    {
        "url":"https://www.youtube.com/watch?v=AavpOiGnSx0",
        "options": {
            "format": "bestaudio[ext=m4a]"
        }
    }' \
    --plaintext \
    localhost:50051 YoutubeDL/ExtractInfo | jq -r '.url'

https://...
```

```
grpcurl -d '
    {
        "url":"https://www.youtube.com/channel/UCNAxrHudMfdzNi6NxruKPLw",
        "options": {
            "format": "bestaudio[ext=m4a]",
            "playlistend": 2
        }
    }' \
    --plaintext \
    localhost:50051 YoutubeDL/ExtractInfo | jq -r '.url'

https://...
https://...
```

```
grpcurl -d '
    {
        "url":"https://www.youtube.com/channel/UCNAxrHudMfdzNi6NxruKPLw",
        "options": {
            "playlistend": 5
        }
    }' --plaintext localhost:50051 YoutubeDL/ExtractInfo |\
    jq '.| "\(.upload_date) \(.view_count)"' -r |\
    gnuplot -p -e '
        set xlabel "Date";
        set ylabel "Views";
        set xdata time;
        set timefmt "%Y%m%d";
        set terminal dumb size 75,20;
        plot "-" using 1:2 notitle'

     350000 +----------------------------------------------------------+   
            |           +           +          +           +           |   
     300000 |-+    A                                                 +-|   
            |                                                          |   
     250000 |-+                                                      +-|   
            |                                                          |   
     200000 |-+                                                      +-|   
            |                                                          |   
Views       |                                                          |   
     150000 |-+                                                      +-|   
            |                                             A            |   
     100000 |-+            A                                         +-|   
            |                                                          |   
      50000 |-+                                                      +-|   
            |           +           +          +      A    +           |   
          0 +----------------------------------------------------------+   
          02/03       02/10       02/17      02/24       03/03       03/10 
                                       Date                                
```

```
ghz --insecure --async -e -d '{}' localhost:50051
ghz --insecure --concurrency=5 -e -d '
    {
        "url":"https://www.youtube.com/channel/UCNAxrHudMfdzNi6NxruKPLw",
        "options": {
            "playlistend": 5
        }
    }' localhost:50051 --call=YoutubeDL/ExtractInfo
```
