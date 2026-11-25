"""Prototipo (paso 2): pool + set partitioning a partir de las soluciones publicadas de HMA.

Uso: python3 proto.py <segundos_por_instancia> <salida.json> [patrón]
Para cada instancia de 100 clientes:
  - referencia: reparación mínima de common/consumo_carga.py (invertir / 1 estación);
  - pool+SP: columnas de reparación (0-2 estaciones), divisiones de rutas
    infactibles, vecindarios (relocate, swap, 2-opt*) y ruin&recreate alrededor
    de la solución vigente, con SP (HiGHS) periódico que re-alimenta la búsqueda.
Toda solución final se comprueba con el juez oficial (check_solution, β=0,2, ρ=0).
"""
import sys, glob, json, time, random
sys.path.insert(0, '/home/user/oe3/pool'); sys.path.insert(0, '/home/user/oe3/common')
from fasteval import Fast
from pool import *
from evrp import read_solution

H = '/home/user/oe3/common/hma'


def baseline_min_repair(F, R):
    """Réplica de la reparación mínima de consumo_carga.py."""
    out = []
    for nodes in R:
        if F.feasible(tuple(nodes)) is not None:
            out.append(nodes); continue
        rev = nodes[::-1]
        if F.feasible(tuple(rev)) is not None:
            out.append(rev); continue
        best = None
        for base in (nodes, rev):
            for k in range(len(base) - 1):
                a, b = base[k], base[k + 1]
                for f in F.stations:
                    if f in (a, b): continue
                    ex = F.Dl[a][f] + F.Dl[f][b] - F.Dl[a][b]
                    if best is not None and ex >= best[0] - 1e-9: continue
                    cand = base[:k + 1] + [f] + base[k + 1:]
                    if F.feasible(tuple(cand)) is not None:
                        best = (ex, cand)
        if best is None:
            return None
        out.append(best[1])
    return out


def run(inst, budget, seed=1, log=None):
    rng = random.Random(seed)
    F = Fast(f'{H}/data/akb_instances/{inst}.txt')
    f = glob.glob(f'{H}/solution/akb/{inst}_timelimit*.txt')[0]
    R0, T0 = read_solution(f)
    R = [[x[0] for x in r] for r in R0]
    res = {'inst': inst, 'pub_K': len(R), 'pub_cost': T0}
    t0 = time.time()
    b = baseline_min_repair(F, R)
    if b is not None:
        j = F.judge(b); res['rep'] = dict(ok=j['ok'], K=j['K'], cost=j['cost'])
    else:
        res['rep'] = dict(ok=False)
    nb = neighbors_of(F)
    P = Pool(F)
    # columnas iniciales
    for c in F.cust:
        rp = repair(F, [0, c, 0], max_st=2)
        if rp: P.add(rp[1], rp[0])
    if b is not None:
        for r in b: P.add(r)
    for r in R:
        rp = repair(F, r, max_st=2, top=len(F.stations))
        if rp:
            P.add(rp[1], rp[0])
        else:  # dividir la ruta en dos
            cs = custs(F, r)
            for cut in range(1, len(cs)):
                for part in (cs[:cut], cs[cut:]):
                    rp2 = repair(F, [0] + part + [0], max_st=2)
                    if rp2: P.add(rp2[1], rp2[0])
    sol, info = P.solve(time_limit=20)
    best = sol; bestc = cost(F, sol)
    hist = [(round(time.time() - t0, 1), len(sol), round(bestc, 2), len(P.cols))]
    cur = sol
    it = 0
    while time.time() - t0 < budget:
        it += 1
        gen_neighborhood(F, P, cur, nb, rng, budget_s=min(8.0, max(1.0, budget - (time.time() - t0))))
        # algunas ruin & recreate desde la solución vigente
        tl = time.time() + min(6.0, max(0.5, budget - (time.time() - t0)))
        while time.time() < tl:
            rr = ruin_recreate(F, P, cur, nb, rng)
        rem = budget - (time.time() - t0)
        sol, info = P.solve(time_limit=max(2.0, min(20.0, rem)))
        if sol is None:
            continue
        c = cost(F, sol)
        if c < bestc - 1e-6:
            best, bestc = sol, c
        cur = sol if rng.random() < 0.8 else best
        hist.append((round(time.time() - t0, 1), len(sol), round(c, 2), len(P.cols)))
    j = F.judge([list(r) for r in best])
    res['pool'] = dict(ok=j['ok'], K=j['K'], cost=round(j['cost'], 2), time=round(time.time() - t0, 1),
                       cols=len(P.cols), evals=F.n_eval, lps=F.n_lp, hist=hist, errors=j['errors'][:3])
    res['pool_routes'] = [list(map(int, r)) for r in best]
    return res


if __name__ == '__main__':
    budget = float(sys.argv[1]); out = sys.argv[2]
    pat = sys.argv[3] if len(sys.argv) > 3 else '*_21'
    insts = sorted(f.split('/')[-1][:-4] for f in glob.glob(f'{H}/data/akb_instances/{pat}.txt'))
    allr = {}
    try:
        allr = json.load(open(out))
    except Exception:
        pass
    for inst in insts:
        if inst in allr:
            continue
        r = run(inst, budget)
        allr[inst] = r
        p = r['pool']; rp = r['rep']
        print(f"{inst:10s} pub K={r['pub_K']} {r['pub_cost']:.2f} | rep {'OK' if rp['ok'] else '--'} "
              f"{rp.get('K', '')} {rp.get('cost', 0):.2f} | pool {'OK' if p['ok'] else 'XX'} K={p['K']} {p['cost']:.2f} "
              f"cols={p['cols']} t={p['time']}", flush=True)
        json.dump(allr, open(out, 'w'))
