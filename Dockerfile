FROM python:3.9-slim

WORKDIR /app

ADD * ./
RUN pip install -e . && rm -rf /app

EXPOSE 50051
ENTRYPOINT [ "python", "-m", "youtube_dl_tiny_grpc", "--port", "50051" ]
