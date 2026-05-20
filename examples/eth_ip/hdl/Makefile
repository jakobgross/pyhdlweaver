TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

VERILOG_SOURCES ?= $(HDL_DIR)/eth_ip_parser.sv
TOPLEVEL ?= eth_ip_parser
COCOTB_TEST_MODULES ?= cocotb_eth_ip_parser
SIM_BUILD ?= sim_build/$(TOPLEVEL)

COMPILE_ARGS += -g2012

.PHONY: test_eth_ip_32 test_eth_ip_24 test_eth_ip_udp_8 test_eth_ip_udp_512 test_eth_ip_route_broadcast_udp_32

test_eth_ip_32:
	python3 $(REPO_ROOT)/examples/eth_ip/generate_sv.py --write
	$(MAKE) sim \
		TOPLEVEL=eth_ip_parser \
		VERILOG_SOURCES=$(HDL_DIR)/eth_ip_parser.sv \
		COCOTB_TEST_MODULES=cocotb_eth_ip_parser \
		SIM_BUILD=sim_build/eth_ip_parser

test_eth_ip_24:
	python3 $(REPO_ROOT)/examples/eth_ip/generate_sv.py --parser-24bit --write
	$(MAKE) sim \
		TOPLEVEL=eth_ip_parser_24bit \
		VERILOG_SOURCES=$(HDL_DIR)/eth_ip_parser_24bit.sv \
		COCOTB_TEST_MODULES=cocotb_eth_ip_parser_24bit \
		SIM_BUILD=sim_build/eth_ip_parser_24bit

test_eth_ip_udp_8:
	python3 $(REPO_ROOT)/examples/eth_ip/generate_sv.py --forward-udp-8bit --write
	$(MAKE) sim \
		TOPLEVEL=eth_ip_forward_udp_8bit \
		VERILOG_SOURCES=$(HDL_DIR)/eth_ip_forward_udp_8bit.sv \
		COCOTB_TEST_MODULES=cocotb_eth_ip_forward_udp_8bit \
		SIM_BUILD=sim_build/eth_ip_forward_udp_8bit

test_eth_ip_udp_512:
	python3 $(REPO_ROOT)/examples/eth_ip/generate_sv.py --forward-udp-512bit --write
	$(MAKE) sim \
		TOPLEVEL=eth_ip_forward_udp_512bit \
		VERILOG_SOURCES=$(HDL_DIR)/eth_ip_forward_udp_512bit.sv \
		COCOTB_TEST_MODULES=cocotb_eth_ip_forward_udp_512bit \
		SIM_BUILD=sim_build/eth_ip_forward_udp_512bit

test_eth_ip_route_broadcast_udp_32:
	python3 $(REPO_ROOT)/examples/eth_ip/generate_sv.py --route-broadcast-udp-32bit --write
	$(MAKE) sim \
		TOPLEVEL=eth_ip_route_broadcast_udp_32bit \
		VERILOG_SOURCES=$(HDL_DIR)/eth_ip_route_broadcast_udp_32bit.sv \
		COCOTB_TEST_MODULES=cocotb_eth_ip_route_broadcast_udp_32bit \
		SIM_BUILD=sim_build/eth_ip_route_broadcast_udp_32bit

include $(shell cocotb-config --makefiles)/Makefile.sim
