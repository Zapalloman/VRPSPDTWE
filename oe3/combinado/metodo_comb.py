#!/usr/bin/env python3
"""HMA-LD-afín + pool de rutas + set partitioning (+ movimientos conscientes de la carga). Derivado de pool/metodo_pool.py.

Uso (plantilla para bench.py):
  python3 /home/user/oe3/pool/metodo_pool.py --instancia {instancia} --salida {salida} \
      --tiempo {tiempo} --semilla {semilla} --beta {beta} --rho {rho} [--frac 0.2] [--polish]

Presupuesto total T (el mismo que recibe HMA-LD sola):
  1. HMA-LD-pool (copia de HMA-LD que vuelca cada ruta distinta de las soluciones que
     produce: tras CDNS, tras cada destroy-repair y cada hijo del cruce) corre
     (1 - frac)·T segundos de CPU;
  2. sp_solve.py resuelve el set partitioning sobre el pool (y, con --polish, alterna
     vecindarios + ruin&recreate + SP) durante el tiempo de pared restante hasta T
     medido desde el inicio, con un mínimo de 3 s.
  3. Se entrega la mejor solución factible (juez) entre la de HMA-LD y la del SP.
"""
import argparse, os, sys, time, subprocess, tempfile, glob, shutil
sys.path.insert(0, '/home/user/oe3/common'); sys.path.insert(0, '/home/user/oe3/base/metodos')
sys.path.insert(0, '/home/user/oe3/pool')
from evrp import read_instance, read_solution, check_solution
from hma import PEQ, MED, escribir_solucion

BIN = '/home/user/oe3/combinado/hma-comb/bin/evrp-comb'


def main():
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--instancia', required=True); ap.add_argument('--salida', required=True)
    ap.add_argument('--tiempo', type=float, required=True); ap.add_argument('--semilla', type=int, default=1)
    ap.add_argument('--beta', type=float, default=0.2); ap.add_argument('--rho', type=float, default=0.0)
    ap.add_argument('--frac', type=float, default=0.2)
    ap.add_argument('--polish', action='store_true')
    ap.add_argument('--min-restart', type=float, default=25.0, help='s mínimos de CPU restantes para relanzar HMA')
    ap.add_argument('--extra', default='--afin 2', help='opciones extra para el binario (afin, elim, reord, pool_afin)')
    ap.add_argument('--keep', help='carpeta donde guardar pool y registros')
    ap.add_argument('--v2', action='store_true', help='SP periódico dentro de HMA con re-inyección')
    ap.add_argument('--every', type=float, default=20.0)
    ap.add_argument('--tl', type=float, default=4.0)
    ap.add_argument('--restart', action='store_true', help='si HMA termina antes, relanzar con otra semilla (mismo pool)')
    ap.add_argument('--t-final', type=float, default=None, help='segundos reservados al SP final')
    a = ap.parse_args()
    nombre = os.path.basename(a.instancia).rsplit('.', 1)[0]
    params = MED if nombre.endswith('_21') else PEQ
    tmp = tempfile.mkdtemp(prefix='pool_')
    try:
        t_final = a.t_final if a.t_final is not None else a.frac * a.tiempo
        pool = os.path.join(tmp, 'pool.txt')
        I = read_instance(a.instancia)
        cands = []
        k = 0
        binp = BIN
        while True:
            t_hma = int(a.tiempo - t_final - (time.time() - t0))
            if t_hma < (a.min_restart if k else 1):
                break
            cmd = [binp, '--problem', a.instancia, '--time', str(t_hma), '--runs', '1',
                   '--random_seed', str(a.semilla + 1000 * k)] + params.split() + ['--output', tmp + f'/r{k}_',
                   '--beta', repr(a.beta), '--rho', repr(a.rho), '--pool_file', pool] + a.extra.split()
            if a.v2:
                cmd += ['--pool_every', str(a.every), '--pool_tl', str(a.tl), '--pool_dir', tmp]
            with open(os.path.join(tmp, 'hma.log'), 'a') as lg:
                subprocess.call(cmd, stdout=lg, stderr=subprocess.STDOUT)
            fs = glob.glob(os.path.join(tmp, f'r{k}_' + nombre + '_timelimit=*'))
            if fs:
                R, tot = read_solution(fs[0])
                rh = [[x[0] for x in r] for r in R]
                j = check_solution(I, [[(i, None, None) for i in r] for r in rh], None, a.beta, a.rho, use_reported=False)
                if j['ok']:
                    cands.append((j['cost'], f'hma{k}', rh))
            k += 1
            if not a.restart:
                break
        if cands:
            cands.sort(key=lambda x: x[0])
            with open(os.path.join(tmp, 'inc.txt'), 'w') as fh:  # incumbente para el SP
                for r in cands[0][2]:
                    fh.write(' '.join(map(str, r)) + '\n')
        t_sp = max(3.0, a.tiempo - (time.time() - t0) - 1.0)
        out = os.path.join(tmp, 'sp.txt')
        cmd = [sys.executable, '/home/user/oe3/pool/sp_solve.py', a.instancia, pool, out, str(t_sp),
               '--seed', str(a.semilla), '--inc', os.path.join(tmp, 'inc.txt')] + (['--polish'] if a.polish else [])
        with open(os.path.join(tmp, 'sp.log'), 'w') as lg:
            try:
                subprocess.call(cmd, stdout=lg, stderr=subprocess.STDOUT, timeout=t_sp + 3)
            except subprocess.TimeoutExpired:
                pass
        if os.path.exists(out):
            rs = [[int(x) for x in l.split()] for l in open(out) if not l.startswith('#') and l.strip()]
            j = check_solution(I, [[(i, None, None) for i in r] for r in rs], None, a.beta, a.rho, use_reported=False)
            if j['ok']:
                cands.append((j['cost'], 'sp', rs))
        if not cands:
            sys.exit(1)
        cands.sort(key=lambda x: x[0])
        escribir_solucion(a.salida, I, cands[0][2])
        info = {c[1]: round(c[0], 2) for c in cands}
        print(f'pool: {info} elegido={cands[0][1]} t={time.time()-t0:.1f}', file=sys.stderr)
        if a.keep:
            os.makedirs(a.keep, exist_ok=True)
            for f in ('hma.log', 'sp.log', 'sp_calls.log'):
                if os.path.exists(os.path.join(tmp, f)):
                    shutil.copy(os.path.join(tmp, f), os.path.join(a.keep, f'{nombre}_s{a.semilla}_{f}'))
            with open(os.path.join(a.keep, 'resumen.txt'), 'a') as fh:
                fh.write(f'{nombre} s{a.semilla} {info} elegido={cands[0][1]} lineas_pool={sum(1 for _ in open(pool))} t={time.time()-t0:.1f}\n')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
