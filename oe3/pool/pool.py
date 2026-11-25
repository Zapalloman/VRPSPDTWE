"""Pool de rutas + set partitioning con consumo según la carga (prototipo Python).

Pool: diccionario {frozenset(clientes): (distancia, nodos)} -- se guarda solo la
mejor secuencia factible conocida para cada conjunto de clientes (deduplicación
exacta para el modelo de set partitioning, donde solo importa el conjunto).
"""
import sys, time, random
sys.path.insert(0, '/home/user/oe3/pool')
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import csc_matrix
from fasteval import Fast


class Pool:
    def __init__(self, F):
        self.F = F
        self.cols = {}
        self.cidx = {c: k for k, c in enumerate(F.cust)}
        self.n_add = 0

    def add(self, nodes, dist=None):
        F = self.F
        if dist is None:
            dist = F.feasible(tuple(nodes))
            if dist is None:
                return False
        key = frozenset(i for i in nodes if F.typ[i] == 'c')
        if not key:
            return False
        old = self.cols.get(key)
        self.n_add += 1
        if old is None or dist < old[0] - 1e-9:
            self.cols[key] = (dist, tuple(nodes))
            return True
        return False

    def solve(self, time_limit=30.0, incumbent=None, covering=False):
        """Set partitioning: min sum (mu1 + mu2 d_r) x_r, cada cliente exactamente una vez."""
        F = self.F
        keys = list(self.cols)
        m, n = len(F.cust), len(keys)
        rows, colsi = [], []
        c = np.empty(n)
        for j, k in enumerate(keys):
            d, _ = self.cols[k]
            c[j] = F.I.mu1 + F.I.mu2 * d
            for cu in k:
                rows.append(self.cidx[cu]); colsi.append(j)
        A = csc_matrix((np.ones(len(rows)), (rows, colsi)), shape=(m, n))
        lb = np.ones(m); ub = np.full(m, np.inf if covering else 1.0)
        opts = {'time_limit': time_limit, 'disp': False, 'mip_rel_gap': 1e-6}
        r = milp(c, constraints=LinearConstraint(A, lb, ub), integrality=np.ones(n),
                 bounds=Bounds(0, 1), options=opts)
        if r.x is None:
            return None, r
        sel = [self.cols[keys[j]][1] for j in range(n) if r.x[j] > 0.5]
        return sel, r


# ---------------------------------------------------------------- reparación

def strip(F, nodes):
    return [i for i in nodes if F.typ[i] != 'f']


def repair(F, nodes, max_st=2, top=3):
    """Mejor variante factible (menor distancia) de una secuencia de clientes:
    tal cual / invertida, con 0, 1 o 2 estaciones insertadas. Devuelve (d, nodos) o None."""
    best = None
    D = F.Dl
    St = F.stations
    for base in (list(nodes), list(nodes)[::-1]):
        for b0 in (base, strip(F, base)):
            d = F.feasible(tuple(b0))
            if d is not None and (best is None or d < best[0]):
                best = (d, tuple(b0))
    if best is not None and max_st == 0:
        return best
    bases = [strip(F, nodes), strip(F, nodes)[::-1]]
    if any(F.typ[i] == 'f' for i in nodes):
        bases += [list(nodes), list(nodes)[::-1]]
    for base in bases:
        # candidatos por arco: mejores 'top' estaciones por desvío
        cands = []
        for k in range(len(base) - 1):
            a, b = base[k], base[k + 1]
            ds = sorted((D[a][f] + D[f][b] - D[a][b], f) for f in St if f != a and f != b)[:top]
            cands.append(ds)
        one = []
        for k in range(len(base) - 1):
            for ex, f in cands[k]:
                one.append((ex, k, f))
        one.sort()
        found1 = False
        for ex, k, f in one:
            if best is not None and F.route_dist(base) + ex >= best[0] - 1e-9:
                break
            cand = base[:k + 1] + [f] + base[k + 1:]
            d = F.feasible(tuple(cand))
            if d is not None:
                best = (d, tuple(cand)); found1 = True
                break
        if found1 or max_st < 2:
            continue
        # dos estaciones (si una no basta)
        if best is not None or base is not bases[0] and base is not bases[1]:
            continue
        two = []
        for i1 in range(len(one)):
            for i2 in range(i1 + 1, len(one)):
                a, b = one[i1], one[i2]
                if a[1] == b[1]:
                    continue
                two.append((a[0] + b[0], a, b))
        two.sort()
        for ex, a, b in two[:60]:
            (_, k1, f1), (_, k2, f2) = sorted([a, b], key=lambda x: x[1])
            cand = base[:k1 + 1] + [f1] + base[k1 + 1:k2 + 1] + [f2] + base[k2 + 1:]
            d = F.feasible(tuple(cand))
            if d is not None:
                best = (d, tuple(cand))
                break
    return best


# ------------------------------------------------------ generación de columnas

def custs(F, r):
    return [i for i in r if F.typ[i] == 'c']


def neighbors_of(F, k=15):
    D = F.D
    cu = np.array(F.cust)
    nb = {}
    for c in F.cust:
        o = cu[np.argsort(D[c, cu] + D[cu, c])]
        nb[c] = set(int(x) for x in o[1:k + 1])
    return nb


def gen_neighborhood(F, P, sol, nb, rng, budget_s=10.0, repair_fail=True):
    """Columnas desde una solución: relocate, swap, 2-opt*, y reordenamientos
    intra-ruta conscientes de la carga. Toda ruta factible evaluada entra al pool."""
    t0 = time.time()
    routes = [list(r) for r in sol]
    cr = [set(custs(F, r)) for r in routes]
    where = {}
    for ri, s in enumerate(cr):
        for c in s:
            where[c] = ri
    for r in routes:
        P.add(r)
    pairs = set()
    for c, ri in where.items():
        for c2 in nb[c]:
            rj = where.get(c2)
            if rj is not None and rj != ri:
                pairs.add((ri, rj))
    pairs = list(pairs); rng.shuffle(pairs)
    for (ri, rj) in pairs:
        if time.time() - t0 > budget_s:
            break
        A = strip(F, routes[ri]); B = strip(F, routes[rj])
        # relocate: cliente de A en B (todas las posiciones), y A sin el cliente
        for c in custs(F, A):
            if not (nb[c] & cr[rj]):
                continue
            Am = [x for x in A if x != c]
            if len(Am) > 2:
                if P.add(Am) is False and F.feasible(tuple(Am)) is None and repair_fail:
                    rp = repair(F, Am, max_st=1)
                    if rp: P.add(rp[1], rp[0])
            ok = False
            for p in range(1, len(B)):
                cand = B[:p] + [c] + B[p:]
                if F.feasible(tuple(cand)) is not None:
                    P.add(cand); ok = True
            if not ok and repair_fail:
                # inserción con estación: probar las 2 mejores posiciones por distancia
                D = F.Dl
                pos = sorted(range(1, len(B)), key=lambda p: D[B[p-1]][c] + D[c][B[p]] - D[B[p-1]][B[p]])[:2]
                for p in pos:
                    rp = repair(F, B[:p] + [c] + B[p:], max_st=1)
                    if rp: P.add(rp[1], rp[0])
        # 2-opt*: intercambio de colas
        for i in range(1, len(A)):
            for j in range(1, len(B)):
                n1 = A[:i] + B[j:]; n2 = B[:j] + A[i:]
                for nn in (n1, n2):
                    if len(nn) > 2 and F.feasible(tuple(nn)) is not None:
                        P.add(nn)
        # swap de clientes cercanos
        for a in custs(F, A):
            for b in nb[a] & cr[rj]:
                ia = A.index(a); ib = B.index(b)
                n1 = A[:ia] + [b] + A[ia + 1:]; n2 = B[:ib] + [a] + B[ib + 1:]
                for nn in (n1, n2):
                    if F.feasible(tuple(nn)) is not None:
                        P.add(nn)
    # reparación de rutas propias con estación (columnas con estaciones nuevas)
    for r in routes:
        rp = repair(F, strip(F, r), max_st=2)
        if rp: P.add(rp[1], rp[0])
    return time.time() - t0


def ruin_recreate(F, P, sol, nb, rng, frac=(0.1, 0.25)):
    """LNS simple: remoción relacionada + inserción más barata factible (con
    estación si hace falta). Devuelve nueva solución completa o None."""
    routes = [strip(F, r) for r in sol]
    allc = [c for r in routes for c in r if F.typ[c] == 'c']
    q = rng.randint(int(frac[0] * len(allc)), int(frac[1] * len(allc)))
    seed = rng.choice(allc)
    order = sorted(allc, key=lambda c: F.D[seed, c] + F.D[c, seed])
    rem = set(order[:q])
    routes = [[x for x in r if x not in rem] for r in routes]
    routes = [r for r in routes if len(r) > 2]
    rem = list(rem); rng.shuffle(rem)
    # orden: mayor demanda primero (más difícil con consumo según la carga)
    rem.sort(key=lambda c: -(F.u[c] + F.v[c]) * rng.uniform(0.7, 1.3))
    D = F.Dl
    for c in rem:
        best = None
        for ri, r in enumerate(routes):
            for p in range(1, len(r)):
                ex = D[r[p-1]][c] + D[c][r[p]] - D[r[p-1]][r[p]]
                if best is not None and ex >= best[0]:
                    continue
                cand = r[:p] + [c] + r[p:]
                if F.feasible(tuple(cand)) is not None:
                    best = (ex, ri, cand)
        if best is None:
            # con estación: mejores posiciones por desvío
            opts = []
            for ri, r in enumerate(routes):
                rs = strip(F, r)
                for p in range(1, len(rs)):
                    ex = D[rs[p-1]][c] + D[c][rs[p]] - D[rs[p-1]][rs[p]]
                    opts.append((ex, ri, p))
            opts.sort()
            for ex, ri, p in opts[:4]:
                rs = strip(F, routes[ri])
                rp = repair(F, rs[:p] + [c] + rs[p:], max_st=1)
                if rp:
                    best = (rp[0] - F.route_dist(routes[ri]), ri, list(rp[1])); break
        if best is None:
            rp = repair(F, [0, c, 0], max_st=2)
            if rp is None:
                return None
            routes.append(list(rp[1]))
        else:
            routes[best[1]] = best[2]
            P.add(best[2])
    for r in routes:
        P.add(r)
    return routes


def cost(F, sol):
    return F.I.mu1 * len(sol) + F.I.mu2 * sum(F.route_dist(r) for r in sol)


# ------------------------------------------------- SP con highspy + incumbente

def _build(P, keys, integer):
    import highspy
    F = P.F
    m, n = len(F.cust), len(keys)
    h = highspy.Highs()
    h.setOptionValue('output_flag', False)
    h.setOptionValue('threads', 1)
    cost = np.array([F.I.mu1 + F.I.mu2 * P.cols[k][0] for k in keys])
    rows = [[] for _ in range(m)]
    for j, k in enumerate(keys):
        for cu in k:
            rows[P.cidx[cu]].append(j)
    h.addVars(n, np.zeros(n), np.ones(n))
    h.changeColsCost(n, np.arange(n, dtype=np.int32), cost)
    if integer:
        h.changeColsIntegrality(n, np.arange(n, dtype=np.int32),
                                np.array([highspy.HighsVarType.kInteger] * n))
    for i in range(m):
        idx = np.array(rows[i], dtype=np.int32)
        h.addRow(1.0, 1.0, len(idx), idx, np.ones(len(idx)))
    return h, cost


def solve_highs(P, time_limit=30.0, incumbent=None, verbose=False, max_cols=2000, pre_cap=20000):
    """Set partitioning con HiGHS (highspy).
    1) relajación lineal sobre todo el pool -> cota LB y costos reducidos;
    2) fijación por costo reducido: una columna con costo reducido > UB - LB no
       puede estar en una solución mejor que la incumbente (UB), así que se
       descarta (exacto); si quedan más de max_cols, se conservan las de menor
       costo reducido (heurístico) más las de la incumbente;
    3) MIP sobre el subconjunto, arrancando desde la incumbente."""
    import highspy
    t0 = time.time()
    F = P.F
    keys = list(P.cols)
    inc_keys = []
    if incumbent is not None:
        inc_keys = [frozenset(i for i in r if F.typ[i] == 'c') for r in incumbent]
        if not all(k in P.cols for k in inc_keys):
            inc_keys = []
    UB = sum(F.I.mu1 + F.I.mu2 * P.cols[k][0] for k in inc_keys) if inc_keys else np.inf
    exact = True
    if len(keys) > pre_cap:
        # pre-filtro barato: mejores columnas por costo por cliente + incumbente
        sc = sorted(keys, key=lambda k: (F.I.mu1 + F.I.mu2 * P.cols[k][0]) / len(k))
        ks = set(sc[:pre_cap]) | set(inc_keys)
        keys = [k for k in keys if k in ks]
        exact = False
    sub = keys
    if len(keys) > max_cols:
        h, cost = _build(P, keys, False)
        h.setOptionValue('time_limit', float(max(1.0, 0.4 * time_limit)))
        h.run()
        if h.getModelStatus() == highspy.HighsModelStatus.kOptimal:
            LB = h.getInfo().objective_function_value
            rc = np.array(h.getSolution().col_dual)
            order = np.argsort(rc)
            keep = [j for j in order if rc[j] <= UB - LB + 1e-6]
            if len(keep) > max_cols:
                keep = list(order[:max_cols]); exact = False
            ks = set(keys[j] for j in keep) | set(inc_keys)
            sub = [k for k in keys if k in ks]
    pos = {k: j for j, k in enumerate(sub)}
    n = len(sub)
    h, cost = _build(P, sub, True)
    h.setOptionValue('time_limit', float(max(0.5, time_limit - (time.time() - t0))))
    h.setOptionValue('mip_rel_gap', 1e-7)
    if inc_keys:
        x0 = np.zeros(n)
        for k in inc_keys:
            x0[pos[k]] = 1.0
        sol = highspy.HighsSolution()
        sol.col_value = list(x0)
        sol.value_valid = True
        h.setSolution(sol)
    h.run()
    st = h.getModelStatus()
    info = h.getInfo()
    if info.primal_solution_status == 0:
        return None, st
    x = h.getSolution().col_value
    sel = [P.cols[sub[j]][1] for j in range(n) if x[j] > 0.5]
    return sel, (str(st).split('.')[-1], round(info.mip_gap, 4), len(keys), n, exact)
