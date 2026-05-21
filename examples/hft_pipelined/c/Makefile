PYTHON ?= python3
CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -fPIC
LDFLAGS ?= -shared
THIS_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(THIS_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

.PHONY: test_hft_pipelined clean

hft_udp_port_router.so: hft_udp_port_router.c hft_udp_port_router.h
	$(CC) $(CFLAGS) $(LDFLAGS) hft_udp_port_router.c -o $@

hft_mold_udp.so: hft_mold_udp.c hft_mold_udp.h
	$(CC) $(CFLAGS) $(LDFLAGS) hft_mold_udp.c -o $@

hft_itch_parser.so: hft_itch_parser.c hft_itch_parser.h
	$(CC) $(CFLAGS) $(LDFLAGS) hft_itch_parser.c -o $@

test_hft_pipelined: hft_udp_port_router.so hft_mold_udp.so hft_itch_parser.so
	$(PYTHON) -m pytest -q ctypes_tb_hft_pipelined.py $(PYTEST_ARGS)

clean:
	rm -f *.so
