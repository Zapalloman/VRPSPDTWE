#!/bin/bash
# Variante multiarranque (--llenar): HMA se reinicia hasta agotar los 120 s de CPU (solo 100 clientes).
cd /home/user/oe3/base
python3 bench.py --metodo hma_ld_llenar --conjunto conjuntos/desarrollo.txt --solo grandes --semillas 1 2 3 --reanudar \
  --cmd 'python3 metodos/hma.py --llenar --bin hma-ld/bin/evrp-tw-spd --beta {beta} --rho {rho} --beta-rep {beta} --rho-rep {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
