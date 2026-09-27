"""Mini-simulateur TO9 (CPU 6809 via le paquet MC6809, vidéo bitmap 16 couleurs, timer 6846,
CNA, clavier par GETC). Repris de TOetris, du même auteur."""
import sys, os
from PIL import Image
from MC6809.components.cpu6809 import CPU
from MC6809.core.configs import BaseConfig

CYC_FRAME = 20000          # 1 MHz / 50 Hz
CYC_LINE = 64

class Mem:
    def __init__(self, sim):
        self.sim = sim
        self.ram = bytearray(0x10000)
        self.vram = [bytearray(0x2000), bytearray(0x2000)]   # [RAMA, RAMB]
        self.cpu = None
    # API utilisée par MC6809
    def read_byte(self, a):
        a &= 0xFFFF
        if 0x4000 <= a < 0x6000:
            return self.vram[0 if self.sim.prc & 1 else 1][a - 0x4000]
        if 0xE7C0 <= a < 0xE800:
            return self.sim.io_read(a)
        return self.ram[a]
    def read_word(self, a):
        return (self.read_byte(a) << 8) | self.read_byte(a + 1)
    def write_byte(self, a, v):
        a &= 0xFFFF; v &= 0xFF
        if 0x4000 <= a < 0x6000:
            self.vram[0 if self.sim.prc & 1 else 1][a - 0x4000] = v; return
        if 0xE7C0 <= a < 0xE800:
            self.sim.io_write(a, v); return
        if a >= 0xE000:
            raise RuntimeError(f"écriture en ROM ${a:04X} PC=${self.cpu.last_op_address:04X}")
        if 0xA000 <= a < self.sim.code_end:
            raise RuntimeError(f"écriture dans le code ${a:04X} PC=${self.cpu.last_op_address:04X}")
        self.ram[a] = v
    def write_word(self, a, v):
        self.write_byte(a, v >> 8); self.write_byte(a + 1, v & 0xFF)
    def load(self, a, data):
        self.ram[a:a + len(data)] = data

class Cfg(BaseConfig):
    RAM_START = 0; RAM_END = 0xFFFF; ROM_START = 0x10000; ROM_END = 0x10000

class TO9:
    def __init__(self, binpath, joystick=True, vsync_ok=True, mon_overhead=60, timept=True, fd=None, machine='TO9'):
        self.prc = 0x01
        self.machine = machine                # 'TO9', 'TO8' ou 'TO9+' (octet $FFF0 de la ROM, palette)
        self.tcr = 0; self.tlatch = 0xFFFF; self.next_irq = None
        self.mon_overhead = mon_overhead      # cycles supposés du gestionnaire d'IRQ du moniteur
        self.timept = timept                  # le moniteur appelle-t-il TIMEPT ?
        self.dac = []                         # (cycle, valeur 0..63)
        self.buz = []
        self.ddrb = 0; self.pcr = 0x30
        self.irq_count = 0
        self.vmode = 0
        self.palidx = 0
        self.paldata = [0] * 32
        self.border = None
        self.joy_present = joystick
        self.joy_dir = 0xFF
        self.joy_btn = 0xFF
        self.cra = 0; self.crb = 0
        self.vsync_ok = vsync_ok
        self.keys = {}            # frame -> code (injecté au prochain GETC)
        self.pending = []
        self.putc = []
        self.mem = Mem(self)
        self.cpu = CPU(self.mem, Cfg({"verbosity": None, "trace": None}))
        self.mem.cpu = self.cpu
        d = open(binpath, 'rb').read(); i = 0; self.code_end = 0
        while True:
            t, n, a = d[i], d[i+1] << 8 | d[i+2], d[i+3] << 8 | d[i+4]
            if t == 0xFF: self.entry = a; break
            self.mem.load(a, d[i+5:i+5+n]); self.code_end = max(self.code_end, a + n); i += 5 + n
        # gestionnaire d'IRQ simplifié du moniteur : appelle [TIMEPT] si STATUS bit5
        stub = [0xB6,0x60,0x19, 0x85,0x20, 0x27,0x04, 0x6E,0x9F,0x60,0x27, 0x3B]   # JMP [TIMEPT], retour par $E830
        if not timept: stub = [0x3B]
        self.mem.ram[0xF000:0xF000+len(stub)] = bytes(stub)
        self.mem.ram[0xE830] = 0x3B   # sortie d'IRQ du moniteur : RTI
        self.mem.ram[0xFFF0] = {'TO9': 2, 'TO8': 3, 'TO9+': 6}[machine]   # identification (relevée dans DCMOTO)
        self.mem.ram[0xE803] = 0x39   # RTS
        self.mem.ram[0xE806] = 0x39
        self.mem.ram[0xE82A] = 0x39   # DKCO (disquette) : simulée ci-dessous, puis RTS
        self.fd = open(fd, 'rb').read() if fd else None      # image .fd du lecteur 0
        self.dk_reads = []
        self.cpu.system_stack_pointer.set(0x9F00)
        self.cpu.program_counter.set(self.entry)
        self.cpu.cc.set(0x00) if hasattr(self.cpu, 'cc') else None
        self.getc_calls = 0
        self.hooks = {}                     # adresse -> fonction(sim), appelée avant l'instruction
        self.beam = None                    # activer avec beam_on() : écran tel que balayé
        self._beam_line = -1
        self.held_until = 0

    @property
    def frame(self):
        return self.cpu.cycles // CYC_FRAME

    def io_read(self, a):
        if a == 0xE7C3: return self.prc
        if a == 0xE7C6:                               # compteur du timer 6846 (octet fort ; l'octet
            if self.next_irq is None: v = self.tlatch   # faible est figé jusqu'à sa lecture)
            else: v = max(0, min(self.tlatch, self.next_irq - self.cpu.cycles - 1))
            self._tlsb = v & 0xFF
            return v >> 8
        if a == 0xE7C7: return getattr(self, '_tlsb', 0)
        if a == 0xE7C1: return self.pcr
        if a == 0xE7C8: return 0xFE | (1 if self.held_until > self.frame else 0)
        if a == 0xE7E7:
            if not self.vsync_ok: return 0
            line = (self.cpu.cycles % CYC_FRAME) // CYC_LINE
            return 0x80 if line < 200 else 0x00
        if a == 0xE7CC:
            if not self.joy_present: return 0x5A
            return self.joy_dir if self.cra & 4 else 0
        if a == 0xE7CD:
            if not self.joy_present: return 0x5A
            return self.joy_btn if self.crb & 4 else 0
        if a == 0xE7CE: return self.cra if self.joy_present else 0x5A
        if a == 0xE7CF: return self.crb if self.joy_present else 0x5A
        return 0
    def io_write(self, a, v):
        if a == 0xE7C3: self.prc = v
        elif a == 0xE7DC: self.vmode = v
        elif a == 0xE7DB: self.palidx = v & 31
        elif a == 0xE7DA:
            self.paldata[self.palidx] = v; self.palidx = (self.palidx + 1) & 31
        elif a == 0xE7DD: self.border = v
        elif a == 0xE7CE: self.cra = v
        elif a == 0xE7CF: self.crb = v
        elif a == 0xE7CD:
            if self.crb & 4: self.dac.append((self.cpu.cycles, v & 0x3F & self.ddrb))
            else: self.ddrb = v
        elif a == 0xE7C1: self.pcr = v; self.buz.append((self.cpu.cycles, (v >> 3) & 1))
        elif a == 0xE7C5:
            self.tcr = v
            self.next_irq = self.cpu.cycles + self.tlatch + 1 if v & 0x40 else None
        elif a == 0xE7C6: self.tmsb = v
        elif a == 0xE7C7:
            self.tlatch = (getattr(self, 'tmsb', 0) << 8) | v
            if self.tcr & 0x40: self.next_irq = self.cpu.cycles + self.tlatch + 1

    def run_frames(self, n):
        end = (self.frame + n) * CYC_FRAME
        cpu = self.cpu
        while cpu.cycles < end:
            # l'IRQ d'abord : si elle tombe à l'entrée de GETC, la touche ne doit être
            # remise qu'au retour, sinon elle serait perdue (écrasée par le 2e passage)
            # le timer 6846 lève son drapeau d'IRQ ; il reste en attente tant que les IRQ
            # sont masquées (une seule en attente, comme sur le vrai circuit)
            if self.next_irq is not None and cpu.cycles >= self.next_irq:
                self.next_irq += self.tlatch + 1
                self.irq_pending = True
            if getattr(self, 'irq_pending', False) and not cpu.I:
                self.irq_pending = False
                self.irq_count += 1
                cpu.E = 1
                cpu.push_irq_registers()
                cpu.I = 1
                cpu.cycles += 19 + self.mon_overhead
                cpu.program_counter.set(0xF000)
                continue
            pc = cpu.program_counter.value
            if pc in self.hooks: self.hooks[pc](self)     # crochets de test (adresse -> fonction)
            if pc == 0xE806:
                self.getc_calls += 1
                f = self.frame
                for k in sorted(list(self.keys)):
                    if k <= f: self.pending.append(self.keys.pop(k))
                cpu.accu_b.set(self.pending.pop(0) if self.pending else 0)
            elif pc == 0xE803:
                self.putc.append(cpu.accu_b.value)
            elif pc == 0xE82A:                         # DKCO : lecture d'un secteur (opération 2)
                r = self.mem.ram
                op, drv, trk, sec, buf = r[0x6048], r[0x6049], r[0x604A] << 8 | r[0x604B], r[0x604C], r[0x604F] << 8 | r[0x6050]
                ok = self.fd is not None and op == 2 and drv == 0 and trk < 80 and 1 <= sec <= 16
                if ok:
                    o = (trk * 16 + sec - 1) * 256
                    for i in range(256): self.mem.write_byte(buf + i, self.fd[o + i])
                    self.dk_reads.append((trk, sec, buf))
                cpu.C = 0 if ok else 1                  # C = 1 : erreur
                cpu.cycles += 20000 if ok else 100      # (une lecture prend du temps)
            cpu.get_and_call_next_op()
            if self.beam is not None:                 # image vue par le faisceau, ligne par ligne
                line = (cpu.cycles % CYC_FRAME) // CYC_LINE
                if line != self._beam_line:
                    # une instruction longue ou une entrée d'IRQ peut sauter des lignes : on les copie aussi
                    first = self._beam_line + 1 if 0 <= self._beam_line < line else line
                    self._beam_line = line
                    for l in range(first, min(line, 199) + 1):
                        o = l * 40
                        self.beam[l] = (bytes(self.mem.vram[0][o:o + 40]), bytes(self.mem.vram[1][o:o + 40]))

    def _nouvelle_touche(self, f):
        """comme le moniteur du TO9 : seule la dernière touche enfoncée se répète,
        une nouvelle touche annule les répétitions à venir de la précédente"""
        self.keys = {k: v for k, v in self.keys.items() if k <= f}

    def hold(self, code, frames):
        """touche maintenue : appui, répétition après 800 ms puis toutes les 70 ms"""
        f0 = self.frame
        self._nouvelle_touche(f0)
        self.keys[f0] = code
        t = 40
        while t < frames:
            self.keys[f0 + int(t)] = code; t += 3.5
        self.held_until = f0 + frames

    def key(self, code, at=None):
        f = self.frame if at is None else at
        if at is None: self._nouvelle_touche(f)
        self.keys[f] = code
        self.held_until = max(self.held_until, f + 3)   # frappe brève : ~60 ms

    def palette_rgb(self):
        lv = [round(255 * (v / 15) ** (1 / 2.8)) for v in range(16)]
        out = []
        for n in range(16):
            k = n ^ 8 if self.machine == 'TO9' else n   # TO9 : entrée k -> couleur k xor 8 (MAME) ; pas sur TO8/TO9+
            lo, hi = self.paldata[2 * k], self.paldata[2 * k + 1]
            out.append((lv[lo & 15], lv[lo >> 4], lv[hi & 15]))
        return out

    def screenshot(self, path, scale=2):
        pal = self.palette_rgb()
        A, B = self.mem.vram
        im = Image.new('RGB', (320, 200))
        px = im.load()
        for y in range(200):
            for xb in range(40):
                o = y * 40 + xb
                a, b = A[o], B[o]
                for i, nib in enumerate((a >> 4, a & 15, b >> 4, b & 15)):
                    c = pal[nib]
                    x = (xb * 4 + i) * 2
                    px[x, y] = c; px[x + 1, y] = c
        # rendu 4:3 approximatif (pixels deux fois plus hauts)
        im = im.resize((320 * scale, 200 * scale * 6 // 5), Image.NEAREST)
        im.save(path)

    def beam_on(self):
        self.beam = [(bytes(40), bytes(40))] * 200

    def beam_pixels(self):
        """pixels (index de palette) de la dernière image balayée par le faisceau"""
        return [[v for xb in range(40) for v in (a[xb] >> 4, a[xb] & 15, b[xb] >> 4, b[xb] & 15)]
                for a, b in self.beam]

    def peek(self, a): return self.mem.ram[a]

def sym(lst):
    s = {}
    for line in open(lst, errors='replace'):
        if line.startswith('[ G]'):
            p = line.split(); s[p[2]] = int(p[3], 16)
    return s

def wav(sim, path, c0=0, c1=None, rate=22050):
    import wave, struct
    ev = [e for e in sim.dac if e[0] >= c0 and (c1 is None or e[0] < c1)]
    if not ev: return 0
    c1 = c1 or ev[-1][0]
    out = bytearray(); j = 0; v = 0
    n = int((c1 - c0) / 1e6 * rate)
    for i in range(n):
        t = c0 + i * 1e6 / rate
        while j < len(ev) and ev[j][0] <= t: v = ev[j][1]; j += 1
        out += struct.pack('<h', int((v - 32) * 800))
    w = wave.open(path, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(out)); w.close()
    return n / rate
