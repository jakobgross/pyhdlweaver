PYTHON ?= python3
CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -fPIC
LDFLAGS ?= -shared
THIS_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(THIS_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

.PHONY: test_mold_udp clean

mold_udp.so: mold_udp.c mold_udp.h
	$(CC) $(CFLAGS) $(LDFLAGS) mold_udp.c -o $@

test_mold_udp: mold_udp.so
	$(PYTHON) -m pytest -q ctypes_tb_mold_udp.py $(PYTEST_ARGS)

clean:
	rm -f *.so
