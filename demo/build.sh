#!/bin/sh

mkdir -p /tmp/nginx_aarch64
mkdir -p /tmp/nginx_aarch64c
mkdir -p /tmp/cores

cd ../
# aarch64c
./configure --with-cc-opt='-Wno-cheri-provenance -Xclang -cheri-bounds=subobject-safe -O3 -ggdb' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail --with-http_v2_module --error-log-path=/tmp/nginx_aarch64c/error.log --http-log-path=/tmp/nginx_aarch64c/access.log --pid-path=/tmp/nginx_aarch64c/nginx.pid
make -j4
rm -rf objs_aarch64c
mv objs objs_aarch64c

# aarch64
./configure --with-cc='/usr/local64/bin/clang' --with-cc-opt='-mabi=aapcs -Wno-cheri-provenance -O3 -ggdb' --with-ld-opt='-mabi=aapcs' --without-http_geo_module --with-http_ssl_module --with-compat --with-mail --with-http_v2_module --error-log-path=/tmp/nginx_aarch64/error.log --http-log-path=/tmp/nginx_aarch64/access.log --pid-path=/tmp/nginx_aarch64/nginx.pid
make -j4
rm -rf objs_aarch64
mv objs objs_aarch64

cd demo/