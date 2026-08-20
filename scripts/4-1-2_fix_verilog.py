# fix_verilog.py
import re

with open("puzzle_extracted.v", "r") as f:
    code = f.read()

# 1. Reemplazar la cabecera del módulo por la definición estándar ANSI
header_pattern = re.compile(r"module puzzle\s*\(.*?\);.*?(?=\n\s*(?://|sky130|wire))", re.DOTALL)

standard_header = """module puzzle (
    input wire clk,
    input wire rst_n,
    input wire enable,
    input wire I,
    output wire [7:0] O,
    output wire success
);"""

code = header_pattern.sub(standard_header, code, count=1)

# 2. Asegurar que los cables escapados \O[x] se traten como índices de bus O[x]
code = re.sub(r"\\O\[(\d+)\]\s*", r"O[\1]", code)

# 3. Eliminar declaraciones redundantes de cables del bus O si existiesen
code = re.sub(r"^\s*wire\s+O\[\d+\];?\s*$", "", code, flags=re.MULTILINE)

with open("puzzle_extracted.v", "w") as f:
    f.write(code)

print("[+] puzzle_extracted.v normalizado a estándar ANSI Verilog.")