#!/usr/bin/env python3
import csv, sys


class Cache:
    def __init__(self, size=256, line=16, ways=1):
        self.size, self.line, self.ways = size, line, ways
        self.nlines = size // line
        self.nsets = self.nlines // ways
        self.w = (line - 1).bit_length()
        self.d = (self.nsets - 1).bit_length()
        self.sets = [[] for _ in range(self.nsets)]
        self.hits = self.misses = self.writebacks = 0
        self.ever = set()

    def fields(self, addr):
        word = addr & (self.line - 1)
        s = (addr >> self.w) & (self.nsets - 1)
        tag = addr >> (self.w + self.d)
        return tag, s, word

    def access(self, rw, addr):
        tag, s, word = self.fields(addr)
        st = self.sets[s]
        block = addr >> self.w
        for i, e in enumerate(st):
            if e[0] == tag:
                self.hits += 1
                st.append(st.pop(i))
                if rw == 'W':
                    e[1] = True
                return dict(hit=True, tag=tag, set=s, word=word, evicted=None, seen=None)
        self.misses += 1
        evicted = None
        if len(st) == self.ways:
            old = st.pop(0)
            evicted = dict(tag=old[0], dirty=old[1], block=(old[0] << self.d) | s)
            if old[1]:
                self.writebacks += 1
        seen = block in self.ever
        self.ever.add(block)
        st.append([tag, rw == 'W'])
        return dict(hit=False, tag=tag, set=s, word=word, evicted=evicted, seen=seen)

    def dirty_lines(self):
        return [(s, e[0]) for s, st in enumerate(self.sets) for e in st if e[1]]

    @property
    def H(self):
        n = self.hits + self.misses
        return self.hits / n if n else 0.0


def read_trace(path):
    with open(path) as f:
        return [(r['RW'], int(r['adres_hex'], 16)) for r in csv.DictReader(f)]


if __name__ == '__main__':
    t = read_trace(sys.argv[1])
    size, line, ways = (int(v) for v in (sys.argv[2:5] + ['256', '16', '1'][len(sys.argv[2:5]):]))
    c = Cache(size, line, ways)
    for rw, a in t:
        c.access(rw, a)
    print(f'refs={len(t)} hits={c.hits} misses={c.misses} H={c.H:.4f} '
          f'writebacks={c.writebacks} dirty_at_end={len(c.dirty_lines())}')
