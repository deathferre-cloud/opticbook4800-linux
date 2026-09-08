#!/usr/bin/env python3
# OpticBook 4800: цель белого затенения из переменной OB4800_SHADING_TARGET
# (hex, например 0x7000) — для подбора по группам без пересборок.
# Запуск из корня sane-backends:  python3 patch_target_env.py
import sys
path = 'backend/genesys/genesys.cpp'
s = open(path).read()
old = '        target_code = 0x9800;\n        {\n'
new = '''        target_code = 0x9800;
        if (const char* e = std::getenv("OB4800_SHADING_TARGET")) {
            unsigned t = static_cast<unsigned>(std::strtoul(e, nullptr, 0));
            if (t >= 0x1000 && t <= 0xffff) {
                target_code = t;
            }
        }
        {
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
