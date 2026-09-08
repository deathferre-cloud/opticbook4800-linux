#!/usr/bin/env python3
# OpticBook 4800, затенение:
#  1. Левый край недокорректирован (103 → 250 за первые 150 px): похоже, чип
#     индексирует таблицу абсолютным номером пикселя CCD, а не от начала окна.
#     Льём всю калибровочную строку целиком с нулевого пикселя.
#  2. Цель белого: полоса даёт 110, бумага на том же профиле 150 — при цели
#     0xdc00 бумага уходит в 255. Ставим 0xac00 (172): 172/110 × 150 ≈ 235.
# Запуск из корня sane-backends:  python3 patch_shading8.py
import sys

def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit('%s: фрагмент найден %d раз, ожидался 1:\n%s' % (path, s.count(old), old[:90]))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path)

edit('backend/genesys/gl846.cpp',
'''        unsigned count = pixels / 4;                 // records = delivered pixels
        // table starts at the first pixel of the scan window (SHDAREA):
        // source index in the calibration line, which is at shading_resolution
        unsigned src_px = (dev->session.output_startx * sensor.shading_resolution)
                          / dev->session.params.xres;
''',
'''        // the chip indexes the table by absolute CCD pixel: upload the whole
        // calibration line starting at pixel 0
        unsigned count = length / 4;                 // records = calibration pixels
        unsigned src_px = 0;
        (void) pixels;
''')

edit('backend/genesys/genesys.cpp',
'''          default:
            target_code = 0xdc00;''',
'''          case SensorId::CCD_PLUSTEK_OPTICBOOK_4800:
                // the calibration strip is ~25% darker than plain paper
                target_code = 0xac00;
            break;
          default:
            target_code = 0xdc00;''')
print('все правки применены')
