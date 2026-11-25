#!/bin/bash
# Uso: correr.sh METODO "CMD" CONJUNTO(desarrollo|reservado) SOLO(grandes|pequenas) "SEMILLAS" [NPAR=3]
# Reparte las instancias en NPAR procesos bench.py (cada uno de un solo hilo) con carpetas
# de salida separadas (resultados/METODO/parteK) y --reanudar; luego unir.py junta los CSV.
M=$1; CMD=$2; CONJ=$3; SOLO=$4; SEM=$5; NPAR=${6:-3}
cd /home/user/oe3/base
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
INST=$(python3 -c "
import sys; sys.path.insert(0,'.')
L=[l.strip() for l in open('conjuntos/$CONJ.txt') if l.strip()]
g=[x for x in L if x.endswith('_21')] if '$SOLO'=='grandes' else [x for x in L if not x.endswith('_21')]
print(' '.join(g))")
arr=($INST)
for k in $(seq 0 $((NPAR-1))); do
  sub=""
  for ((i=k; i<${#arr[@]}; i+=NPAR)); do sub="$sub ${arr[$i]}"; done
  OUT=/home/user/oe3/combinado/resultados/$M/parte$k
  mkdir -p $OUT
  nohup python3 bench.py --metodo $M --instancias $sub --semillas $SEM --reanudar --out $OUT --cmd "$CMD" > $OUT/bench.log 2>&1 &
done
wait
python3 /home/user/oe3/combinado/unir.py /home/user/oe3/combinado/resultados/$M
