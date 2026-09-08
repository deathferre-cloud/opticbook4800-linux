#!/usr/bin/env python3
# OpticBook 4800: настройки АЦП выбирались по dev->session.params.xres, а он в
# момент set_fe ещё не обновлён под текущий скан (без калибровочного прохода
# перед сканом там мусор от прошлого раза) — из кэша калибровки АЦП получал
# режим 1200 и сниженное усиление. Берём группу из сенсора, передаваемого в
# set_fe: sensor.shading_resolution = 300/600/1200.
# Запуск из корня sane-backends:  python3 patch_afe4.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()

def edit(old, new):
    global s
    if s.count(old) != 1:
        sys.exit('фрагмент найден %d раз, ожидался 1:\n%s' % (s.count(old), old[:90]))
    s = s.replace(old, new)

edit('static void gl846_set_adi_fe(Genesys_Device* dev, std::uint8_t set)\n',
     'static void gl846_set_adi_fe(Genesys_Device* dev, const Genesys_Sensor& sensor, std::uint8_t set)\n')
edit('        gl846_set_adi_fe(dev, set);\n',
     '        gl846_set_adi_fe(dev, sensor, set);\n')
edit('''        dev->interface->write_fe_register(0x00, dev->session.params.xres >= 1200 ? 0xf8 : 0x70);
''',
'''        // the CCD clocking group of the session being set up: 300/600/1200.
        // (dev->session is not yet updated at this point, so it must not be used)
        unsigned pitch = sensor.shading_resolution;
        dev->interface->write_fe_register(0x00, pitch >= 1200 ? 0xf8 : 0x70);
''')
edit('''        unsigned xres = dev->session.params.xres;
        if (xres == 200 || xres >= 600) {
''',
'''        if (pitch >= 600) {
''')
open(path, 'w').write(s); print('ok:', path)
