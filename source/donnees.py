"""Données du jeu TOboum -> toboum_data.asm (matériel original uniquement)
Décor + plateformes + textes du panneau (sans les bombes, posées par le programme),
tables des plateformes et des bombes, chiffres, sprites compilés, routines de copie.
    python3 donnees.py [décor]      (égypte par défaut ; voir graphismes/decors)"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'outils'))
import sprites as SP                               # sprites 8x16 et palette (couleurs 7..15)
import lz as LZ                                    # compression des écrans
from police import F                               # police 3x5
DECORS = os.path.join(HERE, '..', 'graphismes', 'decors')

TOUS_DECORS = ['egypte', 'rome', 'moscou', 'paris', 'mont_st_michel']   # un par niveau, en boucle
DECOR = sys.argv[1] if len(sys.argv) > 1 else 'egypte'                  # décor du niveau 1
BUF_ROWB = 29                                      # octets par ligne et par banque dans la copie du décor
BLANC, JAUNE = SP.CODE['w'], SP.CODE['y']

# planches (une par décor, dans l'ordre des niveaux) : plateformes (x, y, largeur en pixels),
# 18 bombes (x, y) dans l'ordre d'allumage, pièce éclair (x, y), départ de Toto (x, y) ;
# x multiple de 4 pour les bombes et la pièce ; aire de jeu : sprites en x 8..116, y 8..176
def rangee(x0, y, n, dx=12): return [(x0 + i * dx, y) for i in range(n)]
def colonne(x, y0, n, dy=30): return [(x, y0 + i * dy) for i in range(n)]
PLANCHES = [
    dict(nom='pyramides',                          # la planche d'origine
         plats=[(20, 60, 32), (72, 104, 36), (24, 150, 32)],
         bombes=rangee(12, 12, 3) + rangee(84, 12, 3) + colonne(12, 80, 3, 20) + colonne(112, 70, 3, 20)
                + [(24, 44), (36, 44), (76, 88), (92, 88), (28, 134), (44, 134)],
         piece=(60, 76), depart=(60, 176)),
    dict(nom='deux corniches',
         plats=[(12, 72, 28), (88, 72, 28), (48, 124, 32)],
         bombes=rangee(44, 20, 3) + [(12, 56), (24, 56), (92, 56), (104, 56)] + rangee(52, 108, 3)
                + [(8, 100), (8, 130), (112, 100), (112, 130)] + [(24, 176), (40, 176), (84, 176), (100, 176)],
         piece=(60, 84), depart=(60, 176)),
    dict(nom='escalier',
         plats=[(12, 150, 28), (44, 110, 28), (76, 70, 28)],
         bombes=rangee(12, 24, 3) + [(16, 134), (28, 134), (48, 94), (60, 94), (80, 54), (92, 54)]
                + colonne(112, 90, 3) + [(88, 24), (100, 24), (24, 176), (88, 176), (100, 176), (84, 110)],
         piece=(20, 90), depart=(60, 176)),
    dict(nom='tour',
         plats=[(48, 150, 32), (48, 100, 32), (48, 50, 32)],
         bombes=colonne(12, 30, 5) + colonne(108, 30, 5) + [(52, 134), (68, 134), (52, 84), (68, 84), (52, 34), (68, 34)]
                + [(24, 176), (96, 176)],
         piece=(60, 112), depart=(60, 176)),
    dict(nom='terrasses',
         plats=[(8, 80, 40), (76, 80, 40), (40, 136, 40)],
         bombes=rangee(16, 20, 3) + rangee(76, 20, 3) + rangee(12, 64, 3) + rangee(80, 64, 3)
                + rangee(48, 120, 3) + [(16, 176), (100, 176), (60, 40)],
         piece=(60, 92), depart=(60, 176)),
]
NBOMB = 18

def verifie(pl):
    """une planche est-elle cohérente ? (bornes, chevauchements, départ libre)"""
    def croise(a, b):
        return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    plats = [(x, y, w, 4) for x, y, w in pl['plats']]
    objets = [(x, y, 8, 16) for x, y in pl['bombes'] + [pl['piece']]]
    assert len(pl['bombes']) == NBOMB, (pl['nom'], len(pl['bombes']))
    for x, y, w, h in plats: assert 8 <= x and x + w <= 124 and 24 <= y <= 180, (pl['nom'], 'plateforme', x, y)
    for i, o in enumerate(objets):
        assert o[0] % 4 == 0 and 8 <= o[0] <= 116 and 8 <= o[1] <= 176, (pl['nom'], 'objet hors limites', o)
        for p in plats: assert not croise(o, p), (pl['nom'], 'objet dans une plateforme', o, p)
        for o2 in objets[i + 1:]: assert not croise(o, o2), (pl['nom'], 'objets qui se chevauchent', o, o2)
    d = (pl['depart'][0], pl['depart'][1], 8, 16)
    for o in objets: assert not croise(d, (o[0] - 4, o[1], 16, 16)), (pl['nom'], 'départ trop près d\'un objet', o)

def charge_decor(nom):
    """décor converti par outils/convertir_decor.py -> (pixels[200][160], niveaux TO9 de la palette)"""
    d = open(os.path.join(DECORS, nom + '_to9.bin'), 'rb').read()
    lv = json.load(open(os.path.join(DECORS, nom + '_palette.json')))['niveaux_to9']
    px = [[0] * 160 for _ in range(200)]
    for y in range(200):
        for g in range(40):
            a, b = d[y * 40 + g], d[8000 + y * 40 + g]
            px[y][4 * g:4 * g + 4] = [a >> 4, a & 15, b >> 4, b & 15]
    return px, lv

def plateforme(px, x, y, w):
    """plateforme aux couleurs des sprites : blanc, gris clair x2, noir"""
    for i in range(w):
        for j, c in enumerate((SP.CODE['w'], SP.CODE['l'], SP.CODE['l'], SP.CODE['k'])):
            px[y + j][x + i] = c

def texte(px, x, y, t, c):
    for ch in t:
        g = F.get(ch, F[' '])
        for r in range(5):
            for k in range(3):
                if g[r * 3 + k] == '1':
                    px[y + 2 * r][x + k] = c; px[y + 2 * r + 1][x + k] = c
        x += 4

def centre(t): return (160 - (4 * len(t) - 1)) // 2

# écran titre : image plein écran (graphismes/decors/titre, convertie avec --plein-ecran),
# logo, sprites, bandeau de textes ; le record est écrit par le jeu en (paire TRECP, ligne TRECY)
TRECP, TRECY = 35, 158
def ecran_titre():
    px, lv = charge_decor('titre')
    K, W, Y, R = SP.CODE['k'], BLANC, JAUNE, SP.CODE['r']
    for y in range(140, 200): px[y] = [0] * 160                  # bandeau noir
    for x in range(160): px[140][x] = SP.CODE['g']
    # logo : lettres 5x5 agrandies (4 x 8), contour noir, ombre rouge, dégradé jaune -> orange
    LOGO = {'T': '11111 00100 00100 00100 00100', 'O': '01110 10001 10001 10001 01110',
            'B': '11110 10001 11110 10001 11110', 'U': '10001 10001 10001 10001 01110',
            'M': '10001 11011 10101 10001 10001'}
    mot, sx, sy = 'TOBOUM', 4, 8
    x0, y0 = (160 - (len(mot) * 6 - 1) * sx) // 2, 16
    plein = set()
    for n, ch in enumerate(mot):
        for r, ligne in enumerate(LOGO[ch].split()):
            for k, v in enumerate(ligne):
                if v == '1':
                    plein |= {(y0 + r * sy + j, x0 + (6 * n + k) * sx + i) for j in range(sy) for i in range(sx)}
    ombre = {(y + 3, x + 2) for y, x in plein}
    for y, x in {(y + dy, x + dx) for y, x in plein | ombre for dy in (-1, 0, 1) for dx in (-1, 0, 1)}: px[y][x] = K
    for y, x in ombre: px[y][x] = R
    for y, x in plein: px[y][x] = W if y == y0 else Y if y - y0 < 3 * sy else SP.CODE['o']
    # Toto (x2) au milieu des bombes
    def pose(nom, x, y, z=1):
        for j, r in enumerate(SP.grid(nom)):
            for i, v in enumerate(r):
                if v:
                    for a in range(z):
                        for b in range(z): px[y + z * j + a][x + z * i + b] = v
    pose('TOTO_VOL', 72, 80, 2)
    for nom, x, y in (('BOMBE', 24, 84), ('BOMBE', 40, 104), ('BOMBE_ALLUMEE', 108, 90), ('BOMBE', 128, 110)):
        pose(nom, x, y)
    texte(px, 2 * TRECP, 146, 'RECORD', Y)
    for t, y, c in (('APPUIE SUR UNE TOUCHE', 174, W), ('FLECHES : BOUGER - ESPACE : SAUTER', 187, SP.CODE['l'])):
        texte(px, centre(t), y, t, c)
    return px, lv

# sprites compilés : chaque image devient 4 routines (2 banques x 2 moitiés de 8 lignes)
# X = adresse écran de la 1re paire de la banque ; X est rendu intact
def compile_moitie(label, g, pairs, lignes, stride=40):
    code = [label]
    base = lignes[0]                  # X pointe sur la ligne 0 du sprite
    dx = 0                            # décalage courant de X (en octets)
    for k, r in enumerate(lignes):
        if k % 4 == 0:                # X avancé toutes les 4 lignes : décalages < 128
            cible = r * stride
            if cible != dx: code.append(f"        LEAX    {cible - dx},X"); dx = cible
        off = r * stride - dx
        octets = []
        for p in pairs:
            a, b = g[r][2 * p], g[r][2 * p + 1]
            m = (0 if a else 0xF0) | (0 if b else 0x0F); d = a << 4 | b
            octets.append((m, d))
        (m0, d0), (m1, d1) = octets
        if m0 == 0xFF and m1 == 0xFF: continue
        if m0 == 0 and m1 == 0:                               # 2 octets opaques
            code += [f"        LDD     #${d0:02X}{d1:02X}", f"        STD     {off},X"]
        elif m0 != 0xFF and m1 != 0xFF:                       # 2 octets, lecture nécessaire
            code.append(f"        LDD     {off},X")
            code += ([f"        LDA     #${d0:02X}"] if m0 == 0 else [f"        ANDA    #${m0:02X}", f"        ORA     #${d0:02X}"])
            code += ([f"        LDB     #${d1:02X}"] if m1 == 0 else [f"        ANDB    #${m1:02X}", f"        ORB     #${d1:02X}"])
            code.append(f"        STD     {off},X")
        else:                                                 # un seul octet
            o, (m, d) = (off, (m0, d0)) if m1 == 0xFF else (off + 1, (m1, d1))
            if m == 0: code += [f"        LDA     #${d:02X}", f"        STA     {o},X"]
            else: code += [f"        LDA     {o},X", f"        ANDA    #${m:02X}", f"        ORA     #${d:02X}", f"        STA     {o},X"]
    if dx: code.append(f"        LEAX    {-dx},X")
    code.append("        RTS")
    return code

def compile_sprite(lab, g, stride=40):
    """sprite 8x16 -> descripteur (4 adresses) + 4 routines compilées
    (stride = octets par ligne : 40 pour l'écran, 29 pour la copie du décor)"""
    out = [f"{lab}  FDB {lab}_1H,{lab}_1B,{lab}_2H,{lab}_2B"]
    for suf, pairs in (('1', (0, 2)), ('2', (1, 3))):
        out += compile_moitie(f"{lab}_{suf}H", g, pairs, range(0, 8), stride)
        out += compile_moitie(f"{lab}_{suf}B", g, pairs, range(8, 16), stride)
    return out

def miroir(g): return [list(reversed(r)) for r in g]

if __name__ == '__main__':
    os.chdir(HERE)
    def compose(nom, pl):
        """décor + plateformes de la planche + textes du panneau -> (pixels, palette, LZ A, LZ B)"""
        if pl is None: px, lv = ecran_titre()
        else:
            px, lv = charge_decor(nom)
            for p in pl['plats']: plateforme(px, *p)
            for t, y in (('SCORE', 12), ('RECORD', 50), ('VIES', 90), ('NIVEAU', 130)):
                texte(px, 131, y, t, JAUNE)
        pal = bytearray()
        for r, g, b in lv: pal += bytes([(g << 4) | r, b])
        A = bytearray(); B = bytearray()
        for y in range(200):
            for k in range(40):
                A.append(px[y][4 * k] << 4 | px[y][4 * k + 1]); B.append(px[y][4 * k + 2] << 4 | px[y][4 * k + 3])
        ca, cb = LZ.lz(bytes(A)), LZ.lz(bytes(B))
        assert LZ.unlz(ca, 8000) == bytes(A) and LZ.unlz(cb, 8000) == bytes(B)
        print(f'décor {nom} : {len(ca) + len(cb)} octets compressés')
        return px, bytes(pal), ca, cb
    out = ["* Généré par donnees.py - ne pas éditer"]
    def db(label, data, per=16):
        if label: out.append(label)
        for i in range(0, len(data), per):
            out.append("        FCB " + ",".join(f"${b:02X}" for b in data[i:i + per]))
    # tous les décors sont sur la disquette (DECORS.DAT), un par niveau, dans cet ordre
    ORDRE = [DECOR] + [n for n in TOUS_DECORS if n != DECOR]
    decors_px = {}
    # palette de secours (si la disquette ne se lit pas) : fond noir, couleurs des sprites
    pal = bytearray(14)
    for i in range(7, 16):
        r, g, b = SP.SPRITE_LV[i]; pal += bytes([(g << 4) | r, b])
    db("PALSECOURS", pal, 8)
    # sur la disquette : par décor, palette (32) + position de la banque B (2) + LZ A + LZ B,
    # à partir d'un début de secteur ; DECTAB = (1er secteur, nombre de secteurs) par décor
    dat = bytearray(); tab = []
    for k, nom in enumerate(ORDRE + ['titre']):                  # l'écran titre en dernier
        pl = PLANCHES[k] if k < len(ORDRE) else None
        if pl: verifie(pl)
        pxd, pal, ca, cb = compose(nom, pl); decors_px[nom] = pxd
        blob = pal + (34 + len(ca)).to_bytes(2, 'big') + ca + cb
        blob += bytes(-len(blob) % 256)
        tab += [len(dat) // 256, len(blob) // 256]; dat += blob
    assert len(dat) // 256 < 256 and max(tab[1::2]) * 256 <= 10672, 'un décor doit tenir dans la copie de l\'aire de jeu'
    open('DECORS.DAT', 'wb').write(dat)
    out.append(f"NDECOR  EQU     {len(ORDRE)}              ; (+ l'écran titre, bloc n° NDECOR)")
    out.append(f"TRECP   EQU     {TRECP}              ; record sur l'écran titre")
    out.append(f"TRECY   EQU     {TRECY}")
    out.append("DATTRK  EQU     21              ; DECORS.DAT commence piste 21 secteur 1 (make_fd.py)")
    out.append("* décors des niveaux 1, 2, 3... : " + ", ".join(ORDRE))
    db("DECTAB", tab, 8)
    # plateformes : paire de début, paire de fin (exclue), ligne du dessus
    # planches : plateformes (nombre, puis paire début, paire fin exclue, ligne du dessus),
    # bombes + pièce éclair (paire, ligne), départ (paire, ligne) ; LAYTAB : 6 octets par planche
    out.append(f"NBOMB   EQU     {NBOMB}")
    for k, pl in enumerate(PLANCHES):
        out.append(f"* planche {k + 1} : {pl['nom']}")
        db(f"LAY{k}_PLATS", [len(pl['plats'])] + sum([[x // 2, (x + w) // 2, y] for x, y, w in pl['plats']], []), 13)
        db(f"LAY{k}_BOMBS", sum([[x // 2, y] for x, y in pl['bombes'] + [pl['piece']]], []), 12)
    out.append("LAYTAB")
    for k, pl in enumerate(PLANCHES):
        out.append(f"        FDB     LAY{k}_PLATS,LAY{k}_BOMBS")
        out.append(f"        FCB     {pl['depart'][0] // 2},{pl['depart'][1]}")
    # chiffres 3x5 : une ligne = 3 bits (bit 2 = pixel de gauche)
    db("DIGITS", [int(F[str(d)][r * 3:r * 3 + 3], 2) for d in range(10) for r in range(5)], 15)
    # sprites compilés
    SPR = [('TOTO_M1D', SP.grid('TOTO_MARCHE')), ('TOTO_M2D', SP.grid('TOTO_MARCHE_2')),
           ('TOTO_M1G', miroir(SP.grid('TOTO_MARCHE'))), ('TOTO_M2G', miroir(SP.grid('TOTO_MARCHE_2'))),
           ('TOTO_V1D', SP.grid('TOTO_VOL')), ('TOTO_V2D', SP.grid('TOTO_VOL_2')),
           ('TOTO_V1G', miroir(SP.grid('TOTO_VOL'))), ('TOTO_V2G', miroir(SP.grid('TOTO_VOL_2'))),
           ('TOTO_CH', SP.grid('TOTO_CHUTE')), ('TOTO_PERDU', SP.grid('TOTO_PERDU')),
           ('ROBOT_1', SP.grid('ROBOT')), ('ROBOT_2', SP.grid('ROBOT_2')),
           ('CHAUVE_1', SP.grid('CHAUVE_SOURIS_1')), ('CHAUVE_2', SP.grid('CHAUVE_SOURIS_2')),
           ('BOULE_1', SP.grid('BOULE')), ('BOULE_2', SP.grid('BOULE_2')),
           ('NUAGE_1', SP.grid('NUAGE_1')), ('NUAGE_2', SP.grid('NUAGE_2')),
           ('BOMBE', SP.grid('BOMBE')), ('BOMBE_AL', SP.grid('BOMBE_ALLUMEE'))]
    for name, g in SPR: out += compile_sprite('SPR_' + name, g)
    # bombes aussi compilées pour la copie du décor (29 octets par ligne)
    out += compile_sprite('BUF_BOMBE', SP.grid('BOMBE'), BUF_ROWB)
    out += compile_sprite('BUF_BOMBE_AL', SP.grid('BOMBE_ALLUMEE'), BUF_ROWB)
    out += compile_sprite('SPR_ECLAIR', SP.grid('ECLAIR'))                  # pièce éclair (elle bouge)
    out += compile_sprite('SPR_GLACON', SP.grid('GLACON'))                  # ennemi gelé
    # images des ennemis par type (1 robot, 2 chauve-souris, 3 boule, 4 nuage)
    out.append("TYPIMG  FDB     SPR_ROBOT_1,SPR_ROBOT_2,SPR_CHAUVE_1,SPR_CHAUVE_2")
    out.append("        FDB     SPR_BOULE_1,SPR_BOULE_2,SPR_NUAGE_1,SPR_NUAGE_2")
    # copies 2 octets x 16 lignes entre écran (X, 40 octets/ligne) et copie du décor (Y, 29)
    out.append("* copie du décor (Y) -> écran (X)")
    out.append("ER16")
    for r in range(16): out += [f"        LDD     {r * BUF_ROWB},Y", f"        STD     {r * 40},X"]
    out.append("        RTS")
    out.append("* écran (X) -> copie du décor (Y)")
    out.append("SV16")
    for r in range(16): out += [f"        LDD     {r * 40},X", f"        STD     {r * BUF_ROWB},Y"]
    out.append("        RTS")
    out.append(f"BUFROW  EQU     {BUF_ROWB}")
    open('toboum_data.asm', 'w').write("\n".join(out) + "\n")
    P0 = PLANCHES[0]
    json.dump({'planches': PLANCHES, 'plateformes': P0['plats'], 'bombes': P0['bombes'], 'depart': P0['depart'],
               'piece': P0['piece'], 'decor': decors_px[DECOR],
               'ordre': ORDRE, 'decors': decors_px}, open('toboum_niveau.json', 'w'))
