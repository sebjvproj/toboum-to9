"""Convertit une image quelconque en décor TO9 pour le jeu de bombes.

    python3 convertir_decor.py image.png [--nom egypte] [--couleurs 6] [--tramage bayer|fs|aucun]
                               [--force 25] [--palette kmeans|mediane] [--taille] [--plein-ecran]

Aire de jeu : 116 x 184 pixels TO9 (x 8..123, y 8..191) ; les pixels TO9 sont 1,67 fois plus
larges que hauts sur un écran 4:3, l'image est donc recadrée au format physique puis réduite.
Couleurs : 0 = noir, 1..N = décor (choisies automatiquement), 7..15 = sprites (sprites.py).
Sorties dans graphismes/decors/ : <nom>_apercu.png (écran TO9 simulé avec sprites), <nom>_to9.bin
(écran brut : banque A puis banque B, 2 x 8000 octets), <nom>_palette.json (niveaux TO9)."""
import argparse, json, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sprites as SP

X0, Y0, W, H = 8, 8, 116, 184               # aire de jeu dans l'écran 160x200
PIXEL_ASPECT = (4 / 160) / (3 / 200)        # largeur / hauteur d'un pixel TO9 sur écran 4:3
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

def recadre(im):
    """recadrage centré au format physique de l'aire de jeu, puis réduction à 116x184"""
    target = W * PIXEL_ASPECT / H
    w, h = im.size
    if w / h > target: nw = round(h * target); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else: nh = round(w / target); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return im.resize((W, H), Image.LANCZOS)

def kmeans_couleurs(small, n, fixes=()):
    """couleurs bien distinctes : départ par les couleurs les plus éloignées (parmi celles qui
    couvrent au moins 0,3 % de l'image, pour ignorer les pixels isolés), puis k-moyennes"""
    px = list(small.getdata()) if not hasattr(small, 'get_flattened_data') else list(small.get_flattened_data())
    hist = {}
    for c in px:
        k = tuple(v >> 3 for v in c); hist[k] = hist.get(k, 0) + 1
    seuil = len(px) * 0.003
    cand = [tuple(v * 8 + 4 for v in k) for k, cnt in hist.items() if cnt >= seuil]
    fixes = list(fixes); nf = len(fixes)
    moy = tuple(sum(c[i] for c in px) / len(px) for i in range(3))
    centres = fixes[:] if fixes else [min(cand, key=lambda c: dist(c, moy))]
    while len(centres) < nf + n:                  # la couleur la plus mal représentée d'abord
        centres.append(max(cand, key=lambda c: min(dist(c, m) for m in centres)))
    for _ in range(10):                           # k-moyennes ; les couleurs fixes ne bougent pas
        acc = [[0, 0, 0, 0] for _ in centres]
        for c, cnt in hist.items():
            c = tuple(v * 8 + 4 for v in c)
            i = min(range(len(centres)), key=lambda j: dist(c, centres[j]))
            for k in range(3): acc[i][k] += c[k] * cnt
            acc[i][3] += cnt
        centres = [centres[i] if i < nf or not a[3] else tuple(a[k] / a[3] for k in range(3))
                   for i, a in enumerate(acc)]
    return [tuple(round(v) for v in c) for c in centres[nf:]]

def palette_decor(small, n, methode='kmeans', fixes=()):
    """n couleurs représentatives, ramenées aux niveaux TO9 ; le noir est l'index 0"""
    if methode == 'mediane':
        raw = small.quantize(colors=n, method=Image.Quantize.MEDIANCUT).getpalette()[:3 * n]
        cols = [tuple(raw[3 * i:3 * i + 3]) for i in range(n)]
    else:
        cols = kmeans_couleurs(small, n, fixes)
    lv = [to9_proche(c) for c in cols]
    lv.sort(key=lambda t: sum(SP.LV[c] for c in t))       # du plus sombre au plus clair
    return [(0, 0, 0)] + lv                                 # index 0 = noir

def lab(c):
    """sRGB 0..255 -> CIELAB (pour comparer les couleurs comme l'œil)"""
    def lin(v):
        v /= 255; return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in c)
    x, y, z = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.9505, 0.2126 * r + 0.7152 * g + 0.0722 * b, \
              (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.089
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))

_TO9 = None
def to9_proche(c):
    """la couleur TO9 (parmi 4096) la plus proche à l'œil -> niveaux (r, v, b)"""
    global _TO9
    if _TO9 is None:
        _TO9 = [((r, g, b), lab(SP.rgb((r, g, b)))) for r in range(16) for g in range(16) for b in range(16)]
    L = lab(c)
    # (le TO9 n'a pas de tons sombres peu saturés : son niveau 1 rend déjà ~40 % de luminosité)
    return min(_TO9, key=lambda t: sum((t[1][i] - L[i]) ** 2 for i in range(3)))[0]

def dist(a, b):                                             # distance pondérée (sensibilité de l'œil)
    return 3 * (a[0] - b[0]) ** 2 + 4 * (a[1] - b[1]) ** 2 + 2 * (a[2] - b[2]) ** 2

def tramer(small, rgbpal, mode, force):
    px = small.load(); out = [[0] * W for _ in range(H)]
    if mode == 'fs':
        pim = Image.new('P', (1, 1)); flat = sum((list(c) for c in rgbpal), [])
        pim.putpalette(flat + flat[:3] * (256 - len(rgbpal)))
        q = small.quantize(palette=pim, dither=Image.Dither.FLOYDSTEINBERG).load()
        return [[min(q[x, y], len(rgbpal) - 1) for x in range(W)] for y in range(H)]  # (index 0..15)
    palab = [lab(c) for c in rgbpal]
    cache = {}
    for y in range(H):
        for x in range(W):
            c = px[x, y]
            if mode == 'bayer':
                t = ((BAYER[y % 4][x % 4] + 0.5) / 16 - 0.5) * force
                c = tuple(min(255, max(0, round(v + t))) for v in c)
            if c not in cache:                      # couleur la plus proche à l'œil
                L = lab(c)
                cache[c] = min(range(len(rgbpal)), key=lambda i: sum((palab[i][k] - L[k]) ** 2 for k in range(3)))
            out[y][x] = cache[c]
    return out

def ecran(decor):
    """écran 160x200 : noir, cadre gris (couleur 9 des sprites), décor, panneau vide"""
    if (W, H) == (160, 200): return decor                   # plein écran (écran titre)
    scr = [[0] * 160 for _ in range(200)]
    for y in range(Y0 - 3, Y0 + H + 3):
        for x in range(X0 - 3, X0 + W + 3):
            if not (X0 - 1 <= x < X0 + W + 1 and Y0 - 1 <= y < Y0 + H + 1): scr[y][x] = 9
    for y in range(H):
        scr[Y0 + y][X0:X0 + W] = decor[y]
    return scr

def pose(scr, name, x, y):
    for j, r in enumerate(SP.grid(name)):
        for i, v in enumerate(r):
            if v: scr[y + j][x + i] = v

def banques(scr):
    A = bytearray(); B = bytearray()
    for y in range(200):
        for g in range(40):
            A.append(scr[y][4 * g] << 4 | scr[y][4 * g + 1]); B.append(scr[y][4 * g + 2] << 4 | scr[y][4 * g + 3])
    return bytes(A), bytes(B)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('image'); ap.add_argument('--nom')
    ap.add_argument('--couleurs', type=int, default=6, help='couleurs du décor, noir en plus (6 au plus)')
    ap.add_argument('--tramage', choices=('bayer', 'fs', 'aucun'), default='bayer')
    ap.add_argument('--force', type=float, default=25, help='intensité du tramage bayer (0-120)')
    ap.add_argument('--palette', choices=('kmeans', 'mediane'), default='kmeans',
                    help='choix des couleurs : kmeans garde les teintes distinctes, mediane les grandes surfaces')
    ap.add_argument('--sans-couleurs-sprites', action='store_true',
                    help="le décor n'utilise pas les couleurs 7..15 des sprites")
    ap.add_argument('--taille', action='store_true', help='mesure la taille compressée (lent)')
    ap.add_argument('--plein-ecran', action='store_true', help='image 160x200 sans cadre (écran titre)')
    a = ap.parse_args()
    if a.plein_ecran:
        global X0, Y0, W, H
        X0, Y0, W, H = 0, 0, 160, 200
    assert 1 <= a.couleurs <= 6, 'le décor a 6 couleurs au plus (7..15 = sprites)'
    nom = a.nom or os.path.splitext(os.path.basename(a.image))[0]
    os.makedirs(os.path.join(HERE, '..', 'graphismes', 'decors'), exist_ok=True)

    small = recadre(Image.open(a.image).convert('RGB'))
    sprite_rgb = [SP.SPRITE_RGB[i] for i in range(7, 16)]
    partage = not a.sans_couleurs_sprites
    lv = palette_decor(small, a.couleurs, a.palette, [(0, 0, 0)] + sprite_rgb if partage else ())
    rgbpal = [SP.rgb(t) for t in lv]
    # couleurs utilisables par le décor : 0..6, plus 7..15 (sprites) si partagées
    tpal = rgbpal + [(0, 0, 0)] * (7 - len(rgbpal)) + (sprite_rgb if partage else [])
    decor = tramer(small, tpal, a.tramage, a.force)
    scr = ecran(decor)

    # palette complète 16 couleurs : 0..6 décor (complétée), 7..15 sprites
    full_lv = lv + [(0, 0, 0)] * (7 - len(lv)) + [SP.SPRITE_LV[i] for i in range(7, 16)]
    full_rgb = [SP.rgb(t) for t in full_lv]
    base = os.path.join(HERE, '..', 'graphismes', 'decors', nom)
    A, B = banques(scr)
    open(base + '_to9.bin', 'wb').write(A + B)
    json.dump({'niveaux_to9': full_lv, 'couleurs_decor': a.couleurs, 'tramage': a.tramage,
               'couleurs_sprites_partagees': partage},
              open(base + '_palette.json', 'w'), indent=1)

    # aperçu : écran TO9 simulé (4:3) avec quelques sprites pour juger la lisibilité
    demo = [r[:] for r in scr]
    for k, (n, x, y) in enumerate([('BOMBE', 14, 12), ('BOMBE', 26, 12), ('BOMBE', 38, 12),
                                   ('BOMBE_ALLUMEE', 98, 60), ('BOMBE', 110, 60),
                                   ('TOTO_VOL', 60, 96), ('ROBOT', 30, 170), ('CHAUVE_SOURIS_1', 92, 130),
                                   ('BOULE', 20, 90), ('NUAGE_1', 44, 150), ('ETOILE', 80, 40)]):
        pose(demo, n, x, y)
    ap_im = Image.new('RGB', (160, 200)); ap_im.putdata([full_rgb[c] for r in demo for c in r])
    src = Image.open(a.image).convert('RGB'); src.thumbnail((480, 480))
    out = Image.new('RGB', (640 + 20 + src.width, 480), (25, 25, 25))
    out.paste(ap_im.resize((640, 480), Image.NEAREST), (0, 0)); out.paste(src, (660, 0))
    out.save(base + '_apercu.png')

    msg = f'{nom} : {a.couleurs} couleurs + noir ({a.palette}), tramage {a.tramage}'
    if a.taille:
        import lz as LZ
        msg += f', compressé {len(LZ.lz(A)) + len(LZ.lz(B))} octets'
    print(msg, '->', os.path.relpath(base + '_apercu.png'))

if __name__ == '__main__':
    main()
