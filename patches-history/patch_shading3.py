#!/usr/bin/env python3
# OpticBook 4800: в сером режиме чип читает по одному коэффициенту на пиксель
# (4 байта), а мы заливали чередование трёх каналов (12 байт) — отсюда полосы
# с периодом 3 столбца. Для серого шлём один канал; какой именно, выбирается
# переменной окружения OB4800_SHADING_CH (0/1/2, по умолчанию 1 = зелёный) —
# для подбора. Цвет остаётся как был.
# Запуск из корня sane-backends:  python3 patch_shading3.py
import sys
path = 'backend/genesys/gl846.cpp'
src = open(path).read()

def edit(old, new):
    global src
    if src.count(old) != 1:
        sys.exit('фрагмент найден %d раз, ожидался 1:\n%s' % (src.count(old), old[:90]))
    src = src.replace(old, new)

edit('#include <vector>\n', '#include <vector>\n#include <cstdlib>\n')

edit('''        unsigned count = pixels / 4;                 // coefficients per channel
        std::vector<std::uint8_t> mixed(count * 12, 0);
        std::uint8_t* ptr = mixed.data();
        for (unsigned n = 0; n < count; n++) {
            for (i = 0; i < 3; i++) {
                std::uint8_t* src = data + offset * sensor.shading_factor
                                    + i * length + n * 4 * sensor.shading_factor;''',
'''        unsigned count = pixels / 4;                 // coefficients per channel
        // gray scans: one coefficient per pixel, taken from a single channel
        unsigned nch = (dev->session.params.channels == 1) ? 1 : 3;
        unsigned gray_ch = 1;
        if (const char* e = std::getenv("OB4800_SHADING_CH")) {
            gray_ch = std::atoi(e) % 3;
        }
        std::vector<std::uint8_t> mixed(count * 4 * nch, 0);
        std::uint8_t* ptr = mixed.data();
        for (unsigned n = 0; n < count; n++) {
            for (unsigned k = 0; k < nch; k++) {
                i = (nch == 1) ? gray_ch : k;
                std::uint8_t* src = data + offset * sensor.shading_factor
                                    + i * length + n * 4 * sensor.shading_factor;''')

edit('        dev->interface->write_ahb(addr, count * 12, mixed.data());',
     '        dev->interface->write_ahb(addr, count * 4 * nch, mixed.data());')
open(path, 'w').write(src)
print('ok:', path)
