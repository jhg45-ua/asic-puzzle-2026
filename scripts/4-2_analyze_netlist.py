import re
from collections import defaultdict

def analyze_verilog(verilog_file):
    print(f"[*] Analizando {verilog_file}...\n")
    
    with open(verilog_file, "r") as f:
        content = f.read()

    # Expresión regular para parsear instancias de celdas y sus puertos
    # formato: sky130_fd_sc_hd__<cell> <inst> ( .pin(net), ... );
    inst_pattern = re.compile(r"(\w+)\s+(\w+)\s*\(\s*(.*?)\s*\);", re.DOTALL)
    
    gates = {}
    net_drivers = {}         # net -> (gate_name, output_pin)
    net_consumers = defaultdict(list) # net -> [(gate_name, input_pin)]
    dff_list = []
    
    for match in inst_pattern.finditer(content):
        cell_type, inst_name, ports_str = match.groups()
        
        # Parsear pines individuales .PIN(NET)
        port_matches = re.findall(r"\.(\w+)\s*\(\s*([^)]+)\s*\)", ports_str)
        ports = {p: n.strip() for p, n in port_matches}
        
        gates[inst_name] = {
            "type": cell_type,
            "ports": ports
        }
        
        # Identificar flip-flops
        if "dfrtp" in cell_type or "dfstp" in cell_type or "dfxtp" in cell_type:
            dff_list.append(inst_name)
        
        # Registrar drivers (salidas X, Y, Q) y consumidores
        for pin, net in ports.items():
            if pin in ("X", "Y", "Q"):
                net_drivers[net] = (inst_name, pin)
            elif pin not in ("VPWR", "VGND", "VPB", "VNB", "CLK"):
                net_consumers[net].append((inst_name, pin))

    print(f"[+] Total de compuertas identificadas: {len(gates)}")
    print(f"[+] Total de Flip-Flops encontrados: {len(dff_list)}")

    # 1. RASTREAR LA CADENA DEL SHIFT REGISTER (desde pin 'I')
    print("\n" + "="*50)
    print("📍 1. RASTREO DEL REGISTRO DE DESPLAZAMIENTO (Entrada I)")
    print("="*50)
    
    current_net = "I"
    shift_chain = []
    visited_gates = set()
    
    for step in range(128):
        consumers = net_consumers.get(current_net, [])
        next_dff = None
        next_net = None
        
        for g_name, p_name in consumers:
            g_info = gates[g_name]
            g_type = g_info["type"]
            
            # Si conecta a un MUX de enable o directamente a un DFF
            if "mux2" in g_type and g_name not in visited_gates:
                visited_gates.add(g_name)
                mux_out = g_info["ports"].get("X")
                # El out del mux debe ir a un DFF
                for mux_consumer, _ in net_consumers.get(mux_out, []):
                    if mux_consumer in dff_list:
                        next_dff = mux_consumer
                        next_net = gates[mux_consumer]["ports"].get("Q")
                        break
            elif g_name in dff_list and g_name not in visited_gates:
                visited_gates.add(g_name)
                next_dff = g_name
                next_net = g_info["ports"].get("Q")
                break
                
        if next_dff:
            shift_chain.append((next_dff, gates[next_dff]["type"], current_net, next_net))
            current_net = next_net
        else:
            break

    print(f"[+] Se ha detectado una cadena de desplazamiento de {len(shift_chain)} etapas/bits:")
    for idx, (dff_name, cell_t, in_n, out_n) in enumerate(shift_chain[:10]):
        print(f"    Bit {idx:02d}: {dff_name} ({cell_t}) | In: {in_n} -> Out: {out_n}")
    if len(shift_chain) > 10:
        print(f"    ... [{len(shift_chain) - 10} etapas intermedias omitidas] ...")
        last_idx = len(shift_chain) - 1
        dff_name, cell_t, in_n, out_n = shift_chain[-1]
        print(f"    Bit {last_idx:02d}: {dff_name} ({cell_t}) | In: {in_n} -> Out: {out_n}")

    # 2. RASTREAR EL CONO LÓGICO DE LA SALIDA 'success'
    print("\n" + "="*50)
    print("🎯 2. CONO DE LÓGICA DE LA SALIDA 'success'")
    print("="*50)
    
    success_driver = net_drivers.get("success")
    if success_driver:
        print(f"[+] Driver directo de 'success': Compuerta {success_driver[0]} ({gates[success_driver[0]]['type']})")
    else:
        print("[!] No se encontró driver directo para el pin 'success'.")

if __name__ == "__main__":
    analyze_verilog("puzzle_extracted.v")