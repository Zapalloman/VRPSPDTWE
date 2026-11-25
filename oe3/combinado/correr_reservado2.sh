#!/bin/bash
# Reanudación tras el reinicio del contenedor: solo lo que falta (--reanudar salta lo existente).
cd /home/user/oe3/combinado
REF_LD='python3 metodos/hma.py --bin hma-ld/bin/evrp-tw-spd --beta {beta} --rho {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
FINAL=$(cat cmd_final.txt)
./correr.sh res_final "$FINAL" reservado grandes "2"
./correr.sh res_hma_ld_peq "$REF_LD" reservado pequenas "1"
./correr.sh res_final_peq "$FINAL" reservado pequenas "1"
echo FIN
