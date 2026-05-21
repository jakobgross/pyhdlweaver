from abc import ABC, abstractmethod

from pyhdlweaver.generators.generated_file import GeneratedFile, GeneratedFiles
from pyhdlweaver.protocols import Protocol
from pyhdlweaver.stream.axi_stream import AxisStream


class CodeGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None = None,
    ) -> GeneratedFile | GeneratedFiles:
        pass
