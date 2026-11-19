"""World English Bible lookup from the official eng-web USFX (assets/webtext/eng-web_usfx.zip)."""
import re, zipfile, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP = os.path.join(ROOT, 'assets', 'webtext', 'eng-web_usfx.zip')
_x = None


def load():
    global _x
    if _x is None:
        with zipfile.ZipFile(ZIP) as z:
            name = [n for n in z.namelist() if n.endswith('_usfx.xml')][0]
            _x = z.read(name).decode('utf-8')
    return _x


def verse(book, ch, v):
    x = load()
    b = re.search(r'<book id="%s">(.*?)</book>' % book, x, re.S).group(1)
    c = re.search(r'<c id="%d"\s*/>(.*?)(?=<c id="%d"\s*/>|$)' % (ch, ch + 1), b, re.S).group(1)
    m = re.search(r'<v id="%d"[^>]*/>(.*?)<ve\s*/>' % v, c, re.S).group(1)
    m = re.sub(r'<f\b.*?</f>', '', m, flags=re.S)
    m = re.sub(r'<x\b.*?</x>', '', m, flags=re.S)
    m = re.sub(r'<[^>]+>', '', m)
    return re.sub(r'\s+', ' ', m).strip()


def passage(book, ch, v1, v2=None):
    return ' '.join(verse(book, ch, v) for v in range(v1, (v2 or v1) + 1))


if __name__ == '__main__':
    import sys
    for spec in sys.argv[1:]:   # e.g. PHP:4:6-7  PSA:4:8
        b, c, v = spec.split(':'); vs = v.split('-')
        print(spec, '=>', passage(b, int(c), int(vs[0]), int(vs[-1])))
