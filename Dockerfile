FROM python:3.9-slim

WORKDIR /app

ADD dist ./
RUN pip install *.tar.gz && rm -rf /app

EXPOSE 50051
ENTRYPOINT [ "python", "-m", "youtube_dl_tiny_grpc" ]
