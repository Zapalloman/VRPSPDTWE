"""Subproblema de recarga exacto para una secuencia fija de clientes (FRVCP-TW-LD).

Dada la secuencia de clientes de una ruta (depósito al inicio y al final), elegir
qué estaciones visitar entre cada par de clientes consecutivos y cuánto recargar
en cada una, minimizando la distancia, con batería en [0, Q], ventanas de tiempo,
recarga parcial lineal (g unidades de tiempo por unidad de energía) y consumo
dependiente de la carga e_ij(L) = h d_ij (1 + beta (L/C - rho)).

Idea central (función de compromiso tiempo-batería de 3 parámetros)
-------------------------------------------------------------------
En cualquier punto de la ruta, el conjunto de estados alcanzables
(instante A en que el vehículo está listo, batería b) queda descrito por
    F(A) = min(bmax, b0 + (A - a)/g)   para A >= a      (y -inf para A < a)
es decir, por tres números (a, b0, bmax): instante más temprano, batería en ese
instante (cargando lo mínimo) y batería máxima alcanzable postergando la salida.
La familia es cerrada bajo las cuatro operaciones del problema:
  * arco (t, e):  a += t + g*max(0, e - b0);  b0 = max(b0, e) - e;  bmax -= e
                  (infactible si bmax < e)
  * cliente [el, ll], s:  infactible si a > ll;  bmax = min(bmax, b0 + (ll - a)/g);
                  si a < el: b0 = min(bmax, b0 + (el - a)/g) (se recarga "gratis"
                  durante la espera), a = el + s;  si no: a += s
  * estación:     bmax = Q   (recargar es lo más rápido para ganar batería, así
                  que llegar antes y cargar más domina a llegar después; F tiene
                  pendiente <= 1/g y su supconvolución con la recta 1/g parte de a)
  * depósito final: factible si a <= l_0.
Por eso, con las estaciones fijas, la factibilidad exacta (equivalente al
programa lineal de evrp.plan_recarga) se decide en O(n) sin resolver un PL.

Con las estaciones por decidir se usa un algoritmo de etiquetas sobre la
secuencia: en cada tramo (c_k, c_k+1) se prueban 0, 1 o 2 estaciones; la carga
(y por tanto la tasa de consumo) es constante dentro del tramo. Una etiqueta
(dist, a, b0, bmax) domina a otra si dist <= dist', a <= a', bmax >= bmax' y
F(a') >= b0'. La dominancia es exacta (F1 >= F2 punto a punto), así que el
algoritmo devuelve el óptimo del subproblema con a lo más `maxper` estaciones
por tramo.
"""
import evrp_path  # noqa: F401  (añade common/ al path)
from evrp import read_instance, read_solution, eval_route, energy, EPS

TOL = 1e-7


class Lab:
    __slots__ = ("d", "a", "b", "m", "prev", "node")

    def __init__(self, d, a, b, m, prev, node):
        self.d, self.a, self.b, self.m, self.prev, self.node = d, a, b, m, prev, node


def arc(I, lab, i, j, phi):
    """Propaga la etiqueta por el arco i->j con factor de consumo phi (=h(1+beta(L/C-rho)))."""
    e = phi * I.dist[i, j]
    if lab[2] < e - TOL:
        return None
    a, b, m = lab[0], lab[1], lab[2]
    if b < e:
        a += I.g * (e - b); b = e
    return (a + I.tm[i, j], max(0.0, b - e), m - e)


def at_customer(I, lab, c):
    a, b, m = lab
    if a > I.l[c] + TOL:
        return None
    m = min(m, b + (I.l[c] - a) / I.g)
    if a < I.e[c]:
        b = min(m, b + (I.e[c] - a) / I.g); a = I.e[c]
    return (a + I.s[c], b, m)


def at_station(I, lab):
    return (lab[0], lab[1], I.Q)


def leg_factors(I, cust, beta, rho):
    """cust = [0, c1, ..., cm, 0]. Devuelve el factor de consumo de cada tramo."""
    load = sum(I.dlv[c] for c in cust[1:-1])
    out = []
    for k in range(len(cust) - 1):
        if k > 0:
            load = load - I.dlv[cust[k]] + I.pck[cust[k]]
        out.append(I.h * (1.0 + beta * (load / I.C - rho)))
    return out, load


def feasible_fixed(I, nodes, beta=0.2, rho=0.0):
    """Factibilidad exacta O(n) de una ruta con estaciones fijas (reemplaza el PL)."""
    load = sum(I.dlv[i] for i in nodes if I.typ[i] == "c")
    if load > I.C + EPS:
        return False
    lab = (I.e[0], I.Q, I.Q)
    for k in range(len(nodes) - 1):
        i, j = nodes[k], nodes[k + 1]
        if k > 0 and I.typ[i] == "c":
            load = load - I.dlv[i] + I.pck[i]
            if load > I.C + EPS:
                return False
        lab = arc(I, lab, i, j, I.h * (1.0 + beta * (load / I.C - rho)))
        if lab is None:
            return False
        t = I.typ[j]
        if k + 1 == len(nodes) - 1:
            return lab[0] <= I.l[0] + TOL
        lab = at_customer(I, lab, j) if t == "c" else at_station(I, lab)
        if lab is None:
            return False
    return True


def dominates(x, y):
    """x domina a y (ambas Lab)."""
    if x.d > y.d + 1e-9 or x.a > y.a + 1e-9 or x.m < y.m - 1e-9:
        return False
    return min(x.m, x.b + (y.a - x.a) / I_g[0]) >= y.b - 1e-9


I_g = [1.0]


def insert_label(bucket, L):
    for x in bucket:
        if dominates(x, L):
            return False
    bucket[:] = [x for x in bucket if not dominates(L, x)]
    bucket.append(L)
    return True


def station_candidates(I, i, j, k_near=None):
    S = I.stations
    if k_near is None:
        return S
    return sorted(S, key=lambda f: I.dist[i, f] + I.dist[f, j])[:k_near]


def frvcp(I, cust, beta=0.2, rho=0.0, maxper=2, k_near=None, ub=float("inf")):
    """Algoritmo de etiquetas. cust = [0, c1, ..., cm, 0] (sin estaciones).
    Devuelve (distancia, nodos con estaciones) óptimos, o None si no hay plan factible.
    k_near: limita las estaciones candidatas por tramo a las k más cercanas (None = todas).
    """
    I_g[0] = I.g
    phis, _ = leg_factors(I, cust, beta, rho)
    load0 = sum(I.dlv[c] for c in cust[1:-1])
    if load0 > I.C + EPS:
        return None
    load = load0
    for c in cust[1:-1]:
        load = load - I.dlv[c] + I.pck[c]
        if load > I.C + EPS:
            return None
    # cota inferior de distancia restante (arcos directos)
    rem = [0.0] * len(cust)
    for k in range(len(cust) - 2, -1, -1):
        rem[k] = rem[k + 1] + I.dist[cust[k], cust[k + 1]]
    bucket = [Lab(0.0, I.e[0], I.Q, I.Q, None, 0)]
    last = len(cust) - 1
    for k in range(last):
        i, j, phi = cust[k], cust[k + 1], phis[k]
        nxt = []
        cands = station_candidates(I, i, j, k_near)
        for L in bucket:
            st = (L.a, L.b, L.m)
            paths = [()]
            if maxper >= 1:
                paths += [(f,) for f in cands if f != i and f != j]
            if maxper >= 2:
                paths += [(f, g) for f in cands for g in cands if f != g and f != i and g != j]
            for p in paths:
                seq = (i,) + p + (j,)
                dd = sum(I.dist[seq[t], seq[t + 1]] for t in range(len(seq) - 1))
                if L.d + dd + rem[k + 1] > ub + 1e-9:
                    continue
                s, ok = st, True
                for t in range(len(seq) - 1):
                    s = arc(I, s, seq[t], seq[t + 1], phi)
                    if s is None:
                        ok = False; break
                    if t + 1 < len(seq) - 1:
                        s = at_station(I, s)
                if not ok:
                    continue
                if k + 1 == last:
                    if s[0] > I.l[0] + TOL:
                        continue
                else:
                    s = at_customer(I, s, j)
                    if s is None:
                        continue
                insert_label(nxt, Lab(L.d + dd, s[0], s[1], s[2], L, p))
        bucket = nxt
        if not bucket:
            return None
    best = min(bucket, key=lambda x: x.d)
    # reconstrucción
    segs, x = [], best
    while x.prev is not None:
        segs.append(x.node); x = x.prev
    segs.reverse()
    nodes = [cust[0]]
    for k, p in enumerate(segs):
        nodes += list(p) + [cust[k + 1]]
    return best.d, nodes
