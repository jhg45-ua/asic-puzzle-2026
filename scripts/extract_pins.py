import gdstk

# 1. Cargar el layout del silicio
library = gdstk.read_gds('04_final.gds')
top_cell = library.top_level()[0]

print("==================================================")
print(" PASO 2: EXTRACCIÓN DE PINES (I/O) DEL SILICIO")
print("==================================================\n")

# En el formato GDSII, los nombres de los puertos se guardan como "labels" (textos)
labels = top_cell.labels

# Si la herramienta de diseño ocultó las etiquetas dentro de la jerarquía, aplanamos el chip
if len(labels) == 0:
    print("[*] No se encontraron pines en la raíz. Aplanando el layout...")
    top_cell = top_cell.copy("flat_top", flatten=True)
    labels = top_cell.labels

print(f"[+] Se han encontrado {len(labels)} pines de conexión en el chip:\n")

# 2. Imprimir la lista de pines, en qué capa están y sus coordenadas
print(f"{'Nombre del Pin':<15} | {'Capa GDS':<10} | {'Posición Física (X, Y)'}")
print("-" * 65)

for label in labels:
    texto = label.text
    capa = label.layer
    x, y = label.origin

    # Intentamos deducir si es alimentación, reloj o datos por el nombre
    tipo = "Datos/Control"
    if texto in ('VPWR', 'VDD', 'VGND', 'VSS'):
        tipo = "Alimentación"
    elif texto in ('clk', 'clock'):
        tipo = "Reloj (Síncrono)"

    print(f" {texto:<14} | {capa:<10} | ({x:.2f}, {y:.2f})  -> {tipo}")