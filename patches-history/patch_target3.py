#!/usr/bin/env python3
# OpticBook 4800: цель белого затенения по группам (подобрано на белом листе):
# 300 -> 0x6800 (~232), 600 -> 0x7000 (~234), 1200 -> 0xe000 (~230).
# Переменная OB4800_SHADING_TARGET по-прежнему переопределяет.
# Запуск из корня sane-backends:  python3 patch_target3.py
import sys
path = 'backend/genesys/genesys.cpp'
s = open(path).read()
old = '        target_code = 0x9800;\n        if (const char* e = std::getenv("OB4800_SHADING_TARGET")) {\n'
new = '''        // white target per CCD clocking group, measured on a white sheet so
        // that paper comes out at ~232 after the 1.7 gamma
        switch (sensor.shading_resolution) {
            case 300:  target_code = 0x6800; break;
            case 600:  target_code = 0x7000; break;
            default:   target_code = 0xe000; break;   // 1200
        }
        if (const char* e = std::getenv("OB4800_SHADING_TARGET")) {
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
