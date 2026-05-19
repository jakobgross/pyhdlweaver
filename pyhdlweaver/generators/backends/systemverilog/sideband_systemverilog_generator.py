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
        config_reg_declarations = [
            f"logic [{p.width - 1}:0] {p.name}_reg;"
            for p in plan.config_ports
        ]
        config_reg_reset_assignments = [
            f"{p.name}_reg <= {sv_int(p.width, p.default_value or 0)};"
            for p in plan.config_ports
        ]
        config_reg_update_assignments = [
            f"{p.name}_reg <= {p.name};"
            for p in plan.config_ports
        ]
        body = self.renderer.render(
            "sideband_body.sv.j2",
            plan=plan,
            beat_count_width=counter_width(plan.parse_beats),
            field_declarations=field_emitter.emit_declarations(),
            comb_declarations=field_emitter.emit_comb_declarations(),
            comb_bypass_blocks=field_emitter.emit_comb_bypass_blocks(),
            config_reg_declarations=config_reg_declarations,
            config_reg_reset_assignments=config_reg_reset_assignments,
            config_reg_update_assignments=config_reg_update_assignments,
            field_reset_assignments=field_emitter.emit_reset_assignments(),
            field_capture_case_items=field_emitter.emit_capture_case_items(),
            default_tdest_literal=sv_int(4, plan.default_tdest),
        )

        content = self.render_module(plan, body)
        return GeneratedFile(name=f"{plan.module_name}.sv", content=content)
