#!/usr/bin/env python3
# OpticBook 4800: чип и в сером режиме читает по 12 байт на пиксель (три канала),
# 4-байтная заливка для серого была ошибкой — за её концом (треть кадра) чип
# читал старую память. Возвращаем 12 байт всегда.
# Запуск из корня sane-backends:  python3 patch_shading5.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '        unsigned nch = (dev->session.params.channels == 1) ? 1 : 3;\n'
new = '        unsigned nch = 3;   // the chip reads 12 bytes per pixel in gray mode too\n'
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
