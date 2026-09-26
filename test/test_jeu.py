"""Tests du jeu TOboum dans le simulateur TO9 (lancer après source/build.sh)."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
from to9sim import TO9, sym
from PIL import Image
os.chdir(os.path.join(HERE, '..', 'source'))
S = sym('toboum.lst')
NIV = json.load(open('toboum_niveau.json'))
fails = []
def check(ok, msg):
    print(('OK   ' if ok else 'ÉCHEC') + ' ' + msg)
    if not ok: fails.append(msg)
E = S['ENTS']
def P(s): return s.peek(E)
def Y(s): return s.peek(E + 1)
def score(s): return bytes(s.mem.ram[S['SCORE']:S['SCORE'] + 3]).hex()
def pixels(s):
    A, B = s.mem.vram
    return [[v for xb in range(40) for v in (A[y*40+xb] >> 4, A[y*40+xb] & 15, B[y*40+xb] >> 4, B[y*40+xb] & 15)]
            for y in range(200)]
def boot(fd=True):
    s = TO9('TOBOUM.BIN', fd='TOBOUM.fd' if fd else None); s.run_frames(60); return s
def poke(s, lab, v, off=0): s.mem.ram[S[lab] + off] = v & 0xFF

# 1. départ
s = boot()
check(s.peek(S['LIVES']) == 3 and score(s) == '000000' and s.peek(S['BLEFT']) == 18, "départ : 3 vies, score 0, 18 bombes")
check((P(s), Y(s)) == (NIV['depart'][0] // 2, NIV['depart'][1]) and s.peek(S['ONGND']) == 1, f"Toto au départ, au sol ({P(s)}, {Y(s)})")
px = pixels(s)
bx, by = NIV['bombes'][5]
diff = sum(px[by + j][bx + i] != NIV['decor'][by + j][bx + i] for j in range(12) for i in range(8))
check(diff > 20, f"les bombes sont dessinées ({diff} pixels de bombe à la 6e)")
check(s.peek(S['NENN']) == 0, "pas encore d'ennemi")

# 2. marche à droite
p0 = P(s); s.hold(0x09, 40); s.run_frames(40)
check(P(s) > p0 and s.peek(S['FACE']) == 0, f"marche à droite ({p0} -> {P(s)})")
s.run_frames(20)

# 3. saut : Toto monte puis redescend et se pose
y0 = Y(s); s.hold(0x0B, 10); s.run_frames(12)
y1 = Y(s)
check(y1 < y0 - 20 and s.peek(S['ONGND']) == 0, f"saut : Toto monte ({y0} -> {y1})")
s.run_frames(180)
check(s.peek(S['ONGND']) == 1 and Y(s) <= y0, f"il retombe et se pose (ligne {Y(s)})")

# 3b. saut en biais au clavier : droite maintenue, puis haut (le clavier ne voit que haut)
s3 = boot(); s3.hold(0x09, 60); s3.run_frames(20)
p0 = P(s3); s3.hold(0x0B, 8); s3.run_frames(30)
check(s3.peek(S['ONGND']) == 0 and P(s3) > p0 + 3 and s3.peek(S['TVX']) == 1, f"saut en biais : droite puis haut, Toto part à droite ({p0} -> {P(s3)})")

# 4. saut façon arcade : hauteur selon la touche, frein par nouvel appui, +10 points
def sommet(action):
    t = boot(); t.mem.ram[S['INVUL']] = 250; y0 = Y(t); ys = []
    action(t)
    for f in range(300):
        t.run_frames(1); ys.append(Y(t))
        if f > 10 and t.peek(S['ONGND']): break
    return y0 - min(ys), len(ys), t
h_n, d_n, t = sommet(lambda t: t.key(0x0B))
h_h, d_h, _ = sommet(lambda t: t.hold(0x0B, 400))
def bas(t): t.key(0x0B); t.run_frames(4); t.hold(0x0A, 300)
h_b, d_b, _ = sommet(bas)
check(100 <= h_n <= 125 and h_h >= 160 and 50 <= h_b <= 75,
      f"hauteur du saut : neutre {h_n}, haut tenu {h_h} (plafond), bas tenu {h_b} lignes")
check(d_h > d_n > d_b, f"temps en l'air : haut tenu {d_h} > neutre {d_n} > bas tenu {d_b} images")
check(score(t) == '000010', f"+10 points par décollage (score {score(t)})")
s2 = boot(); s2.key(0x0B); s2.run_frames(20); s2.key(0x0B); s2.run_frames(2)
v = s2.mem.read_word(S['TVY']); v = v - 65536 if v > 32767 else v
check(0 <= v < 0x20 and s2.peek(S['ONGND']) == 0, f"frein : un nouvel appui en l'air annule la vitesse verticale ({v / 256:+.2f})")

# 5. bombe allumée (n° 0) ramassée : 200 points, la suivante s'allume, fond propre
s = boot()
bx, by = NIV['bombes'][0]
poke(s, 'ENTS', bx // 2); poke(s, 'ENTS', by, 1); poke(s, 'ONGND', 0)
s.run_frames(3)
check(s.peek(S['BSTATE']) == 0 and score(s) == '000200', f"bombe allumée ramassée : +200 (score {score(s)})")
check(s.peek(S['LIT']) == 1 and s.peek(S['BLEFT']) == 17, f"la bombe suivante s'allume (n° {s.peek(S['LIT'])})")
# 6. bombe éteinte : +100 ; et le décor sous la bombe est restauré
bx, by = NIV['bombes'][9]
poke(s, 'ENTS', bx // 2 + 2); poke(s, 'ENTS', by, 1)
s.run_frames(3)
check(s.peek(S['BSTATE'] + 9) == 0 and score(s) == '000300', f"bombe éteinte : +100 (score {score(s)})")
poke(s, 'ENTS', 30); poke(s, 'ENTS', 176, 1); poke(s, 'ONGND', 1); s.run_frames(5)
px = pixels(s)
diff = sum(px[by + j][bx + i] != NIV['decor'][by + j][bx + i] for j in range(16) for i in range(8))
check(diff == 0, f"décor propre à la place de la bombe ramassée ({diff} pixels différents)")

# 7. les ennemis arrivent
s = boot()
for i in range(6): s.mem.ram[S['INVUL']] = 250; s.run_frames(70)      # Toto invincible pendant l'observation
check(s.peek(S['NENN']) >= 2, f"ennemis apparus : {s.peek(S['NENN'])}")
types = [s.peek(E + 16 * k + 11) for k in range(1, s.peek(S['NENN']) + 1)]
check(types[:2] == [1, 2], f"types en alternance (robot, chauve-souris...) : {types}")
rob = E + 16
check(s.peek(rob + 1) > 20, f"le robot est tombé (ligne {s.peek(rob + 1)})")

# 8. contact avec un ennemi : une vie en moins, puis on repart sans ennemis
s.mem.ram[S['INVUL']] = 0
s.mem.ram[rob] = P(s); s.mem.ram[rob + 1] = Y(s)
s.run_frames(3)
check(s.peek(S['GSTATE']) == 1, "contact : Toto est touché")
s.run_frames(100)
check(s.peek(S['LIVES']) == 2 and s.peek(S['NENN']) == 0 and s.peek(S['GSTATE']) == 0, f"une vie en moins ({s.peek(S['LIVES'])}), plus d'ennemis")

# 9. dernière bombe : niveau suivant
s = boot()
for i in range(18): s.mem.ram[S['BSTATE'] + i] = 0
s.mem.ram[S['BSTATE'] + 17] = 1; poke(s, 'BLEFT', 1)
bx, by = NIV['bombes'][17]
poke(s, 'ENTS', bx // 2); poke(s, 'ENTS', by, 1); poke(s, 'ONGND', 0)
s.run_frames(3)
check(s.peek(S['GSTATE']) == 2, "dernière bombe : niveau terminé")
s.run_frames(200)                                  # (pause, lecture du décor sur la disquette)
check(s.peek(S['LEVELB']) == 2 and s.peek(S['BLEFT']) == 18 and s.peek(S['NMAXLV']) == 5, f"niveau 2 : 18 bombes, 5 ennemis au plus")

# 10. fin de partie : record, puis nouvelle partie
s = boot(); poke(s, 'LIVES', 1); s.mem.ram[S['SCORE']:S['SCORE'] + 3] = bytes([0, 0x12, 0x34])
s.run_frames(300)
s.mem.ram[S['INVUL']] = 0
k = s.peek(S['NENN']); r = E + 16 * k
s.mem.ram[r] = P(s); s.mem.ram[r + 1] = Y(s)
s.run_frames(90)
check(s.peek(S['GSTATE']) == 3 and s.border == 12, "plus de vies : fin de partie (bord rouge)")
check(bytes(s.mem.ram[S['RECORD']:S['RECORD'] + 3]).hex() == '001234', "le record est gardé")
s.run_frames(160)
check(s.peek(S['LIVES']) == 3 and score(s) == '000000' and s.peek(S['GSTATE']) == 0, "nouvelle partie")

# 11. stabilité : 40 s de jeu au hasard
import random
random.seed(1)
s = boot(); piles = set()
s.hooks[S['UPDONE']] = lambda sim: piles.add(sim.cpu.system_stack_pointer.value)   # toujours au même endroit
for i in range(400):
    if random.random() < 0.3: s.hold(random.choice([0x08, 0x09, 0x0B, 0x0B, 0x20]), random.randint(3, 30))
    s.run_frames(5)
pc = s.cpu.program_counter.value
check(piles == {0x9FF0} and (0xA000 <= pc < 0xE000 or pc >= 0xE800),
      f"40 s de jeu au hasard : pile toujours {sorted(hex(v) for v in piles)} en fin de tour, score {score(s)}, niveau {s.peek(S['LEVELB'])}")


# 12. personne ne traverse les plateformes : 1 min, 8 ennemis, Toto piloté au hasard (invincible)
PL = [(x // 2, (x + w) // 2, y) for x, y, w in NIV['plateformes']]
def dans_plateforme(p, y):
    return any(p + 2 >= p0 and p + 1 < p1 and y <= yt + 3 and y + 15 >= yt for p0, p1, yt in PL)
s = boot(); s.mem.ram[S['NMAXLV']] = 8
viol = []; vus = [0]
def controle(sim):
    for k in range(sim.peek(S['NENN']) + 1):
        b = E + 16 * k; p, y = sim.peek(b), sim.peek(b + 1)
        if dans_plateforme(p, y): viol.append((k, sim.peek(b + 11), p, y))
    vus[0] += 1
s.hooks[S['UPDONE']] = controle
random.seed(7)
for i in range(600):
    s.mem.ram[S['INVUL']] = 250; s.mem.ram[S['SPT']] = min(s.peek(S['SPT']), 20)
    if random.random() < 0.3: s.hold(random.choice([0x08, 0x09, 0x0B, 0x0B, 0x20]), random.randint(3, 40))
    s.run_frames(5)
check(not viol and s.peek(S['NENN']) == 8, f"1 min avec 8 ennemis : aucun sprite dans une plateforme ({vus[0]} images contrôlées, {len(viol)} fautes {viol[:3]})")

# 13. un décor par niveau : lu sur la disquette, palette comprise ; retour au 1er après le 5e
def finir_niveau(s):
    for i in range(18): s.mem.ram[S['BSTATE'] + i] = 0
    s.mem.ram[S['BSTATE'] + 17] = 1; poke(s, 'BLEFT', 1)
    bx, by = NIV['bombes'][17]
    poke(s, 'ENTS', bx // 2); poke(s, 'ENTS', by, 1); poke(s, 'ONGND', 0)
    s.run_frames(3); s.run_frames(200)
def ecart_decor(s, nom):
    """pixels de l'aire de jeu différents du décor attendu (hors bombes et Toto)"""
    px = pixels(s); ref = NIV['decors'][nom]
    hors = {(y, x) for bx, by in NIV['bombes'] for y in range(by, by + 16) for x in range(bx, bx + 8)}
    for k in range(s.peek(S['NENN']) + 1):            # Toto et ennemis, là où ils sont dessinés
        b = E + 16 * k; p, y = s.peek(b + 2), s.peek(b + 3)
        if p != 0xFF: hors |= {(yy, xx) for yy in range(y, y + 16) for xx in range(2 * p, 2 * p + 8)}
    return sum(px[y][x] != ref[y][x] for y in range(8, 192) for x in range(8, 124) if (y, x) not in hors)
ordre = NIV['ordre']
s = boot()
check(ecart_decor(s, ordre[0]) == 0 and s.dk_reads == [], f"niveau 1 : {ordre[0]}, sans lecture de disquette")
finir_niveau(s)
lu = s.dk_reads
check(len(lu) == 30 and lu[0][:2] == (21, 1) and lu[-1][:2] == (22, 14), f"niveau 2 : {len(lu)} secteurs lus, pistes {lu[0][:2]} -> {lu[-1][:2]}")
check(ecart_decor(s, ordre[1]) == 0, f"niveau 2 : décor {ordre[1]} affiché ({ecart_decor(s, ordre[1])} pixels différents)")
pal_attendue = [tuple(c) for c in json.load(open(f'../graphismes/decors/{ordre[1]}_palette.json'))['niveaux_to9']]
lv = [round(255 * (v / 15) ** (1 / 2.8)) for v in range(16)]
check(s.palette_rgb()[:7] == [tuple(lv[c] for c in t) for t in pal_attendue[:7]], "niveau 2 : palette du décor")
for n in range(3, 7): finir_niveau(s)
check(s.peek(S['LEVELB']) == 6 and ecart_decor(s, ordre[0]) == 0, f"niveau 6 : retour à {ordre[0]}")
s = boot(fd=False); finir_niveau(s)
check(s.peek(S['LEVELB']) == 2 and ecart_decor(s, ordre[0]) == 0, "sans disquette : le niveau 2 garde le 1er décor, sans planter")

print('\n' + ('TOUT EST OK' if not fails else f'{len(fails)} ÉCHEC(S)'))
sys.exit(1 if fails else 0)
