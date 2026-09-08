#!/usr/bin/env python3
# OpticBook 4800: калибровочные проходы (тёмный/белый) genesys снимает в 16 бит
# и читает сырые данные мимо конвейера. Наш чип отдаёт 8 бит — genesys видел
# в каждом 16-битном слове два соседних байта RGB, отсюда мусор с периодом 3
# и полосы. Правка: калибровка на 4800 идёт в 8 бит, прочитанные байты
# расширяются до 16 бит (v<<8|v), дальше всё штатно.
# Запуск из корня sane-backends:  python3 patch_shading4.py
import sys

def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit('%s: фрагмент найден %d раз, ожидался 1:\n%s' % (path, s.count(old), old[:90]))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path)

edit('backend/genesys/gl846.cpp',
'''    session.params.depth = 16;
''',
'''    // OpticBook 4800: the chip delivers 8 bit data only; the calibration
    // reader widens it to 16 bit
    session.params.depth = (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) ? 8 : 16;
''')

edit('backend/genesys/genesys.cpp',
'''    sanei_genesys_read_data_from_scanner(dev, reinterpret_cast<std::uint8_t*>(calibration_data.data()),
                                         size);
''',
'''    if (dev->calib_session.params.depth == 8) {
        // 8 bit calibration scan (OpticBook 4800): read bytes, widen to 16 bit
        std::vector<std::uint8_t> raw8(size / 2);
        sanei_genesys_read_data_from_scanner(dev, raw8.data(), raw8.size());
        for (std::size_t i = 0; i < raw8.size(); ++i) {
            calibration_data[i] = static_cast<std::uint16_t>((raw8[i] << 8) | raw8[i]);
        }
    } else {
        sanei_genesys_read_data_from_scanner(dev, reinterpret_cast<std::uint8_t*>(calibration_data.data()),
                                             size);
    }
''')
print('все правки применены')
