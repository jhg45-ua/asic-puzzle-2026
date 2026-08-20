import re
from collections import defaultdict

def debug_netlist(verilog_file):
    print("="*60)
    print("🔍 DIAGNÓSTICO DEL NETLIST Y CONO DE 'SUCCESS'")
    print("="*60)
    
    with open(verilog_file, "r") as f:
        content = f.read()

    inst_pattern = re.compile(r"(\w+)\s+(\w+)\s*\(\s*(.*?)\s*\);", re.DOTALL)
    
    gates = {}
    net_driver = {}
    cell_types = defaultdict(int)
    
    for match in inst_pattern.finditer(content):
        cell_type, inst_name, ports_str = match.groups()
        port_matches = re.findall(r"\.(\w+)\s*\(\s*([^)]+)\s*\)", ports_str)
        ports = {p: n.strip() for p, n in port_matches}
        
        cell_types[cell_type] += 1
        gates[inst_name] = {"type": cell_type, "ports": ports}
        
        for pin in ("X", "Y", "Q"):
            if pin in ports:
                net_driver[ports[pin]] = (inst_name, cell_type, ports)

    print(f"\n[+] Tipos de celdas encontradas en el Verilog ({len(cell_types)} tipos distintos):")
    for ct, count in sorted(cell_types.items(), key=lambda x: -x[1]):
        print(f"    - {ct}: {count}")

    # 1. Rastrear el cono hacia atrás desde la entrada D del Flip-Flop de success
    success_dff = "sky130_fd_sc_hd__dfrtp_2_81"
    if success_dff in gates:
        d_net = gates[success_dff]["ports"].get("D")
        print(f"\n[+] Flip-Flop de success: {success_dff}")
        print(f"[+] Red de entrada D: {d_net}")
        
        # Cono hacia atrás (primeros 4 niveles)
        print("\n[+] Cono lógico inmediato que calcula 'success':")
        visited = set()
        def print_cone(net, depth=0):
            if depth > 4 or net in visited or net not in net_driver:
                return
            visited.add(net)
            inst, ctype, ports = net_driver[net]
            indent = "  " * depth
            in_pins = [f"{p}={n}" for p, n in ports.items() if p not in ("X", "Y", "Q", "VPWR", "VGND", "VPB", "VNB", "CLK")]
            print(f"{indent}└── [{ctype}] {inst} -> out({net}) <= inputs({', '.join(in_pins)})")
            for p, n in ports.items():
                if p not in ("X", "Y", "Q", "VPWR", "VGND", "VPB", "VNB", "CLK"):
                    print_cone(n, depth + 1)

        print_cone(d_net)
    else:
        print(f"[!] No se encontró {success_dff} en el netlist.")

    # 2. Identificar Flip-Flops que actúan como contador / FSM
    print("\n" + "="*60)
    print("⏱️ DETECCIÓN DE CONTADORES / FSM")
    print("="*60)
    dff_count = sum(1 for g in gates.values() if any(x in g["type"] for x in ("dfrtp", "dfstp", "dfxtp")))
    print(f"[+] Total Flip-Flops: {dff_count}")

if __name__ == "__main__":
    debug_netlist("puzzle_extracted.v")