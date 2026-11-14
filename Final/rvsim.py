#!/usr/bin/env python3
import re, sys, csv, json

MASK = 0xFFFFFFFF


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def load_listing(path):
    code, syms = {}, {}
    cur = None
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'([0-9a-f]{8}) <(.+)>:', line.strip())
        if m:
            cur = m.group(2); syms[int(m.group(1), 16)] = cur; continue
        m = re.match(r'\s+([0-9a-f]+):\s+([0-9a-f]{8})\s+(.*)', line)
        if m:
            code[int(m.group(1), 16)] = (int(m.group(2), 16), m.group(3).strip(), cur)
    return code, syms


class Mem:
    def __init__(self):
        self.b = {}

    def rd(self, a, n, signed=False):
        v = 0
        for i in range(n):
            v |= self.b.get((a + i) & MASK, 0) << (8 * i)
        return sx(v, 8 * n) & MASK if signed else v

    def wr(self, a, n, v):
        for i in range(n):
            self.b[(a + i) & MASK] = (v >> (8 * i)) & 0xFF


def run(listing, sp0=0x7FFFFFF0, max_steps=10_000_000, dump_range=None):
    code, syms = load_listing(listing)
    entry = [a for a, s in syms.items() if s == '_start'][0]
    x = [0] * 32
    x[2] = sp0
    mem = Mem()
    for a, (w, _, _) in code.items():
        mem.wr(a, 4, w)

    w1, w2 = code[entry][0], code[entry + 4][0]
    gp = (entry + (w1 & 0xFFFFF000) + sx(w2 >> 20, 12)) & MASK
    mem.wr(gp - 984, 4, gp - 2048)
    def auipc_addi(a):
        hi, lo = code[a][0], code[a + 4][0]
        return (a + (hi & 0xFFFFF000) + sx(lo >> 20, 12)) & MASK
    s2i = {v: k for k, v in syms.items()}
    lia = s2i['__libc_init_array']; lfa = s2i['__libc_fini_array']
    init_start = auipc_addi(lia + 0x48)
    fini_start = auipc_addi(lfa + 0x8)
    mem.wr(init_start, 4, s2i['frame_dummy']); mem.wr(init_start + 4, 4, s2i['register_fini'])
    mem.wr(fini_start, 4, s2i['__do_global_dtors_aux'])

    pc = entry
    trace, counts, dump = [], {}, []
    ic = 0
    exit_code = None
    while ic < max_steps:
        w, txt, fn = code[pc]
        op = w & 0x7F; rd = (w >> 7) & 31; f3 = (w >> 12) & 7
        rs1 = (w >> 15) & 31; rs2 = (w >> 20) & 31; f7 = w >> 25
        a, b = x[rs1], x[rs2]
        npc = (pc + 4) & MASK
        cls = 'ALU'; res = None; acc = None
        before = list(x) if dump_range and dump_range[0] <= pc <= dump_range[1] else None
        if op == 0x37:   res = w & 0xFFFFF000
        elif op == 0x17: res = (pc + (w & 0xFFFFF000)) & MASK
        elif op == 0x6F:
            imm = sx(((w >> 31) << 20) | (((w >> 12) & 0xFF) << 12) | (((w >> 20) & 1) << 11) | (((w >> 21) & 0x3FF) << 1), 21)
            res = npc; npc = (pc + imm) & MASK; cls = 'Branch/jump'
        elif op == 0x67:
            res = npc; npc = (a + sx(w >> 20, 12)) & ~1 & MASK; cls = 'Branch/jump'
        elif op == 0x63:
            imm = sx(((w >> 31) << 12) | (((w >> 7) & 1) << 11) | (((w >> 25) & 0x3F) << 5) | (((w >> 8) & 0xF) << 1), 13)
            sa, sb_ = sx(a, 32), sx(b, 32)
            t = {0: a == b, 1: a != b, 4: sa < sb_, 5: sa >= sb_, 6: a < b, 7: a >= b}[f3]
            if t: npc = (pc + imm) & MASK
            cls = 'Branch/jump'
        elif op == 0x03:
            addr = (a + sx(w >> 20, 12)) & MASK
            n = {0: 1, 1: 2, 2: 4, 4: 1, 5: 2}[f3]
            res = mem.rd(addr, n, signed=f3 in (0, 1)); cls = 'Load'; acc = ('R', addr, n)
        elif op == 0x23:
            addr = (a + sx(((w >> 25) << 5) | ((w >> 7) & 31), 12)) & MASK
            n = {0: 1, 1: 2, 2: 4}[f3]
            mem.wr(addr, n, b); cls = 'Store'; acc = ('W', addr, n)
        elif op == 0x13:
            imm = sx(w >> 20, 12) & MASK; sh = (w >> 20) & 31
            if f3 == 0: res = (a + imm) & MASK
            elif f3 == 2: res = int(sx(a, 32) < sx(imm, 32))
            elif f3 == 3: res = int(a < imm)
            elif f3 == 4: res = a ^ imm
            elif f3 == 6: res = a | imm
            elif f3 == 7: res = a & imm
            elif f3 == 1: res = (a << sh) & MASK
            elif f3 == 5: res = (sx(a, 32) >> sh) & MASK if (w >> 30) & 1 else a >> sh
        elif op == 0x33:
            if f7 == 1:
                cls = 'Mul/Div'
                sa, sb_ = sx(a, 32), sx(b, 32)
                if f3 == 0: res = (a * b) & MASK
                elif f3 == 1: res = ((sa * sb_) >> 32) & MASK
                elif f3 == 3: res = ((a * b) >> 32) & MASK
                elif f3 == 4: res = MASK if b == 0 else (int(sa / sb_) & MASK)
                elif f3 == 5: res = MASK if b == 0 else a // b
                elif f3 == 6: res = a if b == 0 else (sa - sb_ * int(sa / sb_)) & MASK
                elif f3 == 7: res = a if b == 0 else a % b
            else:
                if f3 == 0: res = (a - b) & MASK if f7 == 0x20 else (a + b) & MASK
                elif f3 == 1: res = (a << (b & 31)) & MASK
                elif f3 == 2: res = int(sx(a, 32) < sx(b, 32))
                elif f3 == 3: res = int(a < b)
                elif f3 == 4: res = a ^ b
                elif f3 == 5: res = (sx(a, 32) >> (b & 31)) & MASK if f7 == 0x20 else a >> (b & 31)
                elif f3 == 6: res = a | b
                elif f3 == 7: res = a & b
        elif op == 0x73:
            cls = 'Branch/jump'
            if x[17] == 93:
                exit_code = x[10]
        else:
            raise RuntimeError(f'Unknown instruction {w:08x} @ {pc:#x}')
        if res is not None and rd:
            x[rd] = res & MASK
        counts[cls] = counts.get(cls, 0) + 1
        ic += 1
        if acc:
            trace.append((acc[0], acc[1], acc[2], pc, fn))
        if before is not None:
            dump.append(dict(pc=pc, npc=npc, w=w, txt=txt, before=before, after=list(x), acc=acc, ic=ic,
                             tidx=len(trace),
                             mem_val=(mem.rd(acc[1], acc[2]) if acc else None)))
        if exit_code is not None:
            break
        pc = npc
    return dict(ic=ic, counts=counts, trace=trace, mem=mem, gp=gp, exit_code=exit_code, dump=dump, x=x)


if __name__ == '__main__':
    r = run(sys.argv[1])
    print('Ic =', r['ic'], r['counts'], 'exit', r['exit_code'], 'gp', hex(r['gp']), 'data refs', len(r['trace']))
