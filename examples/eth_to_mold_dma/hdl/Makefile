TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

VERILOG_SOURCES ?= $(HDL_DIR)/eth_to_mold_dma_64bit.sv
TOPLEVEL ?= eth_to_mold_dma_64bit
COCOTB_TEST_MODULES ?= cocotb_eth_to_mold_dma_64bit
SIM_BUILD ?= sim_build/$(TOPLEVEL)

COMPILE_ARGS += -g2012

.PHONY: test_64bit

test_64bit:
	python3 $(REPO_ROOT)/examples/eth_to_mold_dma/generate_sv.py --write
	$(MAKE) sim \
		TOPLEVEL=eth_to_mold_dma_64bit \
		VERILOG_SOURCES=$(HDL_DIR)/eth_to_mold_dma_64bit.sv \
		COCOTB_TEST_MODULES=cocotb_eth_to_mold_dma_64bit \
		SIM_BUILD=sim_build/eth_to_mold_dma_64bit

include $(shell cocotb-config --makefiles)/Makefile.sim
