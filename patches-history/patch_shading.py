#!/usr/bin/env python3
# OpticBook 4800: включить штатную калибровку затенения genesys (снять флаг
# DISABLE_SHADING_CALIBRATION). Заливка коэффициентов в формате чипа уже есть
# в gl846.cpp (send_shading_data), она просто не использовалась.
# Запуск из корня sane-backends:  python3 patch_shading.py
# Откат:                          python3 patch_shading.py --revert
import sys

path = 'backend/genesys/tables_model.cpp'
src = open(path).read()
beg = src.find('ModelId::PLUSTEK_OPTICBOOK_4800')
if beg < 0:
    sys.exit('блок OpticBook 4800 не найден')
end = src.find('s_usb_devices->emplace_back', beg)
blk = src[beg:end]

on  = '''                  ModelFlag::DISABLE_EXPOSURE_CALIBRATION |
                  ModelFlag::DISABLE_SHADING_CALIBRATION;'''
off = '''                  ModelFlag::DISABLE_EXPOSURE_CALIBRATION;'''
old, new = (off, on) if '--revert' in sys.argv else (on, off)
if blk.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1 — возможно, уже применено' % blk.count(old))
open(path, 'w').write(src[:beg] + blk.replace(old, new) + src[end:])
print('ok:', path, '— затенение', 'ВЫКЛЮЧЕНО' if '--revert' in sys.argv else 'ВКЛЮЧЕНО')
