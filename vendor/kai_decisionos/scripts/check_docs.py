import re, sys, pathlib

root = pathlib.Path('docs')
required = ['TechSpec.md','Plan.md','index.md']
miss = [p for p in required if not (root/p).exists()]
if miss:
    print('MISSING:', miss)
    sys.exit(2)

version_pattern = re.compile(r"v\d+\.\d+\.\d+")
for name in required:
    txt = (root/name).read_text(encoding='utf-8')
    if not version_pattern.search(txt):
        print('NO VERSION TAG:', name)
        sys.exit(3)

print('OK')

