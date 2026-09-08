#!/usr/bin/env python3
# OpticBook 4800: расширенная диагностика таблицы затенения (OB4800_SHADING_TEST=1):
# пять полосок с разным gain, чтобы снять передаточную характеристику чипа:
#   500-519: 0x4000 (x2)   560-579: 0x8000 (x4)   620-639: 0xC000 (x6)
#   680-699: 0x1000 (x0.5) 740-759: 0x3000 (x1.5)
# Запуск из корня sane-backends:  python3 patch_shading10.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '                unsigned g = (n >= 500 && n < 520) ? 0x4000 : 0x2000;\n'
new = '''                unsigned g = 0x2000;
                if (n >= 500 && n < 520) g = 0x4000;
                if (n >= 560 && n < 580) g = 0x8000;
                if (n >= 620 && n < 640) g = 0xC000;
                if (n >= 680 && n < 700) g = 0x1000;
                if (n >= 740 && n < 760) g = 0x3000;
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
