"""Compara dos corridas.csv de bench.py (mismas instancias y semillas): por instancia,
factibles, costo medio, mejor costo, K medio y tiempo medio; y totales.
Uso: python3 comparar.py A/corridas.csv B/corridas.csv [etiquetaA etiquetaB]"""
import csv, sys, statistics as st
from collections import defaultdict
def load(p):
    d = defaultdict(dict)
    for r in csv.DictReader(open(p)):
        d[r["instancia"]][r["semilla"]] = r
    return d
A, B = load(sys.argv[1]), load(sys.argv[2])
la, lb = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ("A", "B")
print(f"| instancia | fact {la} | fact {lb} | TC medio {la} | TC medio {lb} | mejor {la} | mejor {lb} | t medio {la} (s) | t medio {lb} (s) |")
print("|---|---|---|---|---|---|---|---|---|")
win = lose = tie = 0; ta = tb = 0.0; ra = []
for inst in A:
    if inst not in B: continue
    seeds = sorted(set(A[inst]) & set(B[inst]))
    if not seeds: continue
    fa = [A[inst][s] for s in seeds]; fb = [B[inst][s] for s in seeds]
    ca = [float(r["costo_TC"]) for r in fa if r["factible"] == "1"]
    cb = [float(r["costo_TC"]) for r in fb if r["factible"] == "1"]
    ma = st.mean(ca) if ca else float("nan"); mb = st.mean(cb) if cb else float("nan")
    tma = st.mean(float(r["tiempo_pared"]) for r in fa); tmb = st.mean(float(r["tiempo_pared"]) for r in fb)
    ta += tma; tb += tmb
    for s in seeds:
        x, y = A[inst][s], B[inst][s]
        cx = float(x["costo_TC"]) if x["factible"] == "1" else float("inf")
        cy = float(y["costo_TC"]) if y["factible"] == "1" else float("inf")
        if cx < cy - 0.01: win += 1
        elif cy < cx - 0.01: lose += 1
        else: tie += 1
        if cx < float("inf") and cy < float("inf"): ra.append((cx - cy) / cy * 100)
    print(f"| {inst} | {len(ca)}/{len(seeds)} | {len(cb)}/{len(seeds)} | {ma:.2f} | {mb:.2f} | {min(ca) if ca else float('nan'):.2f} | {min(cb) if cb else float('nan'):.2f} | {tma:.1f} | {tmb:.1f} |")
print(f"\nPor corrida (misma instancia y semilla): {la} mejor en {win}, {lb} mejor en {lose}, empates {tie}.")
if ra: print(f"Diferencia relativa media de TC ({la} − {lb})/{lb}: {st.mean(ra):+.3f} %  (mín {min(ra):+.3f} %, máx {max(ra):+.3f} %)")
print(f"Tiempo medio total: {la} {ta:.1f} s, {lb} {tb:.1f} s (razón {tb/ta if ta else float('nan'):.2f})")
