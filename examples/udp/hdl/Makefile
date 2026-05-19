TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

VERILOG_SOURCES ?= $(HDL_DIR)/udp_port_router_8bit.sv
TOPLEVEL ?= udp_port_router_8bit
COCOTB_TEST_MODULES ?= cocotb_udp_port_router_8bit
SIM_BUILD ?= sim_build/$(TOPLEVEL)

COMPILE_ARGS += -g2012

.PHONY: test_udp_port_router_8 test_udp_classifier_64

test_udp_port_router_8:
	python3 $(REPO_ROOT)/examples/udp/generate_sv.py --udp-port-router-8bit --write
	$(MAKE) sim \
		TOPLEVEL=udp_port_router_8bit \
		VERILOG_SOURCES=$(HDL_DIR)/udp_port_router_8bit.sv \
		COCOTB_TEST_MODULES=cocotb_udp_port_router_8bit \
		SIM_BUILD=sim_build/udp_port_router_8bit

test_udp_classifier_64:
	python3 $(REPO_ROOT)/examples/udp/generate_sv.py --udp-classifier-64bit --write
	$(MAKE) sim \
		TOPLEVEL=udp_classifier_64bit \
		VERILOG_SOURCES=$(HDL_DIR)/udp_classifier_64bit.sv \
		COCOTB_TEST_MODULES=cocotb_udp_classifier_64bit \
		SIM_BUILD=sim_build/udp_classifier_64bit

include $(shell cocotb-config --makefiles)/Makefile.sim
