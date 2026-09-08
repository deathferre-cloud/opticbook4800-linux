#!/usr/bin/env python3
# OpticBook 4800: x_size 212.7 -> 212.0 мм. Замер на 1200: если окно скана
# доходит до последнего пикселя CCD (запас 9 px), чип отдаёт строку со сдвигом
# на несколько пикселей относительно калибровочного прохода — пыль не
# сокращается, полосы; при запасе 33 px и больше сдвига нет. 212.0 мм
# оставляет 33 px до конца линейки. Лист A4 (210) в кадр входит целиком.
# Запуск из корня sane-backends:  python3 patch_xsize2.py
import re, sys
path = 'backend/genesys/tables_model.cpp'
s = open(path).read()
b = s.find('ModelId::PLUSTEK_OPTICBOOK_4800'); e = s.find('s_usb_devices->emplace_back', b)
blk = s[b:e]
m = re.search(r'model\.x_size = ([0-9.]+);', blk)
if b < 0 or not m:
    sys.exit('model.x_size OpticBook 4800 не найден')
print('x_size', m.group(1), '-> 212.0')
blk = blk.replace(m.group(0),
    'model.x_size = 212.0;   // 33 px before the end of the CCD line: a read-out window\n'
    '                          // reaching the last pixels comes back shifted at the full clock', 1)
open(path, 'w').write(s[:b] + blk + s[e:]); print('ok:', path)
