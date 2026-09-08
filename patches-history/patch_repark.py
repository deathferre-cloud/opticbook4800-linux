#!/usr/bin/env python3
# OpticBook 4800: после калибровочного прохода парковать каретку
# (ModelFlag::SHADING_REPARK), чтобы скан всегда стартовал от парковки — как
# из кэша и как при выверке геометрии. Без этого учёт положения головки после
# калибровки для группы 300 давал сдвиг кадра на ~3.8 мм вниз.
# Запуск из корня sane-backends:  python3 patch_repark.py
import sys
path = 'backend/genesys/tables_model.cpp'
s = open(path).read()
b = s.find('ModelId::PLUSTEK_OPTICBOOK_4800'); e = s.find('s_usb_devices->emplace_back', b)
blk = s[b:e]
old = '''    model.flags = ModelFlag::CUSTOM_GAMMA |
                  ModelFlag::DISABLE_ADC_CALIBRATION |
                  ModelFlag::DISABLE_EXPOSURE_CALIBRATION;'''
new = '''    model.flags = ModelFlag::CUSTOM_GAMMA |
                  ModelFlag::SHADING_REPARK |
                  ModelFlag::DISABLE_ADC_CALIBRATION |
                  ModelFlag::DISABLE_EXPOSURE_CALIBRATION;'''
if b < 0 or blk.count(old) != 1:
    sys.exit('фрагмент флагов OpticBook 4800 найден %d раз, ожидался 1' % blk.count(old))
open(path, 'w').write(s[:b] + blk.replace(old, new) + s[e:]); print('ok:', path)
