To build in Morello (by default without subobject bounds):

./configure --with-cc-opt='-Wno-cheri-provenance' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail
make -j4

To build with subobject bounds, add `-Xclang -cheri-bounds=subobject-safe`:

./configure --with-cc-opt='-Wno-cheri-provenance -Xclang -cheri-bounds=subobject-safe' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail --with-http_v2_module
make -j4

To test:

sudo make install
sudo python3 test.py <cp_folder>

and check /tmp/cores/nginx.* for coredumps.
