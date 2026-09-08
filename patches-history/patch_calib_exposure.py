#!/usr/bin/env python3
# OpticBook 4800: после ребейза на master экспозиция калибровочного прохода
# берётся из dev->settings.exposure_lperiod — это значение опции
# --scan-exposure-time, которую upstream инициализирует один раз при открытии
# из профиля стартового разрешения. В результате калибровка всех групп шла с
# экспозицией 3500 (группа 300); для 600 нужно 5500, для 1200 — 11000 — чип
# при чужой экспозиции под своим тактом отдаёт плоскую заглушку (126 везде),
# коэффициенты уходят, скан чёрный. На 1.2.1 бралось sensor.exposure_lperiod
# и всё работало. Правка: для 4800 калибровка берёт экспозицию из профиля
# калибруемого сенсора (calib_sensor), остальные модели не тронуты.
# Запуск из корня sane-backends:  python3 patch_calib_exposure.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''    session.params.brightness_adjustment = dev->settings.brightness;
    session.params.exposure_lperiod = dev->settings.exposure_lperiod;
    session.params.flags = flags;
    compute_session(dev, session, calib_sensor);
'''
new = '''    session.params.brightness_adjustment = dev->settings.brightness;
    // OpticBook 4800: each CCD clocking group has its own line period; the
    // calibration pass must use the profile of the group being calibrated,
    // not the --scan-exposure-time option value (initialised once at open
    // for the start-up resolution)
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        session.params.exposure_lperiod = calib_sensor.exposure_lperiod;
    } else {
        session.params.exposure_lperiod = dev->settings.exposure_lperiod;
    }
    session.params.flags = flags;
    compute_session(dev, session, calib_sensor);
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
