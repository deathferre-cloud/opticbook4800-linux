#!/usr/bin/env python3
# OpticBook 4800: genesys_send_shading_coefficient не знает наш сенсор
# («sensor 19 not supported»). Добавляем его в группу LiDE/5600F — там
# коэффициенты считаются в планарном виде (dark,gain по каналам подряд), а
# наш send_shading_data в gl846.cpp именно из планарного вида собирает
# чередование для чипа. Цель белого 0xdc00 (~220/255, у родного драйвера 228).
# Запуск из корня sane-backends:  python3 patch_shading2.py
import sys
path = 'backend/genesys/genesys.cpp'
src = open(path).read()
old = '        case SensorId::CCD_CANON_5600F:\n'
new = old + '        case SensorId::CCD_PLUSTEK_OPTICBOOK_4800:\n'
if src.count(old) != 1:
    sys.exit('якорь найден %d раз, ожидался 1' % src.count(old))
if 'CCD_PLUSTEK_OPTICBOOK_4800:' in src:
    sys.exit('уже применено')
open(path, 'w').write(src.replace(old, new))
print('ok:', path)
