# AIxCC Nginx CHERI demo

This repository is a fork of the released AIxCC Nginx Challenge Project source with
*cherification* patches to support compilation and execution with CHERI. Currently,
this code is tested to work for CheriBSD running on Arm Morello.

This repository contains two scripts to demonstrate the Challege Project Vulnerabilities (CPV)
under CHERI. The [test.py](./test.py) script is used to demonstrate the CPVs individually: it
starts Nginx with the given configuration file and sends the given trigger request. The other
script, [demo/demo.py](demo/demo.py), is used to demonstrate all the CPVs and collect the
results in a table printed to the command line at the end. 

## CheriBSD Morello Build Instructions

This code was tested on the latest official CheriBSD Release (25.03)
available here: https://www.cheribsd.org

### Pre-requisites

* Once CheriBSD is installed, make sure the following packages are installed:

```sh
pkg64 install llvm-base-20240315
pkg64 install llvm-morello-15.0.d20250318
pkg64 install git
pkg64c install sudo
pkg64 install python3-3_3
```

* If you are going to use any of the demo scripts (test.py or demo.py), install Python 3:

```sh
pkg64 install python3-3_3
```

* If you are going to use the demo.py script, also install these packages:

```sh
pkg64 install py39-tabulate-0.8.9
```

### Running all the CPV trigger tests using demo.py

To run the demo.py script, you don't need to follow the instructions at [Building locally (required to run test.py too)](#building-locally-required-to-run-testpy-too) and at [Individually running the CPV trigger tests](#individually-running-the-cpv-trigger-tests).

The [demo folder](./demo/) has a [build.sh](./demo/build.sh) script, which builds for the
hybrid and the purecap ABI and installs them in `$PWD/install_aarch64` and 
`$PWD/install_aarch64c`. It must be run inside `./demo`!

```sh
cd demo/
./build.sh
```

Then, just run `python3 demo.py`. Coredumps will be found at `/tmp/cores`.

### Building locally (required to run test.py too)

For development purposes (because you never want to use this code for production),
point the hardcoded paths to user readable and writable paths (eg. `/tmp/nginx`),
so that we don't need to use `sudo` to start Nginx processes. Set the `--prefix`
to `$PWD/install_nginx` to install to `$PWD/install_nginx` instead of `/usr/local/nginx`.

```sh
./configure --with-cc-opt='-Wno-cheri-provenance' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail --with-http_v2_module  --error-log-path=/tmp/nginx/error.log --http-log-path=/tmp/nginx/access.log --pid-path=/tmp/nginx/nginx.pid --prefix=$PWD/install_nginx
make -j4
make install
```

To build with subobject bounds, add `-Xclang -cheri-bounds=subobject-safe`, for example:

```sh
./configure --with-cc-opt='-Wno-cheri-provenance -Xclang -cheri-bounds=subobject-safe' --without-http_geo_module --with-http_ssl_module --with-pcre --with-compat --with-mail --with-http_v2_module  --error-log-path=/tmp/nginx/error.log --http-log-path=/tmp/nginx/access.log --pid-path=/tmp/nginx/nginx.pid --prefix=$PWD/install_nginx
make -j4
make install
```

The `nginx` binary will be found at `$PWD/install_nginx/sbin/nginx`. 

### Individually running the CPV trigger tests

Assuming the hardcoded paths were changed to `/tmp/nginx` as illustrated above, 
we need to create the `/tmp/nginx` directory. In addition, because the configurations
provided in this repository explicitly points `/tmp/cores` as the location to dump
coredumps, we also need to make sure `/tmp/cores` exists.

```sh
mkdir /tmp/nginx
mkdir /tmp/cores
```

Then we can test each trigger by running the following command:
```sh
python3 test.py <cp_folder> <request.txt>
```

For example, 
```sh
python3 test.py cp1 request.txt
```

Coredumps will be found at `/tmp/cores`.

## Coredumps in CheriBSD

To generate coredumps in CheriBSD, you may want to set these configurations:

```sh
sudo sysctl kern.sugid_coredump=1 # if you used sudo because you installed to /usr/local
sudo sysctl kern.corefile=%N.%P.core # to avoid overwriting coredumps
ulimit -c unlimited
```

Check `/tmp/cores/nginx.*` for coredumps (or the current directory,
if the Nginx configuration file didn't specify the exact coredump location).

## Difference between AIxCC Linux and FreeBSD/CheriBSD

Some Challege Project Vulnerabilities (CPV) were added to features that have platform-dependent implementations. For such CPVs, we need to port the features to FreeBSD/CheriBSD as faithfully as possible so that no new vulnerabilities are added in the porting process. Some features also require patches to be compatible with BSD systems. These are the main differences:

* In AIxCC Nginx, the host specs feature implementation reads from /proc which is not mounted by default in FreeBSD. Then, fclose(NULL) causes SEGFAULT in FreeBSD while it does not in recent Linux. I patched it so that the process doesn't crash and the default "Unknown" host specifications are shown. I'm not going to fix the functionality of the host specs feature because that's irrelevant to the analysis of the UAF vulnerability.

* The connection history feature is implemented by recording the connections in ngx_epoll_process_events, but FreeBSD uses ngx_kqueue_module instead of ngx_epoll_module. I ported the connection history feature to ngx_kqueue_module and I hope I didn't add new vulnerabilities.

* The feature of sending a range of data from a resource with the option to reverse the data stream is implemented in ngx_linux_sendfile_chain.c, which is specific to Linux as the name suggests. **I haven't ported this feature to FreeBSD.** I risk introducing new bugs if I naively add the reverse sendfile feature to FreeBSD. This means that CPV12 cannot be reproduced in FreeBSD/CheriBSD.

## CHERI+ASan Build

AIxCC Nginx can be built and run with CHERI+ASan. However, the reproducibility is low currently, as CHERI+ASan support is not yet upstreamed (not included in the released llvm-morello toolchain).
