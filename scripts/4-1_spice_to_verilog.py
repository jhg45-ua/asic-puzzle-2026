import re
import sys

def convert_spice_to_verilog(spice_filename, output_verilog, top_cell="puzzle"):
    print(f"[*] Leyendo {spice_filename}...")
    with open(spice_filename, "r") as f:
        content = f.read()

    # 1. Mapear la signatura de puertos de cada subcircuito de la librería
    subckt_pattern = re.compile(r"^\.subckt\s+(\S+)\s+(.*?)$", re.MULTILINE)
    cell_ports = {}
    for match in subckt_pattern.finditer(content):
        name = match.group(1)
        ports = match.group(2).split()
        cell_ports[name] = ports

    # 2. Localizar el bloque de la celda Top-Level
    top_pattern = re.compile(
        rf"^\.subckt\s+{top_cell}\s+(.*?)\n(.*?)\n\.ends",
        re.MULTILINE | re.DOTALL
    )
    match_top = top_pattern.search(content)
    if not match_top:
        print(f"[!] Error: No se encontró el subcircuito '.subckt {top_cell}' en el archivo SPICE.")
        return

    top_ports = match_top.group(1).split()
    top_body = match_top.group(2)

    # Filtrar señales de alimentación de los puertos principales
    power_nets = {"VPWR", "VGND", "VPB", "VNB", "vccd1", "vssd1"}
    io_ports = [p for p in top_ports if p not in power_nets]

    print(f"[+] Top cell '{top_cell}' encontrada.")
    print(f"[+] Puertos I/O detectados ({len(io_ports)}): {', '.join(io_ports)}")

    # 3. Parsear las instancias del Top-Level
    # Unir líneas partidas con '+'
    flattened_lines = []
    current_line = ""
    for line in top_body.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+"):
            current_line += " " + line[1:].strip()
        else:
            if current_line:
                flattened_lines.append(current_line)
            current_line = line
    if current_line:
        flattened_lines.append(current_line)

    verilog_lines = [
        f"// Netlist estructural extraído de {spice_filename}",
        f"`timescale 1ns / 1ps\n",
        f"module {top_cell} (",
        f"    " + ", ".join(io_ports),
        f");\n"
    ]

    # Declarar puertos
    for p in io_ports:
        if p == "clk":
            verilog_lines.append(f"    input clk;")
        elif p in ("rst_n", "enable", "I"):
            verilog_lines.append(f"    input {p};")
        elif p == "success":
            verilog_lines.append(f"    output success;")
        elif p.startswith("O[") or p == "O":
            # Formato bus
            pass

    # Detectar bus O si está dividido o completo
    has_bus_o = any(p.startswith("O[") for p in io_ports)
    if has_bus_o:
        verilog_lines.append("    output [7:0] O;")

    verilog_lines.append("\n    // Instancias de Celdas Estándar")

    functional_count = 0
    internal_nets = set()

    for line in flattened_lines:
        if not line.startswith("X"):
            continue

        tokens = line.split()
        inst_name = tokens[0][1:]  # Quitar 'X' inicial
        cell_type = tokens[-1]
        connected_nets = tokens[1:-1]

        # Ignorar celdas de desacoplo y relleno
        if any(cell_type.startswith(p) for p in ("sky130_fd_sc_hd__decap", "sky130_fd_sc_hd__fill", "sky130_fd_sc_hd__tap")):
            continue

        formal_ports = cell_ports.get(cell_type, [])
        port_mappings = []

        for i, net in enumerate(connected_nets):
            if i < len(formal_ports):
                pin = formal_ports[i]
                if pin not in power_nets and not pin.endswith("#"):
                    # Sanitizar nombres de red
                    clean_net = net.replace("/", "_").replace("$", "_")
                    port_mappings.append(f".{pin}({clean_net})")
                    if clean_net not in io_ports and not clean_net.startswith("O["):
                        internal_nets.add(clean_net)

        if port_mappings:
            verilog_lines.append(f"    {cell_type} {inst_name} ( {', '.join(port_mappings)} );")
            functional_count += 1

    # Insertar cables internos
    wires_declaration = [f"    wire {net};" for net in sorted(internal_nets)]
    verilog_lines.insert(len(verilog_lines) - functional_count - 1, "\n    // Cables y Nodos Internos\n" + "\n".join(wires_declaration) + "\n")

    verilog_lines.append("\nendmodule\n")

    with open(output_verilog, "w") as f:
        f.write("\n".join(verilog_lines))

    print(f"[+] Proceso completado: {functional_count} puertas lógicas convertidas a Verilog.")
    print(f"[+] Archivo guardado en: {output_verilog}")

if __name__ == "__main__":
    convert_spice_to_verilog("extracted/puzzle.spice", "puzzle_extracted.v", top_cell="puzzle")