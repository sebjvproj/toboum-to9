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

DECOR = sys.argv[1] if len(sys.argv) > 1 else 'egypte'
BUF_ROWB = 29                                      # octets par ligne et par banque dans la copie du décor
BLANC, JAUNE = SP.CODE['w'], SP.CODE['y']

# disposition : plateformes (x, y, largeur en pixels) et bombes (x, y), x multiple de 4
PLATEFORMES = [(20, 60, 32), (72, 104, 36), (24, 150, 32)]
BOMBES = [(12, 12), (24, 12), (36, 12), (84, 12), (96, 12), (108, 12),
          (12, 80), (12, 100), (12, 120), (112, 70), (112, 90), (112, 110),
          (24, 44), (36, 44), (76, 88), (92, 88), (28, 134), (44, 134)]
DEPART = (60, 176)                                 # Toto au départ (x pixels, y)

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
    for x, y in BOMBES: assert x % 4 == 0, 'bombes sur une paire paire (x multiple de 4)'
    px, lv = charge_decor(DECOR)
    for p in PLATEFORMES: plateforme(px, *p)
    for t, y in (('SCORE', 12), ('RECORD', 50), ('VIES', 90), ('NIVEAU', 130)):
        texte(px, 131, y, t, JAUNE)
    out = ["* Généré par donnees.py - ne pas éditer", f"* décor : {DECOR}"]
    def db(label, data, per=16):
        if label: out.append(label)
        for i in range(0, len(data), per):
            out.append("        FCB " + ",".join(f"${b:02X}" for b in data[i:i + per]))
    pal = []
    for r, g, b in lv: pal += [(g << 4) | r, b]
    db("PALETTE", pal, 8)
    A = bytearray(); B = bytearray()
    for y in range(200):
        for k in range(40):
            A.append(px[y][4 * k] << 4 | px[y][4 * k + 1]); B.append(px[y][4 * k + 2] << 4 | px[y][4 * k + 3])
    ca, cb = LZ.lz(bytes(A)), LZ.lz(bytes(B))
    assert LZ.unlz(ca, 8000) == bytes(A) and LZ.unlz(cb, 8000) == bytes(B)
    db("LZ_DECOR_A", ca); db("LZ_DECOR_B", cb)
    print(f'décor {DECOR} : {len(ca) + len(cb)} octets compressés')
    # plateformes : paire de début, paire de fin (exclue), ligne du dessus
    out.append(f"NPLAT   EQU     {len(PLATEFORMES)}")
    db("PLATS", sum([[x // 2, (x + w) // 2, y] for x, y, w in PLATEFORMES], []), 12)
    out.append(f"NBOMB   EQU     {len(BOMBES)}")
    db("BOMBS", sum([[x // 2, y] for x, y in BOMBES], []), 12)
    out.append(f"DEPP    EQU     {DEPART[0] // 2}")
    out.append(f"DEPY    EQU     {DEPART[1]}")
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
    json.dump({'plateformes': PLATEFORMES, 'bombes': BOMBES, 'depart': DEPART, 'decor': px},
              open('toboum_niveau.json', 'w'))
