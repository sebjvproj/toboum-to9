"""Sprites originaux 8x16 pour le jeu de bombes TO9 (pixels TO9 : 2 fois plus larges que hauts).
Couleurs 7..15 réservées aux sprites (mêmes dans tous les niveaux) ; 0..6 = décor.
python3 sprites.py  ->  ../apercus/planche_sprites.png"""
import os
DECORS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'graphismes', 'decors')
from PIL import Image, ImageDraw

LV = [round(255 * (v / 15) ** (1 / 2.8)) for v in range(16)]    # rendu TO9 (comme TOetris)
def niveaux(rgb8):
    """couleur voulue (0..255) -> niveaux TO9 (0..15) au rendu le plus proche"""
    return tuple(min(range(16), key=lambda v: abs(LV[v] - c)) for c in rgb8)

# palette des sprites : lettre -> (index TO9, couleur voulue)
SPAL = {
    'k': (7,  (0, 0, 0)),         # contour noir
    'w': (8,  (255, 255, 255)),   # blanc
    'l': (9,  (190, 190, 200)),   # gris clair
    'g': (10, (105, 105, 120)),   # gris foncé
    'y': (11, (255, 215, 0)),     # jaune
    'r': (12, (230, 40, 30)),     # rouge
    'o': (13, (255, 185, 135)),   # peau
    'b': (14, (50, 110, 255)),    # bleu
    'v': (15, (40, 190, 60)),     # vert
}
CODE = {k: v[0] for k, v in SPAL.items()}

S = {}
# ---- Toto, le héros à casquette à hélice ----
S['TOTO_DEBOUT'] = """
yyy.yyy.
...k....
..rrrr..
.rrrrrrr
.oooo...
.okoko..
.oooooo.
..oooo..
..vvvv..
.vbbbbv.
ov.bb.vo
..bbbb..
..bb.bb.
..bb.bb.
.kkk.kkk
........"""
S['TOTO_MARCHE'] = """
.yyy.yyy
...k....
..rrrr..
.rrrrrrr
.oooo...
.okoko..
.oooooo.
..oooo..
..vvvv..
.vbbbbv.
.obbbbo.
..bbbb..
.bb..bb.
bb....bb
kk....kk
........"""
S['TOTO_VOL'] = """
yyyykyyy
...k....
..rrrr..
.rrrrrrr
.oooo...
.okoko..
.oooooo.
o.oooo.o
vvvvvvvv
..bbbb..
..bbbb..
..bbbb..
..bb.bb.
.bb...bb
.kk...kk
........"""
S['TOTO_CHUTE'] = """
....k...
.yyykyyy
..rrrr..
.rrrrrrr
.oooo...
.owowo..
.oooooo.
..okko..
o.vvvv.o
.vbbbbv.
..bbbb..
..bbbb..
.bb..bb.
.bb..bb.
.kk..kk.
........"""
# ---- ennemis ----
S['ROBOT'] = """
...ll...
...kk...
.gllllg.
.lkrrkl.
.llllll.
.lwlwll.
..gggg..
.gllllg.
lglllllg
lglbblgl
.gllllg.
..llll..
..l..l..
..l..l..
.gg..gg.
........"""
S['CHAUVE_SOURIS_1'] = """
k......k
kk....kk
kgk..kgk
kggkkggk
kggggggk
.kgrrgk.
.kggggk.
..kwwk..
...kk...
........
........
........
........
........
........
........"""
S['CHAUVE_SOURIS_2'] = """
........
...kk...
..kggk..
.kgrrgk.
kggggggk
kggkkggk
kgk..kgk
kk....kk
k......k
........
........
........
........
........
........
........"""
S['BOULE'] = """
...kk...
k..kk..k
.k.bb.k.
..bwbb..
.bwbbbb.
kbbbbbbk
kbbbbbbk
.bbbbbb.
..bbbb..
.k.bb.k.
k..kk..k
...kk...
........
........
........
........"""
# ---- objets ----
S['BOMBE'] = """
........
.....k..
....k...
..kkkk..
.kggggk.
kgwwgggk
kgwggggk
kggggggk
kggggggk
kggggggk
.kggggk.
..kkkk..
........
........
........
........"""
S['BOMBE_ALLUMEE'] = """
....ryr.
.....y..
....k...
..kkkk..
.krrrrk.
krwwrrrk
krwrrrrk
krrrrrrk
krrrrrrk
krrrrrrk
.krrrrk.
..kkkk..
........
........
........
........"""
S['ETOILE'] = """
...yy...
...yy...
..yyyy..
yyywyyyy
.yywyyy.
..yyyy..
.yyyyyy.
.yy..yy.
yy....yy
........
........
........
........
........
........
........"""

# ---- étapes d'animation, 4e ennemi et objets ----
S['TOTO_DEBOUT_2'] = """
...yky..
...k....
..rrrr..
.rrrrrrr
.oooo...
.okoko..
.oooooo.
..oooo..
..vvvv..
.vbbbbv.
ov.bb.vo
..bbbb..
..bb.bb.
..bb.bb.
.kkk.kkk
........"""
S['TOTO_MARCHE_2'] = """
..ykyy..
...k....
..rrrr..
.rrrrrrr
.oooo...
.okoko..
.oooooo.
..oooo..
..vvvv..
..vbbv..
..obbo..
..bbbb..
...bb...
...bb...
..kkkk..
........"""
S['TOTO_VOL_2'] = """
.yyykyy.
...k....
..rrrr..
.rrrrrrr
.oooo...
.okoko..
.oooooo.
o.oooo.o
vvvvvvvv
..bbbb..
..bbbb..
..bbbb..
..bb.bb.
.bb...bb
.kk...kk
........"""
S['TOTO_PERDU'] = """
y.....y.
.y.k.y..
..rrrr..
.rrrrrrr
.oooo...
.wkowk..
.oooooo.
..okko..
o.vvvv.o
.vbbbbv.
..bbbb..
..bbbb..
..bb.bb.
.bb...bb
.kk...kk
........"""
S['ROBOT_2'] = """
...rr...
...kk...
.gllllg.
.lkrrkl.
.llllll.
.lwlwll.
..gggg..
.gllllg.
lglllllg
lglbblgl
.gllllg.
..llll..
.l....l.
.l....l.
gg....gg
........"""
S['BOULE_2'] = """
k......k
.k.kk.k.
..kbbk..
..bbwb..
.bbbbwb.
kbbbbbbk
kbbbbbbk
.bbbbbb.
..bbbb..
..kbbk..
.k.kk.k.
k......k
........
........
........
........"""
S['NUAGE_1'] = """
........
..ww....
.wwww.w.
wwwwwwww
wlkwwklw
wwkwwkww
wwwwwwww
.wlkkwl.
..llll..
........
........
........
........
........
........
........"""
S['NUAGE_2'] = """
........
..ww....
.wwww.w.
wwwwwwww
wlkwwklw
wwkwwkww
wwwwwwww
.wlkkwl.
..llll..
...y....
....y...
...y....
........
........
........
........"""
S['BOMBE_ALLUMEE_2'] = """
....y.y.
....ry..
....k...
..kkkk..
.krrrrk.
krwwrrrk
krwrrrrk
krrrrrrk
krrrrrrk
krrrrrrk
.krrrrk.
..kkkk..
........
........
........
........"""
S['ECLAIR'] = """
..kkkk..
.kbbbbk.
kbbbbybk
kbbbyybk
kbbyybbk
kbyyyybk
kbbbyybk
kbbyybbk
kbyybbbk
kbbbbbbk
.kbbbbk.
..kkkk..
........
........
........
........"""
S['GLACON'] = """
.kkkkkk.
kwwllllk
kwlllllk
kllllllk
kllwlllk
kllllllk
kllllwlk
kllllllk
kllllllk
kllllllk
kllllllk
.kkkkkk.
........
........
........
........"""
S['COEUR'] = """
.rr..rr.
rwrrrrrr
rrrrrrrr
rrrrrrrr
.rrrrrr.
..rrrr..
...rr...
........
........
........
........
........
........
........
........
........"""

# sprites sans contour dessiné : on ajoute un contour noir automatique (lisibilité sur tous les décors)
CONTOUR_AUTO = ('TOTO', 'ROBOT', 'CHAUVE', 'BOULE', 'NUAGE', 'ETOILE', 'COEUR')

def contour(g):
    """met en noir chaque pixel transparent qui touche (haut, bas, gauche, droite) un pixel coloré"""
    h, w = len(g), len(g[0]); out = [r[:] for r in g]
    for y in range(h):
        for x in range(w):
            if g[y][x] == 0 and any(0 <= y + dy < h and 0 <= x + dx < w and g[y + dy][x + dx] not in (0, CODE['k'])
                                    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                out[y][x] = CODE['k']
    return out

def grid(name, auto=True):
    rows = [r for r in S[name].strip('\n').split('\n')]
    assert len(rows) == 16 and all(len(r) == 8 for r in rows), (name, [len(r) for r in rows])
    g = [[CODE.get(ch, 0) for ch in r] for r in rows]
    return contour(g) if auto and name.startswith(CONTOUR_AUTO) else g

def rgb(levels): return tuple(LV[c] for c in levels)
SPRITE_LV = {i: niveaux(c) for i, c in SPAL.values()}              # niveaux TO9 à programmer
SPRITE_RGB = {i: rgb(lv) for i, lv in SPRITE_LV.items()}           # rendu obtenu

ORDRE = ['TOTO_DEBOUT', 'TOTO_DEBOUT_2', 'TOTO_MARCHE', 'TOTO_MARCHE_2', 'TOTO_VOL', 'TOTO_VOL_2',
         'TOTO_CHUTE', 'TOTO_PERDU', 'ROBOT', 'ROBOT_2', 'CHAUVE_SOURIS_1', 'CHAUVE_SOURIS_2',
         'BOULE', 'BOULE_2', 'NUAGE_1', 'NUAGE_2', 'BOMBE', 'BOMBE_ALLUMEE', 'BOMBE_ALLUMEE_2',
         'ETOILE', 'ECLAIR', 'GLACON', 'COEUR']

def decor_pixels(nom):
    """décor converti (graphismes/decors/<nom>_to9.bin + palette) -> (pixels[200][160], rvb)"""
    import json
    d = open(os.path.join(DECORS, nom + '_to9.bin'), 'rb').read()
    lv = json.load(open(os.path.join(DECORS, nom + '_palette.json')))['niveaux_to9']
    px = [[0] * 160 for _ in range(200)]
    for y in range(200):
        for g in range(40):
            a, b = d[y * 40 + g], d[8000 + y * 40 + g]
            px[y][4 * g:4 * g + 4] = [a >> 4, a & 15, b >> 4, b & 15]
    return px, [rgb(tuple(t)) for t in lv]

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    assert set(ORDRE) == set(S), set(S) ^ set(ORDRE)
    decors = [n for n in ('egypte', 'rome', 'moscou', 'paris', 'mont_st_michel')
              if os.path.exists(os.path.join(DECORS, n + '_to9.bin'))]
    fonds = [decor_pixels(n) for n in decors] or [None]
    PX, PY = 6, 3                                                    # pixel TO9 = 6x3 (2:1)
    cw, ch = 8 * PX + 6, 16 * PY + 6
    im = Image.new('RGB', (110 + len(ORDRE) * cw, 16 + len(fonds) * ch), (25, 25, 25))
    dr = ImageDraw.Draw(im)
    for j, fd in enumerate(fonds):
        if decors: dr.text((4, 16 + j * ch + 20), decors[j], fill=(200, 200, 200))
        for i, n in enumerate(ORDRE):
            x0, y0 = 110 + i * cw, 16 + j * ch
            for y in range(16):                                      # fond : un morceau du décor
                for x in range(8):
                    if fd:
                        px, pal = fd; sx, sy = 12 + (i * 5) % 100, 30 + (j * 37 + i * 11) % 140
                        c = pal[px[sy + y][sx + x]]
                    else: c = (60, 60, 60)
                    dr.rectangle([x0 + x * PX, y0 + y * PY, x0 + x * PX + PX - 1, y0 + y * PY + PY - 1], fill=c)
            for y, r in enumerate(grid(n)):
                for x, v in enumerate(r):
                    if v: dr.rectangle([x0 + x * PX, y0 + y * PY, x0 + x * PX + PX - 1, y0 + y * PY + PY - 1],
                                       fill=SPRITE_RGB[v])
            if j == 0: dr.text((x0, 2), str(i + 1), fill=(255, 255, 0))
    im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(os.path.join('..', 'apercus', 'planche_sprites.png'))
    print(len(ORDRE), 'sprites sur', len(fonds), 'décors -> apercus/planche_sprites.png')
    for i, n in enumerate(ORDRE): print(f'{i + 1:2d} {n}')
