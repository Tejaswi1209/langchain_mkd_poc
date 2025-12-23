from markitdown._base_converter import DocumentConverter, DocumentConverterResult
from markitdown._stream_info import StreamInfo
from typing import BinaryIO, Any
import re

class CodeParserConverter(DocumentConverter):
    """
    A converter that parses code files to extract function and class definitions.
    """

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> bool:
        # Accept only code files with specific extensions
        return stream_info.extension in [".py", ".js", ".java", ".cpp", ".c", ".ts"]

    def convert(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> DocumentConverterResult:
        try:
            # Read the code file content
            content = file_stream.read().decode("utf-8")

            # Extract functions and classes
            functions = self._extract_functions(content)
            classes = self._extract_classes(content)

            # Format the extracted information
            markdown = "# Code Structure\n\n"
            if classes:
                markdown += "## Classes\n\n" + "\n".join(classes) + "\n\n"
            if functions:
                markdown += "## Functions\n\n" + "\n".join(functions) + "\n\n"

            if not classes and not functions:
                markdown += "No classes or functions found in the code."

            return DocumentConverterResult(
                title=stream_info.filename or "Code File",
                markdown=markdown
            )
        except Exception as e:
            raise RuntimeError(f"Error during code parsing: {e}")

    def _extract_functions(self, content: str) -> list:
        # Regex to match function definitions (Python example)
        function_pattern = r"def\s+(\w+)\s*\(.*?\):"
        return [f"- {match}" for match in re.findall(function_pattern, content)]

    def _extract_classes(self, content: str) -> list:
        # Regex to match class definitions (Python example)
        class_pattern = r"class\s+(\w+)\s*(\(.*?\))?:"
        return [f"- {match[0]}" for match in re.findall(class_pattern, content)]