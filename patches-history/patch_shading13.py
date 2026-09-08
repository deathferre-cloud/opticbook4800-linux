#!/usr/bin/env python3
# OpticBook 4800: чип отсчитывает таблицу затенения от startx без
# output_pixel_offset (подобрано по совмещению соринки на стекле: точный сдвиг
# -17 px на 300 dpi = ровно output_pixel_offset группы 300). Берём
# params.startx вместо output_startx; для 600/1200 сдвиг получается сам.
# Запуск из корня sane-backends:  python3 patch_shading13.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''        unsigned src_px = (dev->session.output_startx * sensor.shading_resolution)
                          / dev->session.params.xres;
'''
new = '''        // the chip counts the table from params.startx, i.e. without the
        // sensor's output_pixel_offset (verified by aligning a dust speck)
        unsigned src_px = (dev->session.params.startx * sensor.shading_resolution)
                          / dev->session.params.xres;
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
