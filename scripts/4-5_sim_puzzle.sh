# 1. Compilar con la macro funcional activa
iverilog -g2012 -DFUNCTIONAL \
  -o sim_puzzle \
  tb_puzzle.v \
  puzzle_extracted.v \
  $PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v \
  $PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v

# 2. Ejecutar la simulación
vvp sim_puzzle