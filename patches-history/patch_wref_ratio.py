#!/usr/bin/env python3
# OpticBook 4800: на полном такте (1200) эталон белого применяется не подменой
# живой строки, а как плавный множитель к ней.
# Причина: живой калибровочный проход на 1200 идёт в окне скана и видит узкие
# дефекты (пыль на тракте) пиксель в пиксель; эталон же, снятый с другой
# шириной окна, отдаётся чипом со сдвигом на несколько пикселей — подмена
# строки целиком ставила его пыль мимо, и полосы возвращались. Эталону
# оставляем только то, чего живой проход не знает: плавную разницу освещения
# между полосой под рамкой и плоскостью стекла (рябь лампы, масштаб
# миллиметры). Формула: white = dark + (live − dark) · S(file − dark) / S(live − dark),
# S — скользящее среднее ~2.5 мм. Сдвиг файла на пиксели плавной части не
# вредит; ширина при съёмке эталона перестаёт иметь значение.
# 300/600 не тронуты (там подмена работает, полос нет). OB4800_WREF_REPLACE=1
# возвращает старое поведение для A/B.
# Запуск из корня sane-backends:  python3 patch_wref_ratio.py
import sys
path = 'backend/genesys/genesys.cpp'
s = open(path).read()
old = '''                        for (unsigned i = 0; i < n; i++) {
                            double v = static_cast<unsigned char>(buf[2*i]) |
                                       (static_cast<unsigned char>(buf[2*i+1]) << 8);
                            if (rebase) {
                                v += dlive[i % nch] - dfile[i % nch];
                            }
                            if (v < 0) { v = 0; }
                            if (v > 65535) { v = 65535; }
                            dev->white_average_data[i] = static_cast<std::uint16_t>(v + 0.5);
                        }
'''
new = '''                        // At the full CCD clock the live pass runs in the scan's own
                        // window and sees the narrow CCD/dust defects pixel for pixel,
                        // while the chip delivers a reference captured with another
                        // width shifted by a few pixels against it. So use the reference
                        // only for the smooth part — the lamp ripple difference between
                        // the strip under the frame and the glass plane — and keep the
                        // fine structure of the live pass:
                        //   white = dark + (live - dark) * S(file - dark) / S(live - dark)
                        // with S a ~2.5 mm moving average. A few pixels of misalignment
                        // do not matter to the smooth part, so the reference no longer
                        // depends on the width it was captured with.
                        bool ratio_mode = (sensor.shading_resolution == sensor.full_resolution) &&
                                          (std::getenv("OB4800_WREF_REPLACE") == nullptr) &&
                                          (n / nch > cur_sx + 256);
                        if (ratio_mode) {
                            unsigned px = n / nch;
                            unsigned x0 = cur_sx, x1 = px;
                            unsigned W = std::max(32u, sensor.shading_resolution / 10);
                            std::vector<double> live(n), filev(n);
                            for (unsigned i = 0; i < n; i++) {
                                live[i] = dev->white_average_data[i];
                                double v = static_cast<unsigned char>(buf[2*i]) |
                                           (static_cast<unsigned char>(buf[2*i+1]) << 8);
                                if (rebase) {
                                    v += dlive[i % nch] - dfile[i % nch];
                                }
                                filev[i] = v;
                            }
                            for (unsigned c = 0; c < nch; c++) {
                                std::vector<double> pl(x1 - x0 + 1, 0.0), pf(x1 - x0 + 1, 0.0);
                                for (unsigned x = x0; x < x1; x++) {
                                    unsigned k = x * nch + c;
                                    pl[x - x0 + 1] = pl[x - x0] + std::max(0.0, live[k] - dlive[c]);
                                    pf[x - x0 + 1] = pf[x - x0] + std::max(0.0, filev[k] - dlive[c]);
                                }
                                for (unsigned x = x0; x < x1; x++) {
                                    unsigned a = (x >= x0 + W) ? x - W : x0;
                                    unsigned b = std::min(x1, x + W + 1);
                                    double sl = pl[b - x0] - pl[a - x0];
                                    double sf = pf[b - x0] - pf[a - x0];
                                    double r = (sl > 1.0) ? sf / sl : 1.0;
                                    if (r < 0.5) { r = 0.5; }
                                    if (r > 2.0) { r = 2.0; }
                                    unsigned k = x * nch + c;
                                    double v = dlive[c] + std::max(0.0, live[k] - dlive[c]) * r;
                                    if (v > 65535) { v = 65535; }
                                    dev->white_average_data[k] = static_cast<std::uint16_t>(v + 0.5);
                                }
                            }
                            DBG(DBG_info, "%s: white reference applied as a smooth ratio "
                                "(window %u..%u, W=%u)\\n", __func__, x0, x1, W);
                        } else {
                            for (unsigned i = 0; i < n; i++) {
                                double v = static_cast<unsigned char>(buf[2*i]) |
                                           (static_cast<unsigned char>(buf[2*i+1]) << 8);
                                if (rebase) {
                                    v += dlive[i % nch] - dfile[i % nch];
                                }
                                if (v < 0) { v = 0; }
                                if (v > 65535) { v = 65535; }
                                dev->white_average_data[i] = static_cast<std::uint16_t>(v + 0.5);
                            }
                        }
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
