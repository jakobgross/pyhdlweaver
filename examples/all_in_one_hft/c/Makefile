PYTHON ?= python3
CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -fPIC
LDFLAGS ?= -shared
THIS_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(THIS_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

.PHONY: test_all_in_one_hft clean

all_in_one_hft.so: all_in_one_hft.c all_in_one_hft.h
	$(CC) $(CFLAGS) $(LDFLAGS) all_in_one_hft.c -o $@

test_all_in_one_hft: all_in_one_hft.so
	$(PYTHON) -m pytest -q ctypes_tb_all_in_one_hft.py $(PYTEST_ARGS)

clean:
	rm -f *.so
