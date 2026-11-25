#!/bin/bash
# Semillas 4 y 5 en las 12 de 100 clientes para HMA-LD y HMA-RX (rx=2), luego HMA-RX rx=1 (semillas 1-3). Una corrida a la vez.
cd /home/user/oe3/base
R=/home/user/oe3/recarga
python3 bench.py --metodo hma_ld --conjunto conjuntos/desarrollo.txt --solo grandes --semillas 4 5 --out $R/resultados/hma_ld_s45 --reanudar \
  --cmd 'python3 metodos/hma.py --bin hma-ld/bin/evrp-tw-spd --beta {beta} --rho {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
python3 bench.py --metodo hma_rx2 --conjunto conjuntos/desarrollo.txt --solo grandes --semillas 4 5 --out $R/resultados/hma_rx2_s45 --reanudar \
  --cmd "python3 $R/metodos/hma_rx.py --bin $R/hma-rx/bin/evrp-tw-spd --rx 2 --beta {beta} --rho {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}"
python3 bench.py --metodo hma_rx1 --conjunto conjuntos/desarrollo.txt --solo grandes --semillas 1 2 3 --out $R/resultados/hma_rx1 --reanudar \
  --cmd "python3 $R/metodos/hma_rx.py --bin $R/hma-rx/bin/evrp-tw-spd --rx 1 --beta {beta} --rho {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}"
echo TODO_TERMINADO
