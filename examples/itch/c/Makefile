PYTHON ?= python3
CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -fPIC
LDFLAGS ?= -shared
THIS_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(THIS_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

.PHONY: test_itch_parser clean

itch_parser.so: itch_parser.c itch_parser.h
	$(CC) $(CFLAGS) $(LDFLAGS) itch_parser.c -o $@

test_itch_parser: itch_parser.so
	$(PYTHON) -m pytest -q ctypes_tb_itch_parser.py $(PYTEST_ARGS)

clean:
	rm -f *.so
