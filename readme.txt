Morello Build Instructions
==========================

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


Difference between AIxCC Linux and FreeBSD/CheriBSD
===================================================

Some Challege Project Vulnerabilities (CPV) were added to features that have platform-dependent implementations. For such CPVs, we need to port the features to FreeBSD/CheriBSD as faithfully as possible so that no new vulnerabilities are added in the porting process. Some features also require patches to be compatible with BSD systems. These are the main differences:

* In AIxCC Nginx, the host specs feature implementation reads from /proc which is not mounted by default in FreeBSD. Then, fclose(NULL) causes SEGFAULT in FreeBSD while it does not in recent Linux. I patched it so that the process doesn't crash and the default "Unknown" host specifications are shown. I'm not going to fix the functionality of the host specs feature because that's irrelevant to the analysis of the UAF vulnerability. 

* The connection history feature is implemented by recording the connections in ngx_epoll_process_events, but FreeBSD uses ngx_kqueue_module instead of ngx_epoll_module. I ported the connection history feature to ngx_kqueue_module and I hope I didn't add new vulnerabilities.

* The feature of sending a range of data from a resource with the option to reverse the data stream is implemented in ngx_linux_sendfile_chain.c, which is specific to Linux as the name suggests. **I haven't ported this feature to FreeBSD.** I risk introducing new bugs if I naively add the reverse sendfile feature to FreeBSD. This means that CPV12 cannot be reproduced in FreeBSD/CheriBSD. 


CHERI+ASan Build
================

AIxCC Nginx can be built and run with CHERI+ASan. However, the reproducibility is low currently, as CHERI+ASan support is not yet upstreamed.
