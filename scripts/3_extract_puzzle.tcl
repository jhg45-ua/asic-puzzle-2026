# extract_puzzle.tcl
gds read ../gds/puzzle.gds
load puzzle
extract do local
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice format ngspice
ext2spice
puts "============================================="
puts "[+] Extraccion completada: puzzle.spice generado con exito"
puts "============================================="
quit -noprompt