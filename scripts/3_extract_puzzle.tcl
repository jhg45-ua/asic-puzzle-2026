# extract_puzzle.tcl

# Cargar el diseño físico GDSII y la celda superior en memoria
gds read ../puzzle.gds
load puzzle

# Definir y preparar la carpeta de salida para no ensuciar la raíz
set out_dir "extracted"
file mkdir $out_dir
cd $out_dir

# Extraer la conectividad física a archivos intermedios (.ext)
extract do local
extract all

# Configurar ext2spice en modo LVS (conserva celdas estándar y elimina parásitos)
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice format ngspice

# Generar el netlist SPICE final (se guardará dentro de ../extracted/)
ext2spice -o puzzle.spice
ext2spice

# Mensaje de estado y salida limpia
puts "============================================="
puts "Extraccion completada con exito."
puts "Archivos generados en: $out_dir/puzzle.spice"
puts "============================================="
quit -noprompt