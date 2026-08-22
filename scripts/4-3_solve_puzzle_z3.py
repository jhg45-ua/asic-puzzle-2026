import re
import sys
from collections import defaultdict
from z3 import Solver, Bool, And, Or, Not, Xor, sat, is_true

def get_pin_val(pin_name, in_signals):
    val = in_signals[pin_name]
    # En Sky130, todo pin terminado en _N, _b o _B es activo a nivel bajo (negado)
    if pin_name.endswith("_N") or pin_name.endswith("_b") or pin_name.endswith("_B"):
        return Not(val)
    return val

def eval_sky130_cell(cell_type, in_signals):
    """Evaluador booleano universal para las 68 celdas de SkyWater 130nm HD"""
    # 1. Extraer nombre base limpio (ej: sky130_fd_sc_hd__xor2_2 -> xor2)
    clean_name = cell_type.replace("sky130_fd_sc_hd__", "")
    base = clean_name.split("_")[0]  # ej: "xor2", "a21boi", "nor3b", "mux2"

    # Inversores y Buffers
    if base == "inv":
        return Not(in_signals.get("A", False))
    if base in ("buf", "clkbuf"):
        return in_signals.get("A", False)

    # XOR y XNOR
    if base == "xor2":
        return Xor(get_pin_val("A", in_signals), get_pin_val("B", in_signals))
    if base == "xnor2":
        return Not(Xor(get_pin_val("A", in_signals), get_pin_val("B", in_signals)))

    # Multiplexores (MUX2)
    if base == "mux2":
        s = get_pin_val("S", in_signals)
        a0 = get_pin_val("A0", in_signals)
        a1 = get_pin_val("A1", in_signals)
        return Or(And(s, a1), And(Not(s), a0))

    # AND / NAND Simples
    if base.startswith("and"):
        vals = [get_pin_val(p, in_signals) for p in in_signals]
        return And(*vals) if len(vals) > 1 else vals[0]
    if base.startswith("nand"):
        vals = [get_pin_val(p, in_signals) for p in in_signals]
        res = And(*vals) if len(vals) > 1 else vals[0]
        return Not(res)

    # OR / NOR Simples
    if base.startswith("or"):
        vals = [get_pin_val(p, in_signals) for p in in_signals]
        return Or(*vals) if len(vals) > 1 else vals[0]
    if base.startswith("nor"):
        vals = [get_pin_val(p, in_signals) for p in in_signals]
        res = Or(*vals) if len(vals) > 1 else vals[0]
        return Not(res)

    # Celdas Compuestas AND-OR (a...o / a...oi / a...bo / a...boi)
    # Formato: Términos AND agrupados por letra (A, B, C, D) unidos por OR
    if base.startswith("a") and ("o" in base):
        groups = defaultdict(list)
        for p in in_signals:
            grp = p[0]  # Letra del grupo: 'A', 'B', 'C', 'D'
            groups[grp].append(get_pin_val(p, in_signals))
        and_terms = [And(*terms) if len(terms) > 1 else terms[0] for terms in groups.values()]
        res = Or(*and_terms) if len(and_terms) > 1 else and_terms[0]
        return Not(res) if "oi" in base else res

    # Celdas Compuestas OR-AND (o...a / o...ai / o...ba / o...bai / o2bb2a)
    # Formato: Términos OR agrupados por letra (A, B, C, D) unidos por AND
    if base.startswith("o") and ("a" in base):
        groups = defaultdict(list)
        for p in in_signals:
            grp = p[0]
            groups[grp].append(get_pin_val(p, in_signals))
        or_terms = [Or(*terms) if len(terms) > 1 else terms[0] for terms in groups.values()]
        res = And(*or_terms) if len(or_terms) > 1 else or_terms[0]
        return Not(res) if "ai" in base else res

    return False

def solve_puzzle():
    print("="*65)
    print("ASIC PUZZLE 2026: SOLUCIONADOR SMT / SAT CON Z3")
    print("="*65)

    with open("puzzle_extracted.v", "r") as f:
        content = f.read()

    inst_pattern = re.compile(r"(\w+)\s+(\w+)\s*\(\s*(.*?)\s*\);", re.DOTALL)
    
    comb_gates = {}
    dff_gates = {}
    
    for match in inst_pattern.finditer(content):
        cell_type, inst_name, ports_str = match.groups()
        if cell_type == "module":
            continue
        port_matches = re.findall(r"\.(\w+)\s*\(\s*([^)]+)\s*\)", ports_str)
        ports = {p: n.strip() for p, n in port_matches}
        
        if any(x in cell_type for x in ("dfrtp", "dfstp", "dfxtp")):
            dff_gates[inst_name] = {"type": cell_type, "ports": ports}
        elif "conb" in cell_type:
            comb_gates[inst_name] = {"type": cell_type, "ports": ports}
        elif not any(x in cell_type for x in ("decap", "fill", "tap", "diode")):
            comb_gates[inst_name] = {"type": cell_type, "ports": ports}

    print(f"[*] Red Lógica: {len(comb_gates)} compuertas combinacionales y {len(dff_gates)} Flip-Flops D.")

    solver = Solver()
    
    # Estado inicial tras Reset (t = 0)
    current_state = {}
    for dff, g in dff_gates.items():
        q_net = g["ports"].get("Q")
        if q_net:
            # dfstp inicializa a 1 (Set), dfrtp a 0 (Reset)
            current_state[q_net] = True if "dfstp" in g["type"] else False

    input_vars = []
    max_cycles = 150

    print(f"[*] Desenrollando simulación temporal simbólica (hasta {max_cycles} ciclos)...\n")

    for cycle in range(1, max_cycles + 1):
        # 1 bit de entrada serie simbólica por ciclo
        i_var = Bool(f"I_{cycle}")
        input_vars.append(i_var)
        
        env = dict(current_state)
        env["I"] = i_var
        env["enable"] = True
        env["rst_n"] = True
        env["success"] = current_state.get("success", False)

        # Inyectar constantes de celdas conb_1
        for inst, g in comb_gates.items():
            if "conb" in g["type"]:
                if "HI" in g["ports"]: env[g["ports"]["HI"]] = True
                if "LO" in g["ports"]: env[g["ports"]["LO"]] = False

        # Evaluación combinacional en capas hasta estabilizar todas las compuertas
        unresolved = set(comb_gates.keys())
        while True:
            progress = False
            for inst in list(unresolved):
                g = comb_gates[inst]
                out_pin = "X" if "X" in g["ports"] else ("Y" if "Y" in g["ports"] else None)
                if not out_pin:
                    unresolved.remove(inst)
                    continue
                out_net = g["ports"][out_pin]
                
                in_signals = {}
                ready = True
                for pin, net in g["ports"].items():
                    if pin != out_pin and pin not in ("VPWR", "VGND", "VPB", "VNB", "CLK"):
                        if net in env:
                            in_signals[pin] = env[net]
                        else:
                            ready = False
                            break
                if ready:
                    env[out_net] = eval_sky130_cell(g["type"], in_signals)
                    unresolved.remove(inst)
                    progress = True
            if not progress:
                break

        # Pin D del Flip-Flop de éxito (sky130_fd_sc_hd__dfrtp_2_81)
        success_d_net = "sky130_fd_sc_hd__a32o_2_4_X"
        success_expr = env.get(success_d_net, False)

        # Comprobar si Z3 puede satisfacer success == True en este ciclo
        solver.push()
        solver.add(success_expr == True)
        
        if solver.check() == sat:
            print("="*65)
            print(f"¡SOLUCIÓN SATISFECHA EN EL CICLO T = {cycle}! 🎉")
            print("="*65)
            
            model = solver.model()
            bits = [1 if is_true(model.eval(v)) else 0 for v in input_vars]
            bitstring = "".join(map(str, bits))
            
            print(f"\nSECUENCIA BINARIA ({len(bits)} bits):")
            print(f"   {bitstring}\n")
            
            hex_val = hex(int(bitstring, 2))
            print(f"VALOR HEXADECIMAL:")
            print(f"   {hex_val}\n")
            
            # Decodificar texto ASCII (MSB first / LSB first)
            ascii_chars = []
            for i in range(0, len(bits), 8):
                byte_slice = bits[i:i+8]
                if len(byte_slice) == 8:
                    b_val = int("".join(map(str, byte_slice)), 2)
                    ascii_chars.append(chr(b_val) if 32 <= b_val <= 126 else f"\\x{b_val:02x}")
            
            print(f"TEXTO / FLAG / CONTRASEÑA:")
            print(f"   {''.join(ascii_chars)}\n")
            return bits
            
        solver.pop()

        # Avanzar el estado de los Flip-Flops al ciclo t+1
        next_state = {}
        for dff, g in dff_gates.items():
            d_net = g["ports"].get("D")
            q_net = g["ports"].get("Q")
            if q_net and d_net:
                next_state[q_net] = env.get(d_net, False)
        current_state = next_state
        print(f"  [+] Ciclo {cycle:02d}/{max_cycles} evaluado...")

    print("\n[!] Límite de ciclos alcanzado.")

if __name__ == "__main__":
    solve_puzzle()