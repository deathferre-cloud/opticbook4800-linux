#!/usr/bin/env python3
# OpticBook 4800:
#  1. Белая калибровочная полоса лежит на 20–34 мм от парковки (найдено дампом
#     калибровки 1–31 мм) — ставим y_offset_calib_white 24, y_size_calib_mm 4.
#  2. Калибровочный проход шёл с профилем 1200 dpi (другое тактирование CCD,
#     экспозиция, АЦП), а коэффициенты применялись к сканам групп 300/600 —
#     яркости не совпадали. Теперь каждая группа калибруется своим профилем:
#     shading_resolution = 1200 / shading_factor (300/600/1200), по одному
#     коэффициенту на пиксель, отдаваемый чипом, прореживание = 1.
# Запуск из корня sane-backends:  python3 patch_shading6.py
import re, sys

def block_edit(path, anchor, endmark, edits):
    s = open(path).read()
    b = s.find(anchor)
    if b < 0:
        sys.exit('%s: блок OpticBook 4800 не найден' % path)
    e = s.find(endmark, b)
    blk = s[b:e]
    for old, new in edits:
        if isinstance(old, str):
            if blk.count(old) != 1:
                sys.exit('%s: фрагмент найден %d раз, ожидался 1:\n%s' % (path, blk.count(old), old[:80]))
            blk = blk.replace(old, new)
        else:
            m = old.search(blk)
            if not m:
                sys.exit('%s: не найдено: %s' % (path, old.pattern))
            print('  ', m.group(0).strip(), '->', new.strip())
            blk = blk.replace(m.group(0), new, 1)
    open(path, 'w').write(s[:b] + blk + s[e:])
    print('ok:', path)

block_edit('backend/genesys/tables_model.cpp', 'ModelId::PLUSTEK_OPTICBOOK_4800',
           's_usb_devices->emplace_back', [
    (re.compile(r'model\.y_offset_calib_white = [0-9.]+;'), 'model.y_offset_calib_white = 24.0;'),
    (re.compile(r'model\.y_size_calib_mm = [0-9.]+;'), 'model.y_size_calib_mm = 4.0;'),
])

block_edit('backend/genesys/tables_sensor.cpp', 'SensorId::CCD_PLUSTEK_OPTICBOOK_4800',
           'sensor = Genesys_Sensor();', [
    ('            sensor.shading_resolution = setting.register_dpihw;\n',
     '            // calibrate with the group\'s own CCD clocking and exposure: the\n'
     '            // shading scan runs at the pixel pitch the chip delivers for this\n'
     '            // group (300/600/1200), one coefficient per delivered pixel\n'
     '            sensor.shading_resolution = 1200 / setting.shading_factor;\n'),
    ('            sensor.shading_factor = setting.shading_factor;\n',
     '            sensor.shading_factor = 1;\n'),
])
print('все правки применены')
