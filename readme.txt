To build in Morello:

./configure --with-cc-opt='-Wno-cheri-provenance' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail
make -j4

To test:

sudo make install
sudo python3 test.py <cp_folder>

and check /tmp/cores/nginx.* for coredumps.
