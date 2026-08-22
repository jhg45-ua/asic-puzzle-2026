`timescale 1ns / 1ps

module tb_puzzle;

    reg clk;
    reg rst_n;
    reg enable;
    reg I;
    wire [7:0] O;
    wire success;

    // Clave de 122 bits resuelta por Z3
    reg [121:0] key_stream = 122'b00000001010100001000000000000101010100000000000010100000010000010000001000001010000100000001000000100000100100010100000000;

    // Instancia del ASIC
    puzzle dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .I(I),
        .O(O),
        .success(success)
    );

    // Reloj (100 MHz)
    always #5 clk = ~clk;

    integer cycle_idx;
    integer post_cycle;
    reg [8*64-1:0] final_string; // Buffer para acumular el mensaje
    integer str_idx;

    initial begin
        $dumpfile("puzzle_simulation.vcd");
        $dumpvars(0, tb_puzzle);

        clk = 0;
        rst_n = 0;
        enable = 0;
        I = 0;
        str_idx = 0;

        #25;
        rst_n = 1;
        enable = 1;
        $display("==================================================");
        $display("[+] Reset completado. Inyectando clave de 122 bits...");
        $display("==================================================");

        // 1. Inyección de la clave hasta activar success
        for (cycle_idx = 1; cycle_idx <= 122; cycle_idx = cycle_idx + 1) begin
            @(negedge clk);
            I = key_stream[122 - cycle_idx];

            @(posedge clk);
            #1;
            if (success == 1'b1) begin
                $display("\n¡SUCCESS = 1 DETECTADO EN EL CICLO %0d!", cycle_idx);
                $write("%c", O);
            end
        end

        // 2. Continuar ejecutando ciclos para leer el flujo completo del 'output generator'
        $display("\n==================================================");
        $display("[*] Leyendo flujo de salida del Output Generator...");
        $display("==================================================");
        $write("MENSAJE / FLAG: ");

        // Imprimir el primer carácter del ciclo 122 si es imprimible
        if (O >= 32 && O <= 126) $write("%c", O);

        for (post_cycle = 1; post_cycle <= 64; post_cycle = post_cycle + 1) begin
            @(negedge clk);
            I = 0; // Mantener entrada a 0 tras la clave

            @(posedge clk);
            #1;
            if (O >= 32 && O <= 126) begin
                $write("%c", O);
            end
        end

        $display("\n==================================================");
        $display("[+] Extracción completada.");
        $display("==================================================");
        $finish;
    end

endmodule