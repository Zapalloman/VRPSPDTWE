"""Verifica frvcp (etiquetas) contra fuerza bruta evaluada con el PL del juez (evrp.eval_route)."""
import glob, os, random, itertools, copy
from frvcp import *
H = '/home/user/oe3/common/hma'
random.seed(int(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 7)
files = sorted(glob.glob(H + '/data/akb_instances/*C*.txt'))
tests = ok = infeas_both = 0
mism = 0
withst = 0
for trial in range(400):
    I = copy.deepcopy(read_instance(random.choice(files)))
    cs = I.customers
    m = random.randint(2, min(4, len(cs)))
    seq = random.sample(cs, m)
    seq.sort(key=lambda c: I.e[c] + random.random() * 5)  # orden más o menos compatible con ventanas
    cust = [0] + seq + [0]
    I.Q *= random.uniform(0.45, 1.0)          # batería estrecha para que hagan falta estaciones
    I.C = max(sum(I.dlv[c] for c in seq), 1.0) * random.uniform(1.0, 1.6)
    I.g *= random.uniform(0.3, 2.0)
    beta = random.choice([0.0, 0.2, 0.3])
    maxper = 2 if (len(I.stations) <= 4 and m <= 3) else 1
    S = I.stations
    opts = [()] + [(f,) for f in S] + ([(f, g) for f in S for g in S if f != g] if maxper == 2 else [])
    cands = []
    for combo in itertools.product(opts, repeat=len(cust) - 1):
        nodes = [0]
        for k, p in enumerate(combo):
            nodes += list(p) + [cust[k + 1]]
        if any(nodes[t] == nodes[t+1] for t in range(len(nodes)-1)):
            continue
        cands.append((sum(I.dist[nodes[t], nodes[t+1]] for t in range(len(nodes)-1)), nodes))
    cands.sort(key=lambda x: x[0])
    # fuerza bruta en orden de distancia: el primer candidato factible es el óptimo.
    # Los primeros 400 candidatos se evalúan con el PL del juez; el resto con el evaluador O(n)
    # (validado aparte contra el PL) y el ganador se confirma con el PL.
    best = None
    for idx, (d, nodes) in enumerate(cands):
        fe = eval_route(I, nodes, beta)['feasible'] if idx < 400 else feasible_fixed(I, nodes, beta)
        if fe:
            best = (d, nodes); break
    if best is not None and not eval_route(I, best[1], beta)['feasible']:
        print('AVISO: ganador O(n) rechazado por el PL', best)
    r = frvcp(I, cust, beta, maxper=maxper)
    tests += 1
    if best is None and r is None:
        infeas_both += 1; ok += 1
    elif best is not None and r is not None and abs(best[0] - r[0]) < 1e-6 and eval_route(I, r[1], beta)['feasible']:
        ok += 1; withst += any(I.typ[i]=='f' for i in r[1])
    else:
        mism += 1
        print('DISCREPANCIA', I.name, beta, maxper, cust, 'fb', best, 'dp', r)
print(f'pruebas {tests}, coinciden {ok} (ambas infactibles {infeas_both}), discrepan {mism}; óptimos factibles que usan estaciones {withst}')
