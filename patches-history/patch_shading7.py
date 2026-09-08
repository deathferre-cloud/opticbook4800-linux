#!/usr/bin/env python3
# OpticBook 4800, заливка коэффициентов затенения:
#  1. Память коэффициентов у чипа страничная: 512 байт на страницу, в странице
#     42 записи по 12 байт (dark/gain × R,G,B), 8 байт хвоста не используются.
#     Мы писали записи подряд — на каждой странице поля съезжали на 8 байт,
#     отсюда ступенчатые полосы шириной 42 px с циклом в 3 страницы.
#  2. Начало таблицы бралось по params.startx без output_pixel_offset —
#     коэффициенты были сдвинуты относительно кадра; берём output_startx.
# Запуск из корня sane-backends:  python3 patch_shading7.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
b = s.find('        unsigned count = pixels / 4;                 // coefficients per channel')
e = s.find('dev->interface->write_ahb(addr, count * 4 * nch, mixed.data());', b)
if b < 0 or e < 0:
    sys.exit('блок заливки OpticBook 4800 не найден (ожидалось состояние после patch_shading5.py)')
e = s.find('\n', e) + 1
new = '''        // the shading table is paged: 512 bytes per page, 42 records of 12 bytes
        // (dark/gain for R, G, B) per page, the last 8 bytes of a page unused
        const unsigned REC = 12, PAGE = 512, PER_PAGE = PAGE / REC;
        unsigned count = pixels / 4;                 // records = delivered pixels
        // table starts at the first pixel of the scan window (SHDAREA):
        // source index in the calibration line, which is at shading_resolution
        unsigned src_px = (dev->session.output_startx * sensor.shading_resolution)
                          / dev->session.params.xres;
        unsigned pages = (count + PER_PAGE - 1) / PER_PAGE;
        std::vector<std::uint8_t> mixed(pages * PAGE, 0);
        for (unsigned n = 0; n < count; n++) {
            std::uint8_t* ptr = mixed.data() + (n / PER_PAGE) * PAGE + (n % PER_PAGE) * REC;
            for (i = 0; i < 3; i++) {
                std::uint8_t* src = data + i * length + (src_px + n) * 4;
                ptr[0] = src[0];
                ptr[1] = src[1];
                ptr[2] = src[2];
                ptr[3] = src[3];
                ptr += 4;
            }
        }
        std::uint8_t val = dev->interface->read_register(0xd0);
        addr = val * 8192 + 0x10000000;
        dev->interface->write_ahb(addr, pages * PAGE, mixed.data());
'''
s = s[:b] + new + s[e:]
open(path, 'w').write(s)
print('ok:', path)
