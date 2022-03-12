FROM python:3.9-slim

WORKDIR /app

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt
ADD src/* ./

EXPOSE 50051
ENTRYPOINT [ "/app/youtube_dl_tiny_grpc.py", "--port", "50051" ]
