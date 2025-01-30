To build in Morello:

./configure --with-cc-opt='-Wno-cheri-provenance' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail --with-http_v2_module
make -j4

To test:

sudo make install
sudo python3 test.py <cp_folder> <request.txt>

To generate coredumps in CheriBSD:
sudo sysctl kern.sugid_coredump=1
sudo sysctl kern.corefile=%N.%P.core
ulimit -c unlimited

and check /tmp/cores/nginx.* for coredumps (or the current directory, if the Nginx conf file didn't specify the exact coredump location).

To use perl unit tests:
perl -I/path/to/challenge-004-nginx-cp/src/nginx-unit-tests/lib test.t
