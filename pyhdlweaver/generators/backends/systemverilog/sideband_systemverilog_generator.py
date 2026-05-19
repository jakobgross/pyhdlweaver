from pyhdlweaver.generators.generated_file import GeneratedFile
from pyhdlweaver.generators.backends.systemverilog.field_extract_emitter import FieldExtractEmitter
from pyhdlweaver.generators.backends.systemverilog.systemverilog_generator import SystemVerilogGenerator
from pyhdlweaver.generators.backends.systemverilog.utils import counter_width, sv_int
from pyhdlweaver.protocols import Protocol, SidebandProtocol
from pyhdlweaver.stream.axi_stream import AxisStream


class SidebandSystemVerilogGenerator(SystemVerilogGenerator):
    def generate(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None = None,
    ) -> GeneratedFile:
        if not isinstance(protocol, SidebandProtocol):
            raise TypeError("SidebandSystemVerilogGenerator requires a SidebandProtocol")

        plan = self.build_plan(protocol, stream, module_name)
        field_emitter = FieldExtractEmitter(plan)
        body = self.renderer.render(
            "sideband_body.sv.j2",
            plan=plan,
            beat_count_width=counter_width(plan.parse_beats),
            field_declarations=field_emitter.emit_declarations(),
            comb_declarations=field_emitter.emit_comb_declarations(),
            comb_bypass_blocks=field_emitter.emit_comb_bypass_blocks(),
            field_reset_assignments=field_emitter.emit_reset_assignments(),
            field_capture_case_items=field_emitter.emit_capture_case_items(),
            default_tdest_literal=sv_int(4, plan.default_tdest),
        )

        content = self.render_module(plan, body)
        return GeneratedFile(name=f"{plan.module_name}.sv", content=content)
