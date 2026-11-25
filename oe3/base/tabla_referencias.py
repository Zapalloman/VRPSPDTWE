"""Combina los resúmenes de las referencias en resultados/tabla_referencias.md."""
import csv, os
B = "/home/user/oe3/base/resultados"
M = [("hma_ld", "HMA-LD"), ("hma_orig_reparado", "HMA orig. + reparación")]
data = {}
for m, _ in M:
    p = os.path.join(B, m, "resumen.csv")
    if os.path.exists(p):
        data[m] = {r["instancia"]: r for r in csv.DictReader(open(p))}
inst = [l.strip() for l in open("/home/user/oe3/base/conjuntos/desarrollo.txt") if l.strip()]
L = ["| instancia | " + " | ".join(f"{n}: fact. | {n}: TC medio | {n}: K medio" for _, n in M) + " |",
     "|---|" + "---|---|---|" * len(M)]
tot = {m: [0, 0] for m, _ in M}
for i in inst:
    c = []
    for m, _ in M:
        r = data.get(m, {}).get(i)
        if r is None:
            c += ["—", "—", "—"]
        else:
            c += [f"{r['factibles']}/{r['corridas']}", r["costo_medio"] or "—", r["K_medio"] or "—"]
            tot[m][0] += int(r["factibles"]); tot[m][1] += int(r["corridas"])
    L.append(f"| {i} | " + " | ".join(c) + " |")
L.append("")
for m, n in M:
    L.append(f"- {n}: {tot[m][0]}/{tot[m][1]} corridas factibles (juez oficial, beta=0.2, rho=0).")
open(os.path.join(B, "tabla_referencias.md"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
