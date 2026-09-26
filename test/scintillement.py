"""Mesure du scintillement dans le jeu. L'écran est reconstitué ligne par ligne au passage du
faisceau (ce que montre un vrai téléviseur). Pour chaque image et chaque sprite, on vérifie qu'il
apparaît entier (90 % de ses pixels visibles, ceux cachés par un autre sprite exceptés) à l'une
de ses deux dernières positions dessinées.      python3 scintillement.py [nb_ennemis]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'outils'))
from to9sim import TO9, sym
import sprites as SP
os.chdir(os.path.join(HERE, '..', 'source'))
S = sym('toboum.lst')
ESIZE = 16
def miroir(g): return [list(reversed(r)) for r in g]
NOMS = {'TOTO_M1D': 'TOTO_MARCHE', 'TOTO_M2D': 'TOTO_MARCHE_2', 'TOTO_M1G': '-TOTO_MARCHE', 'TOTO_M2G': '-TOTO_MARCHE_2',
        'TOTO_V1D': 'TOTO_VOL', 'TOTO_V2D': 'TOTO_VOL_2', 'TOTO_V1G': '-TOTO_VOL', 'TOTO_V2G': '-TOTO_VOL_2',
        'TOTO_CH': 'TOTO_CHUTE', 'TOTO_PERDU': 'TOTO_PERDU', 'ROBOT_1': 'ROBOT', 'ROBOT_2': 'ROBOT_2',
        'CHAUVE_1': 'CHAUVE_SOURIS_1', 'CHAUVE_2': 'CHAUVE_SOURIS_2', 'BOULE_1': 'BOULE', 'BOULE_2': 'BOULE_2',
        'NUAGE_1': 'NUAGE_1', 'NUAGE_2': 'NUAGE_2'}
GRILLE = {S['SPR_' + lab]: (miroir(SP.grid(n[1:])) if n.startswith('-') else SP.grid(n)) for lab, n in NOMS.items()}

def mesure(n, images=100):
    s = TO9('TOBOUM.BIN', fd='TOBOUM.fd'); s.run_frames(50); s.key(0x0D); s.run_frames(120)   # écran titre : une touche, puis le niveau se charge
    s.mem.ram[S['NMAXLV']] = n
    while s.peek(S['NENN']) < n:                    # les ennemis arrivent (Toto invincible)
        s.mem.ram[S['INVUL']] = 250; s.mem.ram[S['SPT']] = min(s.peek(S['SPT']), 10); s.run_frames(10)
    hist = []
    def note(sim):
        it = sim.peek(S['ITER']); st = []
        for k in range(sim.peek(S['NENN']) + 1):
            b = S['ENTS'] + ESIZE * k
            st.append((sim.peek(b), sim.peek(b + 1), GRILLE[sim.mem.read_word(b + (8 if it & 8 else 6))]))
        hist.append(st)
    s.hooks[S['UPDONE']] = note
    s.beam_on(); s.run_frames(2)
    ok = total = 0; it0 = s.peek(S['ITER'])
    for i in range(images):
        s.mem.ram[S['INVUL']] = 250
        s.run_frames(1)
        px = s.beam_pixels()
        for k in range(len(hist[-1])):
            vu = False
            for st in hist[-2:]:
                if k >= len(st): continue
                P, Y, g = st[k]
                cache = {(Y2 + j, 2 * P2 + i) for m, (P2, Y2, g2) in enumerate(st) if m != k
                         for j, r in enumerate(g2) for i, v in enumerate(r) if v}
                pts = [(Y + j, 2 * P + i, v) for j, r in enumerate(g) for i, v in enumerate(r)
                       if v and (Y + j, 2 * P + i) not in cache and Y + j < 200]
                if not pts or sum(px[y][x] == v for y, x, v in pts) >= 0.9 * len(pts): vu = True; break
            ok += vu; total += 1
    return ok, total, ((s.peek(S['ITER']) - it0) % 256) / images * 50

if __name__ == '__main__':
    for n in ([int(sys.argv[1])] if len(sys.argv) > 1 else (2, 4, 6, 8)):
        ok, total, ips = mesure(n)
        print(f'{n} ennemis : sprites entiers à l\'écran {ok}/{total} = {ok / total:.1%}, {ips:.0f} images/s')
