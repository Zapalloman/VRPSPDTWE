"""Resuelve el set partitioning sobre un pool de rutas volcado por HMA-LD-pool.

Uso: python3 sp_solve.py <instancia.txt> <pool.txt> <salida.txt> <segundos> [--polish] [--seed S]
  pool.txt: una ruta por línea, ids de nodos separados por espacio (0 ... 0).
  Se filtran con el evaluador rápido (β=0,2) -> pool deduplicado por conjunto de
  clientes (se conserva la secuencia más corta). Si --polish, tras el primer SP
  se alternan vecindarios/ruin&recreate en Python y nuevos SP hasta agotar el tiempo.
  salida.txt: una ruta por línea (misma notación); primera línea "# costo K".
"""
import sys, time, random, os
sys.path.insert(0, '/home/user/oe3/pool')
from fasteval import Fast
from pool import Pool, solve_highs, repair, strip, custs, neighbors_of, gen_neighborhood, ruin_recreate, cost


def load_pool_fast(F, P, path, max_s=1e9):
    """Carga sin evaluar (las rutas vienen marcadas factibles por HMA-LD); se
    conserva la más corta por conjunto de clientes. La factibilidad se verifica
    después, solo para las columnas que elige el SP (verificación perezosa)."""
    t0 = time.time()
    D = F.Dl; typ = F.typ
    n = 0
    for line in open(path):
        n += 1
        nodes = tuple(int(x) for x in line.split())
        if len(nodes) < 3 or nodes[0] != 0 or nodes[-1] != 0:
            continue
        key = frozenset(i for i in nodes if typ[i] == 'c')
        d = 0.0
        for k in range(len(nodes) - 1):
            d += D[nodes[k]][nodes[k + 1]]
        old = P.cols.get(key)
        if old is None or d < old[0] - 1e-9:
            P.cols[key] = (d, nodes)
        if (n & 4095) == 0 and time.time() - t0 > max_s:
            break
    return n


def verified_solve(F, P, time_limit, incumbent=None):
    """Resuelve el SP; si alguna columna elegida no es factible para el
    evaluador (juez), la elimina y vuelve a resolver."""
    t0 = time.time()
    while True:
        sol, info = solve_highs(P, max(1.0, time_limit - (time.time() - t0)), incumbent)
        if sol is None:
            return None, info
        bad = [r for r in sol if F.feasible(tuple(r)) is None]
        if not bad:
            return sol, info
        for r in bad:
            P.cols.pop(frozenset(i for i in r if F.typ[i] == 'c'), None)
        if incumbent is not None and any(tuple(r) in set(map(tuple, bad)) for r in incumbent):
            incumbent = None


def load_pool(F, P, path, offset=0):
    n = 0; bad = 0
    with open(path) as fh:
        fh.seek(offset)
        for line in fh:
            if not line.endswith('\n'):
                break
            n += 1
            nodes = tuple(int(x) for x in line.split())
            if len(nodes) < 3 or nodes[0] != 0 or nodes[-1] != 0:
                continue
            d = F.feasible(nodes)
            if d is None:
                bad += 1; continue
            P.add(nodes, d)
        off = fh.tell()
    return n, bad, off


def main():
    inst, pool_path, out, secs = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
    polish = '--polish' in sys.argv
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1
    inc_path = sys.argv[sys.argv.index('--inc') + 1] if '--inc' in sys.argv else None
    t0 = time.time()
    rng = random.Random(seed)
    F = Fast(inst)
    P = Pool(F)
    n = load_pool_fast(F, P, pool_path, max_s=0.35 * secs)
    inc = None
    if inc_path and os.path.exists(inc_path):
        inc = [tuple(int(x) for x in l.split()) for l in open(inc_path) if l.strip()]
        for r in inc:
            d = F.feasible(r)
            if d is None:
                inc = None; break
            key = frozenset(i for i in r if F.typ[i] == 'c')
            old = P.cols.get(key)
            if old is None or d < old[0] - 1e-9:
                P.cols[key] = (d, r)
    for c in F.cust:  # garantiza factibilidad del SP
        if frozenset([c]) not in P.cols:
            rp = repair(F, [0, c, 0], max_st=2)
            if rp: P.add(rp[1], rp[0])
    t_load = time.time() - t0
    rem = secs - t_load
    tl = rem - 0.5 if not polish else 0.6 * rem
    best = inc; bestc = cost(F, inc) if inc else float('inf')
    sol = None
    while sol is None and time.time() - t0 < secs - 0.5:
        sol, info = verified_solve(F, P, max(1.0, tl), inc)
        # si se eliminó una columna de la incumbente, re-agregar la ruta de HMA
        if inc:
            for r in inc:
                key = frozenset(i for i in r if F.typ[i] == 'c')
                if key not in P.cols:
                    P.cols[key] = (F.route_dist(r), r)
    if sol is not None and cost(F, sol) < bestc - 1e-6:
        best, bestc = sol, cost(F, sol)
    log = [f'pool lineas={n} columnas={len(P.cols)} carga={t_load:.1f}s SP={bestc:.2f} K={len(best)} info={info} t={time.time()-t0:.1f}']
    if polish:
        nb = neighbors_of(F)
        cur = best
        while time.time() - t0 < secs - 1.5:
            rem = secs - (time.time() - t0)
            gen_neighborhood(F, P, cur, nb, rng, budget_s=min(5.0, 0.3 * rem))
            tl2 = time.time() + min(4.0, 0.2 * rem)
            while time.time() < tl2:
                ruin_recreate(F, P, cur, nb, rng)
            rem = secs - (time.time() - t0)
            if rem < 1.5:
                break
            s2, _ = verified_solve(F, P, max(1.0, min(15.0, rem - 1.0)), best)
            if s2 is None:
                continue
            c2 = cost(F, s2)
            if c2 < bestc - 1e-6:
                best, bestc = s2, c2
            cur = s2
        log.append(f'pulido: SP={bestc:.2f} K={len(best)} columnas={len(P.cols)} t={time.time()-t0:.1f}')
    j = F.judge([list(r) for r in best])
    with open(out, 'w') as fh:
        fh.write(f'# {j["cost"]:.4f} {j["K"]} ok={j["ok"]}\n')
        for r in best:
            fh.write(' '.join(map(str, r)) + '\n')
    print('\n'.join(log), flush=True)


if __name__ == '__main__':
    main()
