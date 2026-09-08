#!/usr/bin/env python3
# OpticBook 4800: правило калибровки «в окне скана, в режиме считывания
# скана, с тёмным проходом, эталон — плавный множитель», отлаженное на 1200,
# распространяется на все группы (300/600). Замер на 600 показал тот же сдвиг
# окна калибровки относительно скана (пыль в проходе на 31.0 мм, в скане на
# 31.5 — 12 px), из-за которого после подмены строки оставался остаток ±2 %.
# Условие «только полный такт» снимается в пяти местах; OB4800_CALIB_LEGACY=1
# возвращает старое поведение для 300/600 (для A/B). После патча эталоны
# 300/600 переснять: серые пойдут в -300-gray.dat / -600-gray.dat, цветные в
# -300.dat / -600.dat, в новом окне (заголовок OB4800WREF2 ... <startx>).
# Запуск из корня sane-backends:  python3 patch_calib_allgroups.py
import sys

def edit(path, old, new, what):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit('%s: %s — фрагмент найден %d раз, ожидался 1' % (path, what, s.count(old)))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path, '—', what)

helper = '''
// OpticBook 4800: the shading pass runs in the scan's own window and read-out
// mode, with a lamp-off dark pass; this used to be limited to the full CCD
// clock, OB4800_CALIB_LEGACY=1 restores that limit for A/B comparison.
static bool ob4800_scan_window_calibration(const Genesys_Sensor& sensor, unsigned resolution)
{
    if (std::getenv("OB4800_CALIB_LEGACY") != nullptr) {
        return resolution == sensor.full_resolution;
    }
    return true;
}
'''

# ---- gl846.cpp: хелпер + два условия
s = open('backend/genesys/gl846.cpp').read()
if 'ob4800_scan_window_calibration' not in s:
    anchor = 'static void gl846_set_adi_fe('
    assert s.count(anchor) == 1, 'якорь для хелпера в gl846.cpp'
    s = s.replace(anchor, helper.lstrip('\n') + '\n' + anchor, 1)
    if '#include <cstdlib>' not in s:
        s = s.replace('#include "gl846.h"\n', '#include "gl846.h"\n#include <cstdlib>\n', 1)
    open('backend/genesys/gl846.cpp', 'w').write(s); print('ok: gl846.cpp — хелпер')

edit('backend/genesys/gl846.cpp',
'''        dev->settings.get_channels() == 1 &&
        resolution == sensor.full_resolution) {
''',
'''        dev->settings.get_channels() == 1 &&
        ob4800_scan_window_calibration(sensor, resolution)) {
''', 'число каналов калибровки')

edit('backend/genesys/gl846.cpp',
'''    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
        resolution == sensor.full_resolution) {
        // Single-channel shading pass: use the scan's own window. The chip does
''',
'''    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
        ob4800_scan_window_calibration(sensor, resolution)) {
        // Single-channel shading pass: use the scan's own window. The chip does
''', 'окно калибровки')

# ---- genesys.cpp: хелпер + три условия
s = open('backend/genesys/genesys.cpp').read()
if 'ob4800_scan_window_calibration' not in s:
    anchor = 'static void genesys_send_shading_coefficient('
    if s.count(anchor) != 1:
        anchor = 'static void genesys_shading_calibration_impl('
    assert s.count(anchor) == 1, 'якорь для хелпера в genesys.cpp'
    s = s.replace(anchor, helper.lstrip('\n') + '\n' + anchor, 1)
    open('backend/genesys/genesys.cpp', 'w').write(s); print('ok: genesys.cpp — хелпер')

edit('backend/genesys/genesys.cpp',
'''               (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
                dev->calib_session.params.xres == sensor.full_resolution)) {
''',
'''               (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
                ob4800_scan_window_calibration(sensor, dev->calib_session.params.xres))) {
''', 'лампа после тёмного прохода')

edit('backend/genesys/genesys.cpp',
'''                        bool ratio_mode = (sensor.shading_resolution == sensor.full_resolution) &&
''',
'''                        bool ratio_mode = ob4800_scan_window_calibration(sensor, sensor.shading_resolution) &&
''', 'эталон как множитель')

edit('backend/genesys/genesys.cpp',
'''                                    std::getenv("OB4800_CALIB_3CH") == nullptr &&
                                    sensor.shading_resolution == sensor.full_resolution;
''',
'''                                    std::getenv("OB4800_CALIB_3CH") == nullptr &&
                                    ob4800_scan_window_calibration(sensor, sensor.shading_resolution);
''', 'тёмный проход')
print('готово')
