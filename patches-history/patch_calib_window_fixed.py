#!/usr/bin/env python3
# OpticBook 4800: окно калибровки на полном такте (1200) больше не зависит от
# ширины и начала скана. Раньше оно бралось из dev->settings (tl_x, pixels):
# эталон, снятый с -x 215, применялся к скану с -x 210 (или к любой ширине из
# simple-scan) с другим окном — коэффициенты ложились не на те пиксели, и
# провалы от пыли возвращались полосами. Теперь окно фиксированное: старт
# x_offset (183 px на 1200 — с нуля чип одноканальный проход на полном такте
# не выполняет), ширина — вся линейка до конца CCD. Эталон один на режим,
# файл всегда покрывает любое окно скана; индексация таблицы от params.startx
# скана остаётся прежней (белая строка хранится в координатах CCD).
# Запуск из корня sane-backends:  python3 patch_calib_window_fixed.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''        // Single-channel shading pass: use the scan's own window. The chip does
        // not deliver a single-channel read-out that starts at sensor pixel 0 at
        // the full 1200 dpi clock, and a window equal to the scan's lines the
        // reference up with the frame pixel for pixel.
        unsigned full = session.params.pixels;
        unsigned sx = static_cast<unsigned>((dev->model->x_offset + dev->settings.tl_x) *
                                            resolution / MM_PER_INCH);
        unsigned px = static_cast<unsigned>(static_cast<unsigned long long>(dev->settings.pixels) *
                                            resolution / dev->settings.xres);
        if (sx < full && px > 0) {
            if (sx + px > full) {
                px = full - sx;
            }
            session.params.startx = sx;
            session.params.pixels = px;
        }
'''
new = '''        // Shading pass at the full CCD clock: a fixed window from x_offset to
        // the end of the CCD line, independent of the scan area. The chip does
        // not deliver a read-out that starts at sensor pixel 0 at this clock,
        // and the pass must use the scan's read-out mode; tying the window to
        // the scan area instead would make the white reference depend on the
        // requested width, so a reference captured with one width would be
        // misaligned for another.
        unsigned full = session.params.pixels;
        unsigned sx = static_cast<unsigned>(dev->model->x_offset * resolution / MM_PER_INCH);
        if (sx < full) {
            session.params.startx = sx;
            session.params.pixels = full - sx;
        }
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
