"""Petit film du jeu (écran reconstitué au passage du faisceau) -> apercus/toboum.gif"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
from to9sim import TO9, sym
from PIL import Image
os.chdir(os.path.join(HERE, '..', 'source'))
S = sym('toboum.lst')
s = TO9('TOBOUM.BIN', fd='TOBOUM.fd'); s.run_frames(50)
s.beam_on()
frames = []; iters = []
def film(n):
    for i in range(n):
        it0 = s.peek(S['ITER']); s.run_frames(2)
        iters.append((s.peek(S['ITER']) - it0) % 256)
        pal = s.palette_rgb(); px = s.beam_pixels()
        im = Image.new('RGB', (160, 200)); im.putdata([pal[c] for r in px for c in r])
        frames.append(im.resize((480, 360), Image.NEAREST))
script = [(0x09, 30), (0x0B, 8), (None, 20), (0x0B, 60), (0x08, 25), (0x0B, 10), (0x08, 40), (None, 30),
          (0x0B, 12), (0x09, 50), (0x0B, 70), (0x08, 60), (None, 60), (0x09, 40), (0x0B, 80), (None, 80)]
for key, n in script:
    s.mem.ram[S['INVUL']] = 200                     # le film ne s'arrête pas sur un contact
    if key: s.hold(key, n)
    film(max(1, n // 2))
frames[0].save(os.path.join('..', 'apercus', 'toboum.gif'), save_all=True, append_images=frames[1:], duration=40, loop=0)
frames[len(frames) * 2 // 3].save(os.path.join('..', 'apercus', 'jeu.png'))
print(f'{len(frames)} images, score {bytes(s.mem.ram[S["SCORE"]:S["SCORE"]+3]).hex()}, ennemis {s.peek(S["NENN"])}, '
      f'tours d\'affichage par image (moyenne) {sum(iters) / len(iters) / 2:.2f}')
