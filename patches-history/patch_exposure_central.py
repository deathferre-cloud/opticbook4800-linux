#!/usr/bin/env python3
# OpticBook 4800: одна точка истины для экспозиции строки.
# Upstream (master) берёт session.params.exposure_lperiod из опции
# --scan-exposure-time (dev->settings.exposure_lperiod) в девяти местах
# (сессия скана, калибровка затенения и внутренние калибровки genesys).
# Опция инициализируется один раз при открытии и не пересчитывается при
# смене разрешения; у 4800 экспозиция жёстко привязана к такту CCD и
# профилю мотора группы (3500/5500/11000), поэтому для этой модели значение
# опции игнорируется: compute_session() — единственная воронка, через
# которую проходит каждая сессия, — подставляет sensor.exposure_lperiod
# той группы, для которой сессия считается. Две прежние точечные правки в
# gl846.cpp (patch_calib_exposure / patch_scan_exposure) возвращаются к
# upstream-виду — они больше не нужны.
# Запуск из корня sane-backends:  python3 patch_exposure_central.py
import sys

def edit(path, old, new, what):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit('%s: %s — фрагмент найден %d раз, ожидался 1' % (path, what, s.count(old)))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path, '—', what)

# 1. центральная подстановка
edit('backend/genesys/low.cpp',
'''void compute_session(const Genesys_Device* dev, ScanSession& s, const Genesys_Sensor& sensor)
{
    DBG_HELPER(dbg);

    (void) dev;
    s.params.assert_valid();
''',
'''void compute_session(const Genesys_Device* dev, ScanSession& s, const Genesys_Sensor& sensor)
{
    DBG_HELPER(dbg);

    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        // The line period of this scanner is tied to the CCD clocking group and
        // its motor profile (3500 / 5500 / 11000). Every session — scan, shading
        // and the internal calibrations — must use the period of the sensor
        // profile it is computed for; the --scan-exposure-time option (set once
        // at open for the start-up resolution) is ignored for this model.
        s.params.exposure_lperiod = sensor.exposure_lperiod;
    }
    s.params.assert_valid();
''', 'exposure из профиля сенсора в compute_session')

# 2. откат точечных правок в gl846.cpp к upstream-виду
edit('backend/genesys/gl846.cpp',
'''    // OpticBook 4800: each CCD clocking group has its own line period and a
    // matching motor profile; use the sensor profile, not the
    // --scan-exposure-time option (initialised once for the start-up
    // resolution and not updated on resolution change)
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        session.params.exposure_lperiod = sensor.exposure_lperiod;
    } else {
        session.params.exposure_lperiod = dev->settings.exposure_lperiod;
    }
''',
'''    session.params.exposure_lperiod = dev->settings.exposure_lperiod;
''', 'откат точечной правки в сессии скана')

edit('backend/genesys/gl846.cpp',
'''    // OpticBook 4800: each CCD clocking group has its own line period; the
    // calibration pass must use the profile of the group being calibrated,
    // not the --scan-exposure-time option value (initialised once at open
    // for the start-up resolution)
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        session.params.exposure_lperiod = calib_sensor.exposure_lperiod;
    } else {
        session.params.exposure_lperiod = dev->settings.exposure_lperiod;
    }
''',
'''    session.params.exposure_lperiod = dev->settings.exposure_lperiod;
''', 'откат точечной правки в калибровке')
print('все правки применены')
