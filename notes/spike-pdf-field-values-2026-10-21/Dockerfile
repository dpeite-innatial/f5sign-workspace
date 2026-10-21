FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils qpdf && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "pyhanko[image-support]==0.29.0" requests==2.32.3 cryptography
WORKDIR /w
