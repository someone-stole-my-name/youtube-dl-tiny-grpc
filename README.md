# youtube-dl-tiny-grpc

A tiny slice of `youtube-dl` exposed over gRPC

# Examples

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
