#!/usr/bin/env python3
# OpticBook 4800: проверка вменяемости калибровки затенения.
# Если калибровочный проход снял мусор (сканер не успел подняться, лампа не
# зажглась, сбой USB), белое получается почти чёрным, коэффициенты уходят в
# потолок, и все сканы выходят чёрными — а результат ещё и сохраняется в
# кэш ~/.sane/plustek-opticbook-4800.cal, так что чёрные сканы продолжаются
# до ручного удаления файла.
# Правка: после расчёта усреднённого белого проверяем медиану по середине
# строки. Если она ниже 20 % от цели, калибровка считается несостоявшейся:
# бросаем SANE_STATUS_INVAL с понятным текстом (в кэш ничего не попадает,
# следующий запуск калибруется заново).
# Запуск из корня sane-backends:  python3 patch_calib_sanity.py
import sys
path = 'backend/genesys/genesys.cpp'
s = open(path).read()

old = """        target_code = 0xa400;
"""
if s.count(old) != 1:
    sys.exit('якорь цели найден %d раз, ожидался 1 (нужно состояние после patch_target_single.py)'
             % s.count(old))

new = """        target_code = 0xa400;
        {
            // Sanity check: a failed calibration pass (lamp not lit yet, USB
            // hiccup, scanner still waking up) yields near-black "white" data.
            // The coefficients then saturate and every scan comes out black —
            // and the result would be cached, so it would keep happening.
            // Refuse such a calibration instead; the next run calibrates anew.
            unsigned n = std::min<std::size_t>(dev->white_average_data.size(),
                                               pixels_per_line * 3);
            if (n > 300) {
                std::vector<std::uint16_t> mid(dev->white_average_data.begin() + n / 3,
                                               dev->white_average_data.begin() + 2 * n / 3);
                std::nth_element(mid.begin(), mid.begin() + mid.size() / 2, mid.end());
                unsigned median = mid[mid.size() / 2];
                if (median < target_code / 5) {
                    throw SaneException(SANE_STATUS_INVAL,
                        "OpticBook 4800: shading calibration failed, the white reference reads "
                        "%u (expected at least %u). The lamp may not have been lit or the "
                        "scanner was not ready; power-cycle the scanner and try again.",
                        median, target_code / 5);
                }
            }
        }
"""
open(path, 'w').write(s.replace(old, new))
print('ok:', path)

# нужные заголовки
s = open(path).read()
for inc in ('#include <algorithm>', '#include <vector>'):
    if inc not in s:
        s = s.replace('#include "genesys.h"\n', '#include "genesys.h"\n' + inc + '\n', 1)
        print('добавлен', inc)
open(path, 'w').write(s)
