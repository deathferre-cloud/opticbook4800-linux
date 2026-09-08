#!/usr/bin/env python3
# OpticBook 4800: положение белой калибровочной полосы.
# Запуск из корня sane-backends:  python3 patch_calib_y.py <y_offset_calib_white_mm> [<y_size_calib_mm>]
# Например:  python3 patch_calib_y.py 29.0 4.0
import re, sys
if len(sys.argv) < 2:
    sys.exit('укажите y_offset_calib_white в мм, например: python3 patch_calib_y.py 29.0 4.0')
y = float(sys.argv[1]); size = float(sys.argv[2]) if len(sys.argv) > 2 else None
if not (18.0 <= y <= 31.0) or (size is not None and not (1.0 <= size <= 6.0)):
    sys.exit('вне безопасного диапазона: y 18..31 мм, размер 1..6 мм (полоса 20..34 мм, лист с 34)')
path = 'backend/genesys/tables_model.cpp'
s = open(path).read()
b = s.find('ModelId::PLUSTEK_OPTICBOOK_4800'); e = s.find('s_usb_devices->emplace_back', b)
blk = s[b:e]
for k, v in (('y_offset_calib_white', y), ('y_size_calib_mm', size)):
    if v is None: continue
    m = re.search(r'model\.%s = ([0-9.]+);' % k, blk)
    if not m: sys.exit('%s не найден' % k)
    print(k, m.group(1), '->', '%.1f' % v)
    blk = blk.replace(m.group(0), 'model.%s = %.1f;' % (k, v), 1)
open(path, 'w').write(s[:b] + blk + s[e:]); print('ok:', path)
