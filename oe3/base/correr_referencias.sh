#!/bin/bash
# Corre las dos referencias en el conjunto de desarrollo, 3 semillas, una corrida a la vez.
# (a) HMA-LD (beta=0.2, rho=0)   (b) HMA original + reparación mínima posterior (common/consumo_carga.py)
cd /home/user/oe3/base
python3 bench.py --metodo hma_ld --conjunto conjuntos/desarrollo.txt --semillas 1 2 3 --reanudar \
  --cmd 'python3 metodos/hma.py --bin hma-ld/bin/evrp-tw-spd --beta {beta} --rho {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
python3 bench.py --metodo hma_orig_reparado --conjunto conjuntos/desarrollo.txt --semillas 1 2 3 --reanudar \
  --cmd 'python3 metodos/hma.py --bin hma-ld/bin/evrp-tw-spd-orig --reparar --beta-rep {beta} --rho-rep {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
python3 tabla_referencias.py
