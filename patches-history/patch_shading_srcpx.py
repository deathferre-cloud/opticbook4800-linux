#!/usr/bin/env python3
# OpticBook 4800: заливка таблицы затенения читала усреднённую строку с
# индекса startx·shading_resolution/xres (91 на 600, 45 на 300), а genesys
# хранит её со смещением start_offset = startx·full_resolution/xres (182 на
# 600, 180 на 300 — в пикселях полного такта). На 1200 оба равны 183 и всё
# сходилось; на 300/600 таблица брала данные на startx·(full/xres − 1) левее
# нужного — копия каждого провала от пыли вставала на +3.9 мм (600) / +12 мм
# (300) от самого провала (замер сдвигом OB4800_SHADING_SHIFT: провал стоит,
# горб ходит). Правка: читать с того же смещения, с которым genesys хранит
# строку. Хардкода нет — та же формула, что в genesys_shading_calibration_impl.
# Запуск из корня sane-backends:  python3 patch_shading_srcpx.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''        unsigned src_px = (dev->session.params.startx * sensor.shading_resolution)
'''
i = s.find(old)
if i < 0:
    sys.exit('якорь src_px не найден')
# берём всё выражение до ';' включительно
j = s.find(';', i)
expr = s[i:j+1]
print('было:', ' '.join(expr.split()))
new = '''        // The averaged lines are stored with the start offset that genesys uses
        // for them, startx * full_resolution / xres (see
        // genesys_shading_calibration_impl); the table must be read from the
        // same index, otherwise the correction is displaced by
        // startx * (full_resolution / xres - 1) pixels at the lower clockings.
        unsigned src_px = static_cast<unsigned>(
            static_cast<unsigned long long>(dev->session.params.startx) * sensor.full_resolution
            / dev->session.params.xres);'''
s = s[:i] + new + s[j+1:]
open(path, 'w').write(s); print('ok:', path)
