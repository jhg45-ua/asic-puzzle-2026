import gdstk
from collections import Counter

# 1. Cargar el archivo GDSII
library = gdstk.read_gds('../puzzle.gds')
top_cell = library.top_level()[0]

print(f"==================================================")
print(f" PASO 1: ANALIZANDO LÓGICA DE LA CELDA: {top_cell.name}")
print(f"==================================================\n")

# Lista de prefijos/patrones de celdas físicas a ignorar
PHYSICAL_OVERHEAD = ('decap', 'tap', 'fill', 'diode', 'phy', 'VIA')

logic_cells = []
physical_cells_count = 0

# 2. Iterar sobre todas las referencias del layout
for ref in top_cell.references:
    cell_name = ref.cell.name if hasattr(ref.cell, 'name') else str(ref.cell)
    
    # Limpiar el nombre quitando el prefijo largo si existe
    short_name = cell_name.replace('sky130_fd_sc_hd__', '')
    
    # Comprobar si es una celda física de infraestructura
    if any(short_name.startswith(pattern) for pattern in PHYSICAL_OVERHEAD):
        physical_cells_count += 1
    else:
        logic_cells.append(short_name)

total_instancias = len(top_cell.references)
total_logicas = len(logic_cells)

print(f"RESUMEN DEL SILICIO:")
print(f" - Instancias totales en el GDSII: {total_instancias}")
print(f" - Celdas de infraestructura (filtradas): {physical_cells_count}")
print(f" - Puertas lógicas funcionales reales: {total_logicas}\n")

# 3. Contar y clasificar las puertas lógicas encontradas
counts = Counter(logic_cells)

print(f"DESGLOSE DE PUERTAS LÓGICAS FUNCIONALES:")
print(f"{'Tipo de Celda':<30} | {'Cantidad':<10} | {'Función Estimada'}")
print("-" * 65)

for cell, count in counts.most_common():
    # Clasificación rápida según el nombre de la celda
    if 'inv' in cell:
        func = "Inversor (NOT)"
    elif 'buf' in cell or 'clkbuf' in cell:
        func = "Buffer / Distribución de reloj"
    elif 'nand' in cell:
        func = "Puerta NAND"
    elif 'nor' in cell:
        func = "Puerta NOR"
    elif 'and' in cell:
        func = "Puerta AND"
    elif 'or' in cell:
        func = "Puerta OR"
    elif 'xor' in cell or 'xnor' in cell:
        func = "Puerta XOR / XNOR (Sumador)"
    elif 'dfxtp' in cell or 'dff' in cell:
        func = "Flip-Flop D (Registros)"
    elif 'mux' in cell:
        func = "Multiplexor"
    elif 'fa' in cell or 'ha' in cell:
        func = "Sumador completo / Medio sumador"
    else:
        func = "Lógica combinacional especial"
        
    print(f"{cell:<30} | {count:<10} | {func}")