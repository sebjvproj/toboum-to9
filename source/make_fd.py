"""Crée une disquette Thomson DOS (.fd, 80 pistes x 16 secteurs x 256 octets).
Usage : python3 make_fd.py PROG.BIN sortie.fd   (repris de TOetris, nom du programme = nom du .BIN)"""
import sys, datetime

TRACKS, SECT, SSIZE = 80, 16, 256
USE = 255                                 # le DOS Thomson n'utilise que 255 octets par secteur
NBLOCKS = TRACKS * 2                      # 1 bloc = 8 secteurs (demi-piste)
img = bytearray(b'\xE5' * (TRACKS * SECT * SSIZE))

def sector(track, s):                      # s = 1..16
    o = (track * SECT + s - 1) * SSIZE
    return o

def put_sector(track, s, data):
    data = bytes(data) + b'\x00' * (SSIZE - len(data))
    o = sector(track, s); img[o:o + SSIZE] = data

# piste 20 : nom (secteur 1), FAT (secteur 2), catalogue (secteurs 3-16)
NAME = __import__('os').path.splitext(__import__('os').path.basename(sys.argv[1]))[0].upper()[:8]
put_sector(20, 1, NAME.ljust(8).encode() + b'\xFF' * (SSIZE - 8))
fat = bytearray(b'\xFF' * SSIZE)
fat[0] = 0
fat[1 + 40] = fat[1 + 41] = 0xFE           # blocs de la piste 20 réservés
for s in range(3, 17): put_sector(20, s, b'\xFF' * SSIZE)
directory = []
next_block = [42]

def add_file(name, ext, ftype, flag, data, comment=b''):
    nsec = max(1, (len(data) + USE - 1) // USE)
    nblk = (nsec + 7) // 8
    blocks = list(range(next_block[0], next_block[0] + nblk)); next_block[0] += nblk
    for i, blk in enumerate(blocks):
        track, first = blk // 2, 1 + 8 * (blk % 2)
        for k in range(8):
            chunk = data[(i * 8 + k) * USE:(i * 8 + k + 1) * USE]
            if chunk: put_sector(track, first + k, chunk)
        if i < nblk - 1: fat[1 + blk] = blocks[i + 1]
        else: fat[1 + blk] = 0xC0 + (nsec - 8 * i)
    last = len(data) - (nsec - 1) * USE
    d = datetime.date.today()
    e = bytearray(b'\x00' * 32)
    e[0:8] = name.ljust(8).encode()[:8]; e[8:11] = ext.ljust(3).encode()[:3]
    e[11] = ftype; e[12] = flag; e[13] = blocks[0]
    e[14], e[15] = last >> 8, last & 0xFF
    e[16:24] = comment.ljust(8)[:8]
    e[24], e[25], e[26] = d.day, d.month, d.year % 100
    directory.append(bytes(e))

binary = open(sys.argv[1], 'rb').read()
add_file(NAME, 'BIN', 2, 0x00, binary, NAME.encode())
# chargeur BASIC tokenisé : 10 CLEAR,&H9FFF / 20 LOADM"<NOM>.BIN" / 30 EXEC&HA000
def line(num, toks):
    body = num.to_bytes(2, 'big') + toks + b'\x00'
    return (len(body) + 2).to_bytes(2, 'big') + body
prog = (line(10, b'\xae,&H9FFF') + line(20, b'\xb3M"' + NAME.encode() + b'.BIN"') +
        line(30, b'\xa2&HA000') + b'\x00\x00')
loader = b'\xff' + len(prog).to_bytes(2, 'big') + prog
add_file(NAME, 'BAS', 0, 0x00, loader, b'LANCEUR')
add_file('AUTO', 'BAT', 0, 0x00, loader, b'')

put_sector(20, 2, fat)
cat = b''.join(directory)
cat += b'\xFF' * (SSIZE - len(cat))
put_sector(20, 3, cat[:256])
open(sys.argv[2], 'wb').write(img)
print('fd ok:', len(img), 'octets,', len(binary), 'octets de binaire')
