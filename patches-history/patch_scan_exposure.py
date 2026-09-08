#!/usr/bin/env python3
# OpticBook 4800: тот же разрыв после ребейза на master, теперь в сессии скана.
# upstream берёт экспозицию строки из dev->settings.exposure_lperiod (опция
# --scan-exposure-time), инициализированной один раз при открытии для стартового
# разрешения; при смене разрешения она не пересчитывается — скан 600 шёл с
# 3500 вместо 5500 (изображение «накладывается само на себя»: мотор и CCD
# рассинхронизированы), скан 1200 с 3500 вместо 11000 (чип не отдаёт данные,
# зависание). Правка: для 4800 экспозиция скана — из профиля сенсора группы,
# как на 1.2.1. Остальные модели не тронуты.
# Запуск из корня sane-backends:  python3 patch_scan_exposure.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''    session.params.brightness_adjustment = settings.brightness;
    session.params.exposure_lperiod = dev->settings.exposure_lperiod;
    // backtracking isn't handled well, so don't enable it
'''
new = '''    session.params.brightness_adjustment = settings.brightness;
    // OpticBook 4800: each CCD clocking group has its own line period and a
    // matching motor profile; use the sensor profile, not the
    // --scan-exposure-time option (initialised once for the start-up
    // resolution and not updated on resolution change)
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        session.params.exposure_lperiod = sensor.exposure_lperiod;
    } else {
        session.params.exposure_lperiod = dev->settings.exposure_lperiod;
    }
    // backtracking isn't handled well, so don't enable it
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
