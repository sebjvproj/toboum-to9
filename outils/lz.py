"""Compression LZ des écrans (format décodé par UNLZ en 6809 : c<$80 : c+1 littéraux ;
c>=$80 : copie de (c&$7F)+3 octets à distance d sur 16 bits). Reprise de TOetris."""

def lz(data):
    """c<$80 : c+1 littéraux ; c>=$80 : copie de (c&$7F)+3 octets à distance d (16 bits)
    Découpage optimal (programmation dynamique) : même format, ~7 % plus petit qu'un choix glouton."""
    n = len(data)
    # plus longue correspondance (longueur, distance) à chaque position
    table = {}; ml = [(0, 0)] * n
    for i in range(n):
        key = data[i:i+3]; best = (0, 0)
        if len(key) == 3:
            for j in reversed(table.get(key, [])):
                l = 0
                while i+l < n and l < 130 and data[j+l] == data[i+l]: l += 1
                if l > best[0]: best = (l, i - j)
                if l == 130: break
            table.setdefault(key, []).append(i)
        ml[i] = best
    # coût minimal pour atteindre i ; état = 0 après une copie, k = k littéraux en cours
    INF = 10**9
    cost = [dict() for _ in range(n + 1)]; cost[0] = {0: (0, None)}
    for i in range(n):
        for st, (c, _) in list(cost[i].items()):
            ns, nc = (1, c + 2) if st in (0, 128) else (st + 1, c + 1)
            if nc < cost[i+1].get(ns, (INF,))[0]: cost[i+1][ns] = (nc, (i, st, None))
            L, d = ml[i]
            for l in range(3, L + 1):
                if c + 3 < cost[i+l].get(0, (INF,))[0]: cost[i+l][0] = (c + 3, (i, st, (l, d)))
    st = min(cost[n], key=lambda s: cost[n][s][0]); ops = []; i = n
    while i > 0:
        bk = cost[i][st][1]; ops.append(bk); i, st = bk[0], bk[1]
    out = bytearray(); lit = bytearray()
    def flush():
        nonlocal lit
        while lit:
            ch = lit[:128]; out.append(len(ch) - 1); out.extend(ch); lit = lit[128:]
    for i, _, m in reversed(ops):
        if m is None: lit.append(data[i])
        else: flush(); out.append(0x80 | (m[0] - 3)); out += m[1].to_bytes(2, 'big')
    flush()
    return bytes(out)

def unlz(c, n):
    o = bytearray(); i = 0
    while len(o) < n:
        b = c[i]; i += 1
        if b < 0x80: o += c[i:i+b+1]; i += b+1
        else:
            l = (b & 0x7F) + 3; d = c[i] << 8 | c[i+1]; i += 2
            for _ in range(l): o.append(o[-d])
    return bytes(o)
