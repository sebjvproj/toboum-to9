"""Petit film d'une vraie partie (écran reconstitué au passage du faisceau) -> apercus/toboum.gif

Personne n'est invincible : un pilote automatique joue. Toutes les 0,2 s, il essaie chaque
action sur une copie du jeu et les classe selon qu'elles rapprochent Toto de sa cible : la
bombe la plus proche (l'allumée compte double), la pièce éclair si elle est là, un glaçon
pendant le gel ; s'il piétine 2 s sur une bombe, il en vise une autre. Il garde la
première après laquelle Toto peut encore échapper aux ennemis pendant 0,8 s (en restant,
en allant à gauche, à droite ou en sautant) ; en cas d'impasse, il revient sur ses choix.
Le film est déterministe (même résultat à chaque lancement).
    python3 film.py [secondes de jeu]      (20 par défaut ; quelques minutes de calcul)"""
import os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__))
from to9sim import TO9, sym
from PIL import Image
os.chdir(os.path.join(HERE, '..', 'source'))
S = sym('toboum.lst')
E = S['ENTS']
DUREE = int(sys.argv[1]) if len(sys.argv) > 1 else 20
SEG = 10                                            # images par décision (0,2 s)
GAUCHE, DROITE, HAUT, BAS = 0x08, 0x09, 0x0B, 0x0A
ACTIONS = [None, ('hold', GAUCHE), ('hold', DROITE), ('key', HAUT), ('hold', HAUT), ('hold', BAS)]

def peek(s, lab, off=0): return s.mem.ram[S[lab] + off]
def score(s): return int(bytes(s.mem.ram[S['SCORE']:S['SCORE'] + 3]).hex())
def vivant(s): return peek(s, 'GSTATE') in (0, 2) and peek(s, 'LIVES') == 3

def cible(s):
    """(paire, ligne) visée"""
    n = peek(s, 'NENN')
    if peek(s, 'POWER') > 25 and n:                 # gel : le glaçon le plus proche
        tp, ty = peek(s, 'ENTS'), peek(s, 'ENTS', 1)
        return min(((s.mem.ram[E + 16 * k], s.mem.ram[E + 16 * k + 1]) for k in range(1, n + 1)),
                   key=lambda c: abs(c[0] - tp) * 3 + abs(c[1] - ty))
    if peek(s, 'COINON'):                           # la pièce (entité qui suit les ennemis)
        b = E + 16 * (n + 1); return s.mem.ram[b], s.mem.ram[b + 1]
    return bombe_visee(s)[1:]

EXCLUES = set()                                     # bombes abandonnées (Toto piétinait)
def bombe_visee(s):
    """(n°, paire, ligne) de la bombe restante la plus proche ; l'allumée paraît 2 fois plus près"""
    tp, ty = peek(s, 'ENTS'), peek(s, 'ENTS', 1)
    bp = s.mem.read_word(S['BOMBPTR']); lit = peek(s, 'LIT'); best = None
    for i in range(18):
        if not s.mem.ram[S['BSTATE'] + i] or i in EXCLUES: continue
        p, y = s.mem.ram[bp + 2 * i], s.mem.ram[bp + 2 * i + 1]
        d = (abs(p - tp) * 3 + abs(y - ty)) * (0.5 if i == lit else 1)
        if best is None or d < best[0]: best = (d, i, p, y)
    if best is None:
        if EXCLUES: EXCLUES.clear(); return bombe_visee(s)
        return None, tp, ty                         # plus de bombe : niveau fini
    return best[1:]

def valeur(s, s0):
    if not vivant(s): return -10 ** 9
    p, y = cible(s)
    d = abs(p - peek(s, 'ENTS')) * 3 + abs(y - peek(s, 'ENTS', 1))
    return (score(s) - score(s0)) * 10 - d

def joue(s, a):
    if a is None: return
    if a[0] == 'hold': s.hold(a[1], SEG)
    else: s.key(a[1])

def essai(s, a):
    c = copy.deepcopy(s); c.beam = None
    joue(c, a); c.run_frames(SEG)
    return valeur(c, s), c

def echappe(c, n=40):
    """Toto peut-il encore éviter tout contact pendant n images (une des 4 façons) ?"""
    for a in (None, ('hold', GAUCHE), ('hold', DROITE), ('key', HAUT)):
        d = copy.deepcopy(c)
        if a: (d.hold(a[1], n) if a[0] == 'hold' else d.key(a[1]))
        d.run_frames(n)
        if vivant(d): return True
    return False

def classe(s):
    """actions classées, avec l'état obtenu ; celles qui mènent à une impasse sont écartées"""
    res = sorted(((essai(s, a), k) for k, a in enumerate(ACTIONS)), key=lambda r: -r[0][0])
    return [(ACTIONS[k], c) for (v, c), k in res if v > -10 ** 9]

def demarre(faisceau):
    s = TO9('TOBOUM.BIN', fd='TOBOUM.fd')
    if faisceau: s.beam_on()
    return s
TITRE, CHARGE = 80, 150                             # écran titre, puis chargement du niveau

# 1. recherche (sans capture d'image)
s = demarre(False); s.run_frames(TITRE); s.key(0x0D); s.run_frames(CHARGE)
N = DUREE * 50 // SEG
hist = []                                           # par segment : [actions classées (+ état après), n° essayé]
etat = s; seg = 0; retours = 0; dernier = [18, 0]
while seg < N:
    if len(hist) == seg: hist.append([classe(etat), 0])
    cands, i = hist[seg]
    while i < len(cands) and not echappe(cands[i][1]): i += 1
    hist[seg][1] = i
    if i >= len(cands):                             # impasse : on revient sur le choix précédent
        hist.pop(); seg -= 1; retours += 1
        assert seg >= 0 and retours < 200, 'aucune partie sans contact trouvée'
        hist[seg][1] += 1
        etat = hist[seg - 1][0][hist[seg - 1][1]][1] if seg else s
        continue
    etat = cands[i][1]; seg += 1
    if peek(etat, 'BLEFT') != dernier[0]: dernier[:] = [peek(etat, 'BLEFT'), seg]; EXCLUES.clear()
    elif seg - dernier[1] >= 10 and not peek(etat, 'COINON') and not peek(etat, 'POWER'):
        EXCLUES.add(bombe_visee(etat)[0]); dernier[1] = seg     # piétine : autre bombe
    if seg % 5 == 0:
        print(f"{seg * SEG / 50:5.1f} s : score {score(etat):06d}, bombes restantes {peek(etat, 'BLEFT')}, "
              f"ennemis {peek(etat, 'NENN')}, pièce {peek(etat, 'COINON')}, gel {peek(etat, 'POWER')}, retours {retours}", flush=True)
choix = [h[0][h[1]][0] for h in hist]

# 2. le film : la même partie rejouée, image par image telle que le faisceau l'affiche
s = demarre(True)
images = []
def filme(n):
    for i in range(n // 2):
        s.run_frames(2)
        pal = s.palette_rgb(); px = s.beam_pixels()
        im = Image.new('RGB', (160, 200)); im.putdata([pal[c] for r in px for c in r])
        images.append(im.resize((480, 360), Image.NEAREST))
filme(TITRE)
s.key(0x0D); s.run_frames(CHARGE)
for a in choix:
    joue(s, a); filme(SEG)
assert vivant(s), 'la partie rejouée diffère de la recherche'
out = os.path.join('..', 'apercus', 'toboum.gif')
images[0].save(out, save_all=True, append_images=images[1:], duration=40, loop=0, optimize=True)
images[len(images) * 2 // 3].save(os.path.join('..', 'apercus', 'jeu.png'))
print(f"{len(images)} images, score {score(s):06d}, vies {peek(s, 'LIVES')}, niveau {peek(s, 'LEVELB'):x}, "
      f"{os.path.getsize(out) // 1024} Ko")
