from pyhdlweaver.generators.generated_file import GeneratedFile
from pyhdlweaver.generators.backends.systemverilog.systemverilog_generator import SystemVerilogGenerator
from pyhdlweaver.protocols import Protocol
from pyhdlweaver.stream.axi_stream import AxisStream


class FixedSystemVerilogGenerator(SystemVerilogGenerator):
    def generate(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None = None,
    ) -> GeneratedFile:
        raise NotImplementedError("FixedProtocol SystemVerilog generation is not implemented yet")
