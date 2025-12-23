from markitdown._base_converter import DocumentConverter, DocumentConverterResult
import re
import pandas as pd
from io import StringIO
from openpyxl import Workbook

class MarkdownTableConverter(DocumentConverter):
    def accepts(self, file_stream, stream_info, **kwargs):
        # Accept only Markdown files
        return stream_info.extension == ".md"

    def convert(self, file_stream, stream_info, **kwargs):
        # Read the Markdown content
        content = file_stream.read().decode("utf-8")

        # Extract tables using a regex pattern
        tables = self._extract_tables(content)

        if not tables:
            return DocumentConverterResult(text_content="No tables found in the Markdown file.")

        # Convert tables to CSV format
        csv_output = self._convert_tables_to_csv(tables)

        return DocumentConverterResult(text_content=f"Extracted Tables:\n\n{csv_output}")

    def _extract_tables(self, content):
        # Regex to match Markdown tables
        table_pattern = r"(\|.+\|(?:\n\|[-:]+[-|:]*\|)+\n(?:\|.*\|(?:\n|$))*)"
        return re.findall(table_pattern, content)

    def _convert_tables_to_csv(self, tables):
        csv_output = []
        for table in tables:
            # Convert Markdown table to DataFrame
            df = pd.read_csv(StringIO(table), sep="|", engine="python", skipinitialspace=True)
            csv_output.append(df.to_csv(index=False))
        return "\n\n".join(csv_output)
    
    def _convert_tables_to_excel(self, tables, filename):
        # Create a new Excel workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Extracted Tables"

        # Parse each Markdown table and write to the Excel sheet
        row_offset = 1
        for table in tables:
            # Convert Markdown table to DataFrame
            df = pd.read_csv(StringIO(table), sep="|", engine="python", skipinitialspace=True)

            # Write DataFrame to Excel sheet
            for r_idx, row in enumerate(df.itertuples(index=False), start=row_offset):
                for c_idx, value in enumerate(row, start=1):
                    sheet.cell(row=r_idx, column=c_idx, value=value)

            # Add an empty row between tables
            row_offset += len(df) + 2

        # Save the Excel file
        excel_file_path = f"{filename}_tables.xlsx"
        workbook.save(excel_file_path)
        return excel_file_path
 