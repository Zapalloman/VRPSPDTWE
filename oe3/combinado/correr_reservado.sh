#!/bin/bash
# Prueba final en el conjunto reservado (nunca usado para ajustar). Reanudable (--reanudar).
cd /home/user/oe3/combinado
REF_LL='python3 metodos/hma.py --llenar --bin hma-ld/bin/evrp-tw-spd --beta {beta} --rho {rho} --beta-rep {beta} --rho-rep {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
REF_LD='python3 metodos/hma.py --bin hma-ld/bin/evrp-tw-spd --beta {beta} --rho {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
FINAL=$(cat cmd_final.txt)
for S in 1 2; do
  ./correr.sh res_hma_ld_llenar "$REF_LL" reservado grandes "$S"
  ./correr.sh res_final "$FINAL" reservado grandes "$S"
done
./correr.sh res_hma_ld_peq "$REF_LD" reservado pequenas "1"
./correr.sh res_final_peq "$FINAL" reservado pequenas "1"
echo FIN
