#!/bin/sh

mkdir -p /tmp/nginx
mkdir -p /tmp/cores

cd ../
./configure --with-cc-opt='-Wno-cheri-provenance -Xclang -cheri-bounds=subobject-safe -O3 -ggdb' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail --with-http_v2_module --error-log-path=/tmp/nginx/error.log --http-log-path=/tmp/nginx/access.log --pid-path=/tmp/nginx/nginx.pid
make -j4
cd demo/