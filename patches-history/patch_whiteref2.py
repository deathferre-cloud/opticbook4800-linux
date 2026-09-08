#!/usr/bin/env python3
# patch_whiteref2.py — перебазирование эталона белого на тёмный уровень текущего прохода.
#
# Причина: в файл эталона пишется сырое белое со своим пьедесталом, а коэффициенты
# считаются как target/(white - dark), где dark берётся из холостых столбцов 5..36
# живой калибровочной строки. Знаменатель получался смешанным: white_файла - dark_живое.
# Ошибка аддитивная и постоянная по ширине, поэтому относительно она максимальна там,
# где сигнал мал — левый склон купола лампы, 8-25 мм (пункт 1a).
#
# Тёмное эталона берётся из него же (столбцы 5..36), формат файла не меняется.
# OB4800_WREF_NODARK=1 отключает перебазирование без пересборки (для A/B).
import sys, os, shutil

SRC = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")

OLD = """                        for (unsigned i = 0; i < n; i++) {
                            dev->white_average_data[i] = static_cast<std::uint16_t>(
                                static_cast<unsigned char>(buf[2*i]) |
                                (static_cast<unsigned char>(buf[2*i+1]) << 8));
                        }
"""

NEW = """                        // OB4800: the file holds raw white including its own dark
                        // pedestal, while shading coefficients are computed against
                        // the dark level of the current pass (dummy columns 5..36).
                        // Rebase the reference so that the denominator stays
                        // white_file - dark_file instead of white_file - dark_live.
                        const unsigned nch = 3;
                        double dlive[3] = { 0, 0, 0 }, dfile[3] = { 0, 0, 0 };
                        bool rebase = (std::getenv("OB4800_WREF_NODARK") == nullptr) &&
                                      n >= 37 * nch &&
                                      dev->white_average_data.size() >= 37 * nch;
                        if (rebase) {
                            for (unsigned c = 0; c < nch; c++) {
                                double sl = 0, sf = 0;
                                for (unsigned x = 5; x < 37; x++) {
                                    unsigned k = x * nch + c;
                                    sl += dev->white_average_data[k];
                                    sf += static_cast<unsigned char>(buf[2 * k]) |
                                          (static_cast<unsigned char>(buf[2 * k + 1]) << 8);
                                }
                                dlive[c] = sl / 32.0;
                                dfile[c] = sf / 32.0;
                            }
                            DBG(DBG_info, "%s: white ref rebase, dark file %.0f/%.0f/%.0f "
                                "live %.0f/%.0f/%.0f\\n", __func__,
                                dfile[0], dfile[1], dfile[2],
                                dlive[0], dlive[1], dlive[2]);
                        }
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
"""

revert = "--revert" in sys.argv
src, dst = (NEW, OLD) if revert else (OLD, NEW)
text = open(SRC, encoding="utf-8").read()
if text.count(src) != 1:
    print("не найдено или не однозначно: вхождений %d — файл не тронут" % text.count(src))
    print("(возможно, правка уже применена)" if text.count(dst) else "")
    sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_whiteref2")
open(SRC, "w", encoding="utf-8").write(text.replace(src, dst, 1))
print("откат выполнен" if revert else "правка применена")
print("бэкап: " + SRC + ".bak_whiteref2")
