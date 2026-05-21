PYTHON ?= python3
CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -fPIC
LDFLAGS ?= -shared
THIS_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(THIS_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

.PHONY: test_eth_ip_forward_udp clean

eth_ip_forward_udp.so: eth_ip_forward_udp.c eth_ip_forward_udp.h
	$(CC) $(CFLAGS) $(LDFLAGS) eth_ip_forward_udp.c -o $@

test_eth_ip_forward_udp: eth_ip_forward_udp.so
	$(PYTHON) -m pytest -q ctypes_tb_eth_ip_forward_udp.py $(PYTEST_ARGS)

clean:
	rm -f *.so
