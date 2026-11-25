#!/bin/bash
# Re-corrida final de HMA-LD-afín (--afin 2, con margen TOL) y comparación a presupuesto igual.
cd /home/user/oe3/base
python3 bench.py --metodo hma_ld_afin_tol --conjunto conjuntos/desarrollo.txt --semillas 1 2 3 --reanudar \
  --out /home/user/oe3/afin/resultados/hma_ld_afin_tol \
  --cmd 'python3 /home/user/oe3/afin/metodos/hma_afin.py --bin /home/user/oe3/afin/hma-afin/bin/evrp-tw-spd --afin 2 --beta {beta} --rho {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla} --log {salida}.log'
python3 bench.py --metodo hma_ld_afin_llenar --conjunto conjuntos/desarrollo.txt --solo grandes --semillas 1 2 3 --reanudar \
  --out /home/user/oe3/afin/resultados/hma_ld_afin_llenar \
  --cmd 'python3 /home/user/oe3/afin/metodos/hma_afin_llenar.py --llenar --afin 2 --bin /home/user/oe3/afin/hma-afin/bin/evrp-tw-spd --beta {beta} --rho {rho} --beta-rep {beta} --rho-rep {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
