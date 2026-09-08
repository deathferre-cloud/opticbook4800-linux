#!/usr/bin/env python3
# OpticBook 4800: подбор усиления АЦП. Переменная OB4800_AFE_GAIN_DELTA=<целое>
# прибавляется к младшему байту кодов усиления (регистры АЦП 5-7:
# 0x114/0x10c/0x10d) — для поиска значений под группу 1200, где сырое
# насыщается. Без переменной поведение прежнее.
# Запуск из корня sane-backends:  python3 patch_afe.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''        dev->interface->write_fe_register(0x05, 0x114);
        dev->interface->write_fe_register(0x06, 0x10c);
        dev->interface->write_fe_register(0x07, 0x10d);
'''
new = '''        unsigned gain[3] = { 0x114, 0x10c, 0x10d };
        if (const char* e = std::getenv("OB4800_AFE_GAIN_DELTA")) {
            int d = std::atoi(e);
            for (unsigned k = 0; k < 3; k++) {
                int v = static_cast<int>(gain[k] & 0xff) + d;
                v = v < 0 ? 0 : (v > 255 ? 255 : v);
                gain[k] = (gain[k] & 0x100) | static_cast<unsigned>(v);
            }
        }
        dev->interface->write_fe_register(0x05, gain[0]);
        dev->interface->write_fe_register(0x06, gain[1]);
        dev->interface->write_fe_register(0x07, gain[2]);
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
