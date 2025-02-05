Morello Build Instructions

This code was tested on the latest official CheriBSD Release (24.05)
available here: https://www.cheribsd.org

* Once CheriBSD is installed Make sure the following packages are installed:

pkg64 install llvm-base-20240315
pkg64 install llvm-morello-14.0.d20240325_1
pkg64 install git
pkg64c install sudo

* Build the nginx server locally

./configure --with-cc-opt='-Wno-cheri-provenance' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail --with-http_v2_module
make -j4

To build with subobject bounds, add `-Xclang -cheri-bounds=subobject-safe`:

./configure --with-cc-opt='-Wno-cheri-provenance -Xclang -cheri-bounds=subobject-safe' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail --with-http_v2_module
make -j4

* Run the CPV trigger tests 

sudo make install
sudo mkdir /tmp/cores
sudo python3 test.py <cp_folder> <request.txt>

For example, 
sudo python3 test.py cp1 request.txt

To generate coredumps in CheriBSD, you need to set up your box like this:

sudo sysctl kern.sugid_coredump=1
sudo sysctl kern.corefile=%N.%P.core
ulimit -c unlimited

Check /tmp/cores/nginx.* for coredumps (or the current directory, if the Nginx conf file didn't specify the exact coredump location).

* Run perl unit tests (Optional)

For example,
perl -I/path/to/challenge-004-nginx-cp/src/nginx-unit-tests/lib test.t
