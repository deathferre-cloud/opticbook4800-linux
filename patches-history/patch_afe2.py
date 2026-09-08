#!/usr/bin/env python3
# OpticBook 4800: подбор АЦП, вторая переменная. OB4800_AFE_OFS_DELTA=<целое>
# прибавляется к регистрам АЦП 2-4 (0x3e/0x34/0x39). OB4800_AFE_GAIN_DELTA
# (регистры 5-7) остаётся.
# Запуск из корня sane-backends:  python3 patch_afe2.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''        dev->interface->write_fe_register(0x02, 0x3e);
        dev->interface->write_fe_register(0x03, 0x34);
        dev->interface->write_fe_register(0x04, 0x39);
'''
new = '''        unsigned ofs[3] = { 0x3e, 0x34, 0x39 };
        if (const char* e = std::getenv("OB4800_AFE_OFS_DELTA")) {
            int d = std::atoi(e);
            for (unsigned k = 0; k < 3; k++) {
                int v = static_cast<int>(ofs[k]) + d;
                ofs[k] = static_cast<unsigned>(v < 0 ? 0 : (v > 255 ? 255 : v));
            }
        }
        dev->interface->write_fe_register(0x02, ofs[0]);
        dev->interface->write_fe_register(0x03, ofs[1]);
        dev->interface->write_fe_register(0x04, ofs[2]);
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
