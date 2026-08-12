import gdstk
from shapely.geometry import Polygon
from shapely.strtree import STRtree
from collections import defaultdict

# 1. DICCIONARIO DE PINES DE SKYWATER 130nm
# Asocia el tipo de puerta con los nombres oficiales de sus pines
CELL_PIN_MAP = {
    'mux2_1': ['A0', 'A1', 'S', 'X'],
    'dfrtp_2': ['CLK', 'D', 'RESET_B', 'Q'],
    'nor2_2': ['A', 'B', 'Y'],
    'and2_2': ['A', 'B', 'X'],
    'or2_2': ['A', 'B', 'X'],
    'nand2_2': ['A', 'B', 'Y'],
    'xor2_2': ['A', 'B', 'X'],
    'xnor2_2': ['A', 'B', 'Y'],
    'clkbuf_16': ['A', 'X'],
    'and4bb_2': ['A_N', 'B_N', 'C', 'D', 'X'],
    'and3_2': ['A', 'B', 'C', 'X'],
    'a31o_2': ['A1', 'A2', 'A3', 'B1', 'X'],
    'a21o_2': ['A1', 'A2', 'B1', 'X'],
    'a21bo_2': ['A1', 'A2', 'B1_N', 'X'],
    'a21boi_2': ['A1', 'A2', 'B1_N', 'Y'],
    'o21bai_2': ['A1', 'A2', 'B1_N', 'Y']
}

ROUTING_LAYERS = [67, 68, 69, 70] # li1, met1, met2, met3
PHYSICAL_OVERHEAD = ('decap', 'tap', 'fill', 'diode', 'phy', 'VIA')

class UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))
    def find(self, i):
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]
    def union(self, i, j):
        root_i, root_j = self.find(i), self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j

def run_clean_extraction():
    print("==================================================")
    print(" EXTRACCIÓN PYTHON CORREGIDA (CON PINES REALES LEF)")
    print("==================================================\n")
    
    lib = gdstk.read_gds('04_final.gds')
    original_top = lib.top_level()[0]
    flat_top = original_top.copy('flat_top')
    flat_top.flatten()
    
    # Extraer polígonos de ruteo
    all_polygons = []
    poly_layer_map = []
    for poly in flat_top.polygons:
        if poly.layer in ROUTING_LAYERS:
            sp = Polygon(poly.points).buffer(0.001)
            all_polygons.append(sp)
            poly_layer_map.append(poly.layer)
            
    num_polys = len(all_polygons)
    uf = UnionFind(num_polys)
    spatial_tree = STRtree(all_polygons)
    
    # Agrupar polígonos solapados
    for i, p1 in enumerate(all_polygons):
        candidatos = spatial_tree.query(p1)
        for idx in candidatos:
            if i < idx and abs(poly_layer_map[i] - poly_layer_map[idx]) <= 1:
                if p1.intersects(all_polygons[idx]):
                    uf.union(i, idx)

    # Identificar puertos externos legítimos (A, B, clk, en, rst_n, S)
    VALID_PORTS = {'A', 'B', 'clk', 'en', 'rst_n', 'S'}
    label_to_net = {}
    for label in flat_top.labels:
        if label.text in VALID_PORTS:
            point = Polygon([(label.origin[0]-0.05, label.origin[1]-0.05),
                             (label.origin[0]+0.05, label.origin[1]+0.05)])
            candidatos = spatial_tree.query(point)
            for idx in candidatos:
                if point.intersects(all_polygons[idx]):
                    label_to_net[label.text] = f"net_{uf.find(idx)}"
                    break

    # Mapear celdas con nombres de pines correctos
    logic_instances = []
    for ref in original_top.references:
        cell_name = ref.cell.name if hasattr(ref.cell, 'name') else str(ref.cell)
        short_name = cell_name.replace('sky130_fd_sc_hd__', '')
        
        if any(short_name.startswith(p) for p in PHYSICAL_OVERHEAD):
            continue
            
        ox, oy = ref.origin
        
        # Obtener lista de pines esperados para esta celda
        expected_pins = CELL_PIN_MAP.get(short_name, [f"pin_{i}" for i in range(10)])
        
        pin_connections = {}
        found_nets = []
        
        # Detectar qué redes chocan con los contactos de la celda
        for p in ref.cell.polygons:
            if p.layer in (67, 68):
                shifted = [(pt[0] + ox, pt[1] + oy) for pt in p.points]
                pin_poly = Polygon(shifted).buffer(0.001)
                candidatos = spatial_tree.query(pin_poly)
                for idx in candidatos:
                    if pin_poly.intersects(all_polygons[idx]):
                        net_num = uf.find(idx)
                        net_name = f"net_{net_num}"
                        # Reemplazar por nombre de puerto externo si coincide
                        for lbl, n_id in label_to_net.items():
                            if n_id == net_name:
                                net_name = lbl
                        if net_name not in found_nets:
                            found_nets.append(net_name)
                        break
        
        # Asignar los nombres oficiales de los pines en orden
        for i, net in enumerate(found_nets):
            pin_name = expected_pins[i] if i < len(expected_pins) else f"pin_{i}"
            pin_connections[pin_name] = net
            
        logic_instances.append({
            'cell_type': cell_name,
            'inst_name': f"inst_{len(logic_instances)}",
            'connections': pin_connections
        })

    # Escribir el archivo Verilog limpio
    output_verilog = 'clean_extracted_netlist.v'
    with open(output_verilog, 'w') as f:
        f.write("// VERILOG EXTRAÍDO Y CORREGIDO CON PINES LEF REALES\n\n")
        f.write("module adder_demo (A, B, clk, en, rst_n, S);\n")
        f.write("  input A, B, clk, en, rst_n;\n")
        f.write("  output S;\n\n")
        
        # Declarar wires internos
        declared = {'A', 'B', 'clk', 'en', 'rst_n', 'S'}
        for inst in logic_instances:
            for net in inst['connections'].values():
                if net not in declared:
                    f.write(f"  wire {net};\n")
                    declared.add(net)
                    
        f.write("\n")
        for inst in logic_instances:
            f.write(f"  {inst['cell_type']} {inst['inst_name']} (\n")
            pairs = [f"    .{pin}({net})" for pin, net in inst['connections'].items()]
            f.write(",\n".join(pairs))
            f.write("\n  );\n\n")
        f.write("endmodule\n")
        
    print(f"[+] ¡ÉXITO! Verilog limpio generado en '{output_verilog}'.")

if __name__ == '__main__':
    run_clean_extraction()