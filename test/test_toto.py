"""Tests du jeu TOTO dans le simulateur TO9 (lancer après source/build.sh)."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
from to9sim import TO9, sym
from PIL import Image
os.chdir(os.path.join(HERE, '..', 'source'))
S = sym('toto.lst')
NIV = json.load(open('toto_niveau.json'))
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
def boot():
    s = TO9('TOTO.BIN'); s.run_frames(60); return s
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
s.run_frames(120)
check(s.peek(S['ONGND']) == 1 and Y(s) <= y0, f"il retombe et se pose (ligne {Y(s)})")

# 4. vol plané : touche haut maintenue en retombant = descente lente
s2 = boot(); s2.hold(0x0B, 200); s2.run_frames(60)
v = s2.mem.read_word(S['TVY'])
check(s2.peek(S['GLIDE']) == 1 and v == 0x80, f"vol plané : vitesse de chute limitée ({v:#x})")

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
s.run_frames(100)
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
s = boot(); sp0 = s.cpu.system_stack_pointer.value
for i in range(400):
    if random.random() < 0.3: s.hold(random.choice([0x08, 0x09, 0x0B, 0x0B, 0x20]), random.randint(3, 30))
    s.run_frames(5)
check(abs(s.cpu.system_stack_pointer.value - sp0) < 16 and 0xA000 <= s.cpu.program_counter.value < 0xE000 or s.cpu.program_counter.value >= 0xE800,
      f"40 s de jeu au hasard : pile {sp0:04X} -> {s.cpu.system_stack_pointer.value:04X}, score {score(s)}, niveau {s.peek(S['LEVELB'])}")


print('\n' + ('TOUT EST OK' if not fails else f'{len(fails)} ÉCHEC(S)'))
sys.exit(1 if fails else 0)
