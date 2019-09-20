Testing
=======

This guide will help you check that the codebase is working by building the project, running automated tests and finally running a manual QA end-to-end test.

## 1. Install

Full instructions in [`/doc/build-XXXX.md`](/doc/build-unix.md), the gist is:

```shell
./autogen.sh
./configure
make

# copy binaries from ./src to system:
sudo make install
```

## 2. Run unit tests

Full instructions in [`/src/test/README.md`](/src/test/README.md), the gist is: 

```shell
make check
```

## 3. Run integration tests

Full instructions in [`/test/README.md`](/test/README.md), the gist is:

```shell
test/functional/test_runner.py --extended
```

## 4. Manual QA end-to-end test

Full instructions in [`/manual/README.md`](/manual/README.md), the gist is:

```shell
cd manual
./1-cleanup-env.sh
./2-start-network.sh

# use the UI to manually create a transaction between them... and mine it:
./3-mine-one.sh

# use the UI to manually create a transaction back... and mine it:
./3-mine-one.sh

./4-stop-network.sh
```