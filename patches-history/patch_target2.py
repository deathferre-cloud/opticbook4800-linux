#!/usr/bin/env python3
# OpticBook 4800: цель белого 0xa000 -> 0x9800 (белый лист уходил в 255).
# Запуск из корня sane-backends:  python3 patch_target2.py
import sys
path = 'backend/genesys/genesys.cpp'
s = open(path).read()
old = '        target_code = 0xa000;\n        {\n'
new = '        target_code = 0x9800;\n        {\n'
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
