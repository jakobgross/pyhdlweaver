PYTHON ?= python3
CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -fPIC
LDFLAGS ?= -shared
THIS_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(THIS_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

.PHONY: test_udp_port_router test_udp_classifier clean

udp_port_router.so: udp_port_router.c udp_port_router.h
	$(CC) $(CFLAGS) $(LDFLAGS) udp_port_router.c -o $@

udp_classifier.so: udp_classifier.c udp_classifier.h
	$(CC) $(CFLAGS) $(LDFLAGS) udp_classifier.c -o $@

test_udp_port_router: udp_port_router.so
	$(PYTHON) -m pytest -q ctypes_tb_udp_port_router.py $(PYTEST_ARGS)

test_udp_classifier: udp_classifier.so
	$(PYTHON) -m pytest -q ctypes_tb_udp_classifier.py $(PYTEST_ARGS)

clean:
	rm -f *.so
