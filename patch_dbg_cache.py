#!/usr/bin/env python3
# OpticBook 4800: диагностическая печать в лог (уровень 5) — что легло в
# таблицу затенения: белое/тёмное усреднённые, цель, coeff и готовая запись
# для пикселя 1000 (канал G). Нужна, чтобы сравнить путь с калибровкой и путь
# из кэша. Безвредна, можно оставить.
# Запуск из корня sane-backends:  python3 patch_dbg_cache.py
import sys
path = 'backend/genesys/genesys.cpp'
s = open(path).read()
old = '''        compute_coefficients(dev, shading_data.data(), pixels_per_line, 3,
                             ColorOrder::RGB, 0, coeff, target_code);
        break;
'''
new = '''        compute_coefficients(dev, shading_data.data(), pixels_per_line, 3,
                             ColorOrder::RGB, 0, coeff, target_code);
        if (pixels_per_line > 1000) {
            unsigned x = 1000 * 3 + 1;   // pixel 1000, channel G
            const std::uint8_t* r = shading_data.data() + 1000 * 12 + 4;
            DBG(DBG_info, "%s: OB4800 px1000 G: white=%u dark=%u target=0x%x coeff=0x%x "
                          "-> record dark=%u gain=%u (avg sizes %zu/%zu)\\n", __func__,
                x < dev->white_average_data.size() ? dev->white_average_data[x] : 0,
                x < dev->dark_average_data.size() ? dev->dark_average_data[x] : 0,
                target_code, coeff, r[0] | (r[1] << 8), r[2] | (r[3] << 8),
                dev->white_average_data.size(), dev->dark_average_data.size());
        }
        break;
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
