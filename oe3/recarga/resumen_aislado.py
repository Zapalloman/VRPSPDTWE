"""Resume efecto_aislado_b*.json: soluciones factibles por política y costo extra."""
import json, sys
d = json.load(open(sys.argv[1]))
for grupo, filt in (('pequeñas', lambda k: '_21' not in k), ('100 clientes', lambda k: '_21' in k)):
    ks = [k for k in d if filt(k)]
    print(f'## {grupo} ({len(ks)} soluciones)')
    for tag, nom in (('pub', 'publicada (estaciones de HMA)'), ('rep', 'reparación mínima (consumo_carga)'),
                     ('dp', 'etiquetas exactas, misma secuencia'), ('dprev', 'etiquetas exactas, secuencia o inversa')):
        ok = [k for k in ks if d[k][tag]['ok']]
        rinf = sum(d[k][tag]['rutas_inf'] for k in ks)
        print(f'- {nom}: factibles {len(ok)}/{len(ks)}; rutas sin plan factible {rinf}')
    both = [k for k in ks if d[k]['rep']['ok'] and d[k]['dp']['ok']]
    if both:
        dr = sum(d[k]['rep']['cost'] - d[k]['cost_pub'] for k in both)
        dd = sum(d[k]['dp']['cost'] - d[k]['cost_pub'] for k in both)
        better = sum(d[k]['dp']['cost'] < d[k]['rep']['cost'] - 1e-6 for k in both)
        print(f'- en las {len(both)} que ambas resuelven: +distancia total vs publicada: reparación {dr:.2f}, etiquetas {dd:.2f}; etiquetas más baratas en {better}')
    only = [k for k in ks if d[k]['dp']['ok'] and not d[k]['rep']['ok']]
    print(f'- recuperadas solo por etiquetas: {len(only)} {only}')
    onlyrev = [k for k in ks if d[k]['dprev']['ok'] and not d[k]['rep']['ok']]
    print(f'- recuperadas solo por etiquetas (con inversión): {len(onlyrev)}')
    ts = sum(d[k]['t'] for k in ks)
    print(f'- tiempo total Python (4 llamadas por ruta incluidas la reparación): {ts:.1f}s')
