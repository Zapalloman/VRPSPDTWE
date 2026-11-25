"""Prueba de estrés del greedy de recarga con 2+ estaciones (donde las esperas importan).

Se toman rutas publicadas, se insertan 1-3 estaciones al azar y se reduce la batería Q
(factor 0,45-1,0) para forzar recargas en varias estaciones. Se compara el resumen con
el juez (LP) y también la política "cargar lo justo, lo más tarde posible" (sin carga
gratis en esperas), para mostrar que la parte de holgura es necesaria y suficiente.
"""
import sys, glob, os, random, copy
sys.path.insert(0, "/home/user/oe3/common")
from evrp import read_instance, read_solution, eval_route
import resumen
from resumen import Model

H = "/home/user/oe3/common/hma"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
BETA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2


class Late(Model):
    def eval_route(self, s):
        # misma evaluación pero sin carga gratis
        g0 = self.g
        head, mids, tail = self._parts(s) if s.legs is not None else (s, [], None)
        return Model.eval_route(self, s) if s.legs is None else self._late(s)

    def _late(self, s):
        C, Q, g = self.C, self.Q, self.g
        L0 = s.U
        if L0 + s.H > C + 1e-9 or not s.ok:
            return False, s.d
        head, mids, tail = self._parts(s)
        legs = [head] + mids + [tail]
        E, L = [], L0
        for lg in legs:
            E.append(self.energy(lg, L)); L += lg.Dl
        if E[0] > Q + 1e-9 or not head.ok:
            return False, s.d
        t = head.TE + head.D; b = Q - E[0]
        for k in range(1, len(legs)):
            lg = legs[k]
            if not lg.ok or E[k] > Q + 1e-9:
                return False, s.d
            q = max(0.0, E[k] - b); t += g * q
            if t > lg.TL + 1e-7:
                return False, s.d
            t = max(t, lg.TE) + lg.D; b += q - E[k]
        return True, s.d


def main():
    rng = random.Random(7)
    tot = agree = fe = late_fe = multi = 0
    bad = []
    for f in sorted(glob.glob(f"{H}/data/akb_instances/*.txt")):
        name = os.path.basename(f)[:-4]
        sol = glob.glob(f"{H}/solution/akb/{name}_timelimit*")
        if not sol:
            continue
        I0 = read_instance(f)
        routes = [[x[0] for x in r] for r in read_solution(sol[0])[0]]
        for _ in range(N):
            I = copy.copy(I0); I.Q = I0.Q * rng.uniform(0.6, 1.0)
            M, ML = Model(I, BETA), Late(I, BETA)
            r = list(rng.choice(routes))
            inner = [x for x in r[1:-1] if rng.random() < 0.5 or I.typ[x] == "c"]
            for _k in range(rng.randint(1, 3)):
                p = rng.randrange(len(inner) + 1)
                a = ([0] + inner)[p]; b = (inner + [0])[p]
                best = sorted(I.stations, key=lambda f: I.dist[a, f] + I.dist[f, b])[:3]
                inner.insert(p, rng.choice(best))
            nodes = [0] + inner + [0]
            jr = eval_route(I, nodes, BETA, 0.0)
            s = M.seq(nodes)
            ok = M.eval_route(s)[0]; okl = ML.eval_route(s)[0]
            tot += 1; fe += jr["feasible"]; late_fe += okl
            multi += sum(1 for x in nodes if I.typ[x] == "f") >= 2
            if ok == jr["feasible"]:
                agree += 1
            else:
                bad.append((name, round(I.Q, 3), nodes, jr["feasible"], ok, jr["viol"]))
    print(f"beta={BETA} rutas={tot} (con >=2 estaciones: {multi})  factibles juez={fe}")
    print(f"resumen coincide={agree}/{tot}   política tardía factibles={late_fe} (pierde {fe-late_fe})")
    for b in bad[:8]:
        print("DISCREPANCIA", b)


main()
