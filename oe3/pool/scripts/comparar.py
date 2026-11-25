"""Compara un método (corridas.csv de bench.py) con HMA-LD de base, por instancia y semilla.
Uso: python3 comparar.py <corridas_metodo.csv> [ref.csv]"""
import csv, sys, statistics as st
m = sys.argv[1]
ref = sys.argv[2] if len(sys.argv) > 2 else '/home/user/oe3/base/resultados/hma_ld/corridas.csv'
def load(p):
    d = {}
    for r in csv.DictReader(open(p)):
        if int(r['n_clientes']) < 100: continue
        d[(r['instancia'], r['semilla'])] = r
    return d
A, B = load(ref), load(m)
keys = sorted(set(A) & set(B))
insts = sorted(set(k[0] for k in keys))
print('| instancia | HMA-LD TC medio | K medio | método TC medio | K medio | Δ TC medio | mejor/igual/peor |')
print('|---|---|---|---|---|---|---|')
w = t = l = 0; dK = []; dTC = []; fa = fb = 0
for i in insts:
    ks = [k for k in keys if k[0] == i]
    ta = [float(A[k]['costo_TC']) for k in ks if A[k]['factible'] == '1']
    tb = [float(B[k]['costo_TC']) for k in ks if B[k]['factible'] == '1']
    ka = [int(A[k]['K']) for k in ks if A[k]['factible'] == '1']
    kb = [int(B[k]['K']) for k in ks if B[k]['factible'] == '1']
    fa += len(ta); fb += len(tb)
    ww = tt = ll = 0
    for k in ks:
        if A[k]['factible'] != '1' or B[k]['factible'] != '1': continue
        a, b = float(A[k]['costo_TC']), float(B[k]['costo_TC'])
        dK.append(int(B[k]['K']) - int(A[k]['K'])); dTC.append(100 * (b / a - 1))
        if b < a - 0.01: ww += 1
        elif b > a + 0.01: ll += 1
        else: tt += 1
    w += ww; t += tt; l += ll
    print(f'| {i} | {st.mean(ta):.2f} | {st.mean(ka):.2f} | {st.mean(tb):.2f} | {st.mean(kb):.2f} | {st.mean(tb)-st.mean(ta):+.2f} | {ww}/{tt}/{ll} |')
print(f'\nCorridas pareadas: {len(dTC)}; factibles ref {fa}, método {fb}. Mejor/igual/peor: {w}/{t}/{l}. '
      f'Vehículos totales: ref {sum(int(A[k]["K"]) for k in keys)}, método {sum(int(B[k]["K"]) for k in keys)} (Δ {sum(dK):+d}). '
      f'Δ TC medio por corrida: {st.mean(dTC):+.3f} %.')
