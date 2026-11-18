"""Pruebas de mutación: el comprobador debe rechazar soluciones alteradas."""
import glob, os, random, copy, sys, json
from evrp import *
H = sys.argv[1]
random.seed(2026)
kinds = {"quitar_cliente": 0, "duplicar_cliente": 0, "intercambiar_clientes": 0, "quitar_estacion": 0, "alterar_costo": 0}
det = {k: 0 for k in kinds}
for f in sorted(glob.glob(H + '/solution/akb/*.txt')):
    base = os.path.basename(f).split('_timelimit')[0]
    I = read_instance(H + '/data/akb_instances/' + base + '.txt'); R, T = read_solution(f)
    for kind in kinds:
        R2 = copy.deepcopy(R); T2 = T
        cust_pos = [(a, b) for a, r in enumerate(R2) for b in range(1, len(r) - 1) if I.typ[r[b][0]] == 'c']
        st_pos = [(a, b) for a, r in enumerate(R2) for b in range(1, len(r) - 1) if I.typ[r[b][0]] == 'f']
        if kind == "quitar_cliente":
            a, b = random.choice(cust_pos); del R2[a][b]
        elif kind == "duplicar_cliente":
            a, b = random.choice(cust_pos); a2 = random.randrange(len(R2)); R2[a2].insert(1, R2[a][b])
        elif kind == "intercambiar_clientes":
            # intercambia dos clientes de rutas/posiciones distintas
            (a, b), (c, d) = random.sample(cust_pos, 2); R2[a][b], R2[c][d] = R2[c][d], R2[a][b]
        elif kind == "quitar_estacion":
            if not st_pos: continue
            a, b = random.choice(st_pos); del R2[a][b]
        elif kind == "alterar_costo":
            T2 = T + 1.0
        kinds[kind] += 1
        res = check_solution(I, R2, T2, use_reported=False)
        det[kind] += (not res['ok'])
out = {k: {"mutaciones": kinds[k], "detectadas": det[k]} for k in kinds}
print(json.dumps(out, indent=1, ensure_ascii=False)); json.dump(out, open('mutaciones.json', 'w'), indent=1, ensure_ascii=False)
