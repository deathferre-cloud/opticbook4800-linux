#!/usr/bin/env python3
# OpticBook 4800: усреднённые калибровочные строки genesys хранит с чередованием
# каналов (R,G,B на пиксель — видно по дампу), а compute_planar_coefficients из
# группы LiDE читает их как планарные — коэффициент пикселя x считался по
# белому пикселя x/3, кривая растягивалась втрое. Переводим расчёт на
# compute_coefficients (чередующийся вход, на выходе сразу записи по 12 байт
# dark/gain × R,G,B — формат чипа), а заливка просто раскладывает записи по
# страницам 512 байт. Цель белого 0xac00. Диагностика OB4800_SHADING_TEST сохранена.
# Запуск из корня sane-backends:  python3 patch_shading11.py
import sys

def edit(path, old, new, count=1):
    s = open(path).read()
    if s.count(old) != count:
        sys.exit('%s: фрагмент найден %d раз, ожидался %d:\n%s' % (path, s.count(old), count, old[:90]))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path)

# ---------- genesys.cpp ----------
edit('backend/genesys/genesys.cpp',
'''          case SensorId::CCD_PLUSTEK_OPTICBOOK_4800:
                // the calibration strip is ~25% darker than plain paper
                target_code = 0xac00;
            break;
''', '')
edit('backend/genesys/genesys.cpp',
'''        case SensorId::CCD_CANON_5600F:
        case SensorId::CCD_PLUSTEK_OPTICBOOK_4800:
''',
'''        case SensorId::CCD_CANON_5600F:
''')
edit('backend/genesys/genesys.cpp',
'''    case SensorId::CIS_CANON_LIDE_700F:
    case SensorId::CIS_CANON_LIDE_100:
''',
'''    case SensorId::CCD_PLUSTEK_OPTICBOOK_4800:
        // averages are channel-interleaved; compute_coefficients produces the
        // chip's own record layout: dark, gain for R, G, B per pixel (12 bytes).
        // The calibration strip is ~25% darker than plain paper, hence the target.
        target_code = 0xac00;
        length = pixels_per_line * 12;
        shading_data.clear();
        shading_data.resize(length, 0);
        compute_coefficients(dev, shading_data.data(), pixels_per_line, 3,
                             ColorOrder::RGB, 0, coeff, target_code);
        break;
    case SensorId::CIS_CANON_LIDE_700F:
    case SensorId::CIS_CANON_LIDE_100:
''')

# ---------- gl846.cpp ----------
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
b = s.find('        // the shading table is paged: 512 bytes per page')
e = s.find('        dev->interface->write_ahb(addr, pages * PAGE, mixed.data());', b)
if b < 0 or e < 0:
    sys.exit('gl846.cpp: блок заливки не найден (ожидалось состояние после patch_shading9/10)')
e = s.find('\n', e) + 1
new = '''        // the shading table is paged: 512 bytes per page, 42 records of 12 bytes
        // (dark/gain for R, G, B) per page, the last 8 bytes of a page unused.
        // data already holds one 12-byte record per calibration pixel; the chip
        // indexes the table from the first pixel of the scan window
        const unsigned REC = 12, PAGE = 512, PER_PAGE = PAGE / REC;
        unsigned count = static_cast<unsigned>(size) / REC;
        unsigned src_px = (dev->session.output_startx * sensor.shading_resolution)
                          / dev->session.params.xres;
        if (src_px < count) {
            count -= src_px;
        } else {
            count = 0;
        }
        unsigned pages = (count + PER_PAGE - 1) / PER_PAGE;
        std::vector<std::uint8_t> mixed(pages * PAGE, 0);
        for (unsigned n = 0; n < count; n++) {
            std::uint8_t* ptr = mixed.data() + (n / PER_PAGE) * PAGE + (n % PER_PAGE) * REC;
            std::memcpy(ptr, data + (src_px + n) * REC, REC);
        }
        (void) pixels;
        (void) length;
        if (std::getenv("OB4800_SHADING_TEST")) {
            // synthetic table: unity gain everywhere, test stripes:
            // 500-519 x2, 560-579 x4, 620-639 x6, 680-699 x0.5, 740-759 x1.5
            for (unsigned n = 0; n < count; n++) {
                std::uint8_t* ptr = mixed.data() + (n / PER_PAGE) * PAGE + (n % PER_PAGE) * REC;
                unsigned g = 0x2000;
                if (n >= 500 && n < 520) g = 0x4000;
                if (n >= 560 && n < 580) g = 0x8000;
                if (n >= 620 && n < 640) g = 0xC000;
                if (n >= 680 && n < 700) g = 0x1000;
                if (n >= 740 && n < 760) g = 0x3000;
                for (i = 0; i < 3; i++) {
                    ptr[0] = 0; ptr[1] = 0;
                    ptr[2] = g & 0xff; ptr[3] = g >> 8;
                    ptr += 4;
                }
            }
        }
        std::uint8_t val = dev->interface->read_register(0xd0);
        addr = val * 8192 + 0x10000000;
        dev->interface->write_ahb(addr, pages * PAGE, mixed.data());
'''
s = s[:b] + new + s[e:]
if '#include <cstring>' not in s:
    s = s.replace('#include <cstdlib>\n', '#include <cstdlib>\n#include <cstring>\n', 1)
open(path, 'w').write(s)
print('ok:', path)
print('все правки применены')
