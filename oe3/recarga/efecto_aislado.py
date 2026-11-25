"""Paso 2: efecto aislado del subproblema de recarga exacto sobre las soluciones publicadas de HMA (akb).

Para cada ruta publicada: se quitan sus estaciones y se re-deciden con frvcp (misma
secuencia de clientes; opcionalmente también la secuencia invertida). Se compara con
(i) la solución publicada tal cual y (ii) la reparación mínima de common/consumo_carga.py.
Toda solución se valida con el juez oficial check_solution(beta, rho=0, use_reported=False).
"""
import glob, os, sys, json, time
from frvcp import *
from evrp import check_solution
sys.argv = [sys.argv[0], '/home/user/oe3/common/hma'] + sys.argv[1:]
import consumo_carga as cc
H = '/home/user/oe3/common/hma'
beta = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
out = sys.argv[3] if len(sys.argv) > 3 else f'efecto_aislado_b{beta}.json'
files = sorted(glob.glob(H + '/solution/akb/*.txt'))
files.sort(key=lambda f: '_21' in f)
res = {}
for f in files:
    base = os.path.basename(f).split('_timelimit')[0]
    I = read_instance(H + '/data/akb_instances/' + base + '.txt')
    R, T = read_solution(f)
    t0 = time.time()
    orig, rep, dp, dprev = [], [], [], []
    for r in R:
        nodes = [x[0] for x in r]
        orig.append(nodes)
        if eval_route(I, nodes, beta)['feasible']:
            rep.append(nodes)
        else:
            rp = cc.repair(I, nodes, beta, 0.0)
            rep.append(rp[1] if rp else None)
        cust = [0] + [i for i in nodes[1:-1] if I.typ[i] == 'c'] + [0]
        a = frvcp(I, cust, beta, maxper=2)
        dp.append(a[1] if a else None)
        b = frvcp(I, cust[::-1], beta, maxper=2)
        cand = [x for x in (a, b) if x]
        dprev.append(min(cand)[1] if cand else None)
    rec = {'n': len(I.customers), 'K': len(R), 'cost_pub': T}
    for tag, sol in (('pub', orig), ('rep', rep), ('dp', dp), ('dprev', dprev)):
        if any(x is None for x in sol):
            rec[tag] = {'ok': False, 'rutas_inf': sum(x is None for x in sol)}
            # rutas resueltas: calcula costo parcial para diagnóstico
            continue
        c = check_solution(I, [[(i, None, None) for i in x] for x in sol], None, beta, 0.0, use_reported=False)
        rec[tag] = {'ok': c['ok'], 'cost': c['cost'], 'dist': c['dist'], 'K': c['K'],
                    'rutas_inf': sum(not o['feasible'] for o in c['routes'])}
    # mismo cálculo a beta=0 (¿mejora la distancia de HMA solo re-decidiendo estaciones?)
    rec['t'] = time.time() - t0
    rec['dp_routes'] = dp
    res[base] = rec
    print(base, rec['K'], {k: (round(rec[k].get('cost', -1), 2), rec[k]['ok']) for k in ('pub', 'rep', 'dp', 'dprev')}, f"{rec['t']:.1f}s", flush=True)
json.dump(res, open(out, 'w'))
