#!/usr/bin/env python3
# OpticBook 4800: диагностическая таблица затенения. При переменной окружения
# OB4800_SHADING_TEST=1 вместо коэффициентов калибровки заливается синтетика:
# везде dark=0, gain=0x2000 (единица), а записи 500..519 — gain=0x4000 (×2).
# По положению и ширине светлой полоски на скане видно, как чип индексирует
# таблицу (от окна или от нулевого пикселя, 1:1 или по оптическим пикселям)
# и что 0x2000 действительно единица. Без переменной поведение прежнее.
# Запуск из корня sane-backends:  python3 patch_shading9.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''        std::uint8_t val = dev->interface->read_register(0xd0);
        addr = val * 8192 + 0x10000000;
        dev->interface->write_ahb(addr, pages * PAGE, mixed.data());
'''
new = '''        if (std::getenv("OB4800_SHADING_TEST")) {
            // synthetic table: unity gain everywhere, x2 for records 500..519
            for (unsigned n = 0; n < count; n++) {
                std::uint8_t* ptr = mixed.data() + (n / PER_PAGE) * PAGE + (n % PER_PAGE) * REC;
                unsigned g = (n >= 500 && n < 520) ? 0x4000 : 0x2000;
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
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
