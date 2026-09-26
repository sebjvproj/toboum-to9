"""Les 5 niveaux (décor et planche) tels que le jeu les affiche -> apercus/niveaux.png"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
from to9sim import TO9, sym
from PIL import Image
os.chdir(os.path.join(HERE, '..', 'source'))
S = sym('toboum.lst')
s = TO9('TOBOUM.BIN', fd='TOBOUM.fd'); s.run_frames(60)
def ecran():
    pal = s.palette_rgb(); A, B = s.mem.vram
    im = Image.new('RGB', (160, 200))
    im.putdata([pal[v] for y in range(200) for xb in range(40)
                for v in (A[y*40+xb] >> 4, A[y*40+xb] & 15, B[y*40+xb] >> 4, B[y*40+xb] & 15)])
    return im.resize((320, 200), Image.NEAREST)
planche = Image.new('RGB', (3 * 320 + 2 * 8, 2 * 200 + 8), (32, 32, 32))
for n in range(5):
    planche.paste(ecran(), ((n % 3) * 328, (n // 3) * 208))
    for i in range(18): s.mem.ram[S['BSTATE'] + i] = 0          # niveau suivant : dernière bombe prise
    s.mem.ram[S['BSTATE'] + 17] = 1; s.mem.ram[S['BLEFT']] = 1
    bp = s.mem.read_word(S['BOMBPTR'])
    s.mem.ram[S['ENTS']] = s.peek(bp + 34); s.mem.ram[S['ENTS'] + 1] = s.peek(bp + 35); s.mem.ram[S['ONGND']] = 0
    s.run_frames(200)
planche.save(os.path.join('..', 'apercus', 'niveaux.png'))
print('apercus/niveaux.png')
