"""Comparación pareada (misma instancia y semilla) de dos corridas.csv de bench.py.
Uso: python3 comparar.py REF.csv MET.csv [--md salida.md] [--nombres ref met]
Imprime tabla por instancia, totales, ganadas/empates/perdidas, prueba de signos y Wilcoxon."""
import csv, sys, argparse
from collections import defaultdict
from scipy.stats import binomtest, wilcoxon

ap = argparse.ArgumentParser()
ap.add_argument('ref'); ap.add_argument('met'); ap.add_argument('--md'); ap.add_argument('--nombres', nargs=2, default=['ref', 'met'])
ap.add_argument('--tol', type=float, default=0.01)
a = ap.parse_args()

def load(p):
    d = {}
    for r in csv.DictReader(open(p)):
        d[(r['instancia'], int(r['semilla']))] = r
    return d
R, M = load(a.ref), load(a.met)
keys = sorted(set(R) & set(M))
by = defaultdict(list)
fr = fm = 0; Kr = Km = 0; deltas = []; w = t = l = 0; diffs = []
for k in keys:
    r, m = R[k], M[k]
    okr, okm = r['factible'] == '1', m['factible'] == '1'
    fr += okr; fm += okm
    if not (okr and okm):
        by[k[0]].append(None); continue
    cr, cm = float(r['costo_TC']), float(m['costo_TC'])
    kr, km = int(r['K']), int(m['K'])
    Kr += kr; Km += km
    dlt = (cm - cr) / cr * 100
    deltas.append(dlt); diffs.append(cm - cr)
    s = 'w' if cm < cr - a.tol else ('l' if cm > cr + a.tol else 't')
    w += s == 'w'; t += s == 't'; l += s == 'l'
    by[k[0]].append((cr, cm, kr, km, s))
n1, n2 = a.nombres
L = [f'| instancia | TC medio {n1} | K medio {n1} | TC medio {n2} | K medio {n2} | ΔTC medio (%) | mejor/igual/peor |', '|---|---|---|---|---|---|---|']
for inst in sorted(by):
    v = [x for x in by[inst] if x]
    if not v: L.append(f'| {inst} | — | — | — | — | — | — |'); continue
    mr = sum(x[0] for x in v) / len(v); mm = sum(x[1] for x in v) / len(v)
    kr = sum(x[2] for x in v) / len(v); km = sum(x[3] for x in v) / len(v)
    dd = sum((x[1] - x[0]) / x[0] * 100 for x in v) / len(v)
    L.append(f'| {inst} | {mr:.2f} | {kr:.2f} | {mm:.2f} | {km:.2f} | {dd:+.2f} | {sum(x[4]=="w" for x in v)}/{sum(x[4]=="t" for x in v)}/{sum(x[4]=="l" for x in v)} |')
L.append('')
L.append(f'- Corridas pareadas: {len(keys)}; factibles (juez oficial): {n1} {fr}/{len(keys)}, {n2} {fm}/{len(keys)}.')
L.append(f'- Vehículos totales (pares factibles): {n1} {Kr}, {n2} {Km} (Δ {Km-Kr:+d}).')
if deltas:
    L.append(f'- ΔTC medio por par: {sum(deltas)/len(deltas):+.3f} % (mín {min(deltas):+.2f} %, máx {max(deltas):+.2f} %).')
L.append(f'- {n2} mejor / igual / peor: {w}/{t}/{l}.')
if w + l > 0:
    L.append(f'- Prueba de signos (bilateral, sin empates): p = {binomtest(w, w+l, 0.5).pvalue:.2g}.')
nz = [x for x in diffs if abs(x) > a.tol]
if len(nz) >= 2:
    L.append(f'- Wilcoxon de rangos con signo (bilateral, diferencias de TC sin empates, n = {len(nz)}): p = {wilcoxon(nz).pvalue:.2g}.')
out = '\n'.join(L)
print(out)
if a.md: open(a.md, 'w').write(out + '\n')
