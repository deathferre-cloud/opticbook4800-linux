#!/usr/bin/env python3
# OpticBook 4800: цель белого 0xac00 -> 0xa000 (справа упиралось в 255);
# сдвиг таблицы относительно окна подбирается переменной OB4800_SHADING_SHIFT
# (целое, пиксели калибровочной строки, может быть отрицательным).
# Запуск из корня sane-backends:  python3 patch_shading12.py
import sys

def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit('%s: фрагмент найден %d раз, ожидался 1:\n%s' % (path, s.count(old), old[:90]))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path)

edit('backend/genesys/genesys.cpp',
     '        target_code = 0xac00;\n        length = pixels_per_line * 12;',
     '        target_code = 0xa000;\n        length = pixels_per_line * 12;')

edit('backend/genesys/gl846.cpp',
'''        unsigned src_px = (dev->session.output_startx * sensor.shading_resolution)
                          / dev->session.params.xres;
        if (src_px < count) {''',
'''        unsigned src_px = (dev->session.output_startx * sensor.shading_resolution)
                          / dev->session.params.xres;
        if (const char* e = std::getenv("OB4800_SHADING_SHIFT")) {
            int sh = std::atoi(e);
            src_px = (sh < 0 && static_cast<unsigned>(-sh) > src_px) ? 0 : src_px + sh;
        }
        if (src_px < count) {''')
print('все правки применены')
