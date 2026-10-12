FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ make cmake ninja-build meson autoconf automake libtool \
    pkg-config git ca-certificates python3 binutils curl unzip \
    libssl-dev zlib1g-dev libboost-all-dev libcurl4-openssl-dev libprotobuf-dev \
    protobuf-compiler libgtest-dev libeigen3-dev libfmt-dev libspdlog-dev \
    libbz2-dev liblzma-dev libreadline-dev libsqlite3-dev libpng-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
