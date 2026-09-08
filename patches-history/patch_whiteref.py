#!/usr/bin/env python3
# OpticBook 4800: эталон белого по листу на стекле.
#  - OB4800_CALIB_Y_MM=<мм>   — разовое переопределение положения калибровочного
#                               прохода (для съёмки эталона: лист лежит на стекле,
#                               берём 40 мм).
#  - OB4800_WHITE_REF_SAVE=1  — после калибровки сохранить усреднённую белую
#                               строку (16 бит, R,G,B на пиксель, линейная, в
#                               координатах CCD) в
#                               ~/.sane/opticbook4800-white-<shading_dpi>.dat
#  - без переменных: если файл для группы (300/600/1200) есть — белое берётся из
#    него вместо полосы под рамкой; нет — как раньше, с полосы.
# Запуск из корня sane-backends:  python3 patch_whiteref.py
import sys

def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit('%s: фрагмент найден %d раз, ожидался 1:\n%s' % (path, s.count(old), old[:90]))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path)

# ---------- gl846.cpp: положение калибровки из переменной ----------
edit('backend/genesys/gl846.cpp',
'''        move = static_cast<int>(dev->model->y_offset_calib_white);
    }
''',
'''        move = static_cast<int>(dev->model->y_offset_calib_white);
        if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
            // white reference capture: calibrate on a sheet lying on the glass
            if (const char* e = std::getenv("OB4800_CALIB_Y_MM")) {
                float y = static_cast<float>(std::atof(e));
                if (y >= 18.0f && y <= 60.0f) {
                    move = y;
                }
            }
        }
    }
''')

# ---------- genesys.cpp: файл эталона ----------
edit('backend/genesys/genesys.cpp',
'''#include "genesys.h"
''',
'''#include "genesys.h"
#include <cstdlib>
#include <fstream>
''')

edit('backend/genesys/genesys.cpp',
'''        target_code = 0xa000;
        length = pixels_per_line * 12;
        shading_data.clear();
        shading_data.resize(length, 0);
        compute_coefficients(dev, shading_data.data(), pixels_per_line, 3,
                             ColorOrder::RGB, 0, coeff, target_code);
        break;
''',
'''        target_code = 0xa000;
        {
            // White reference on the glass plane: the calibration strip under
            // the frame sees the lamp ripple at a different contrast than the
            // document does. If a reference file for this pixel pitch exists,
            // it replaces the strip; OB4800_WHITE_REF_SAVE=1 creates it from
            // the current calibration (run with OB4800_CALIB_Y_MM pointing at
            // a white sheet on the glass).
            std::string path;
            if (const char* home = std::getenv("HOME")) {
                path = std::string(home) + "/.sane/opticbook4800-white-" +
                       std::to_string(sensor.shading_resolution) + ".dat";
            }
            unsigned n = pixels_per_line * 3;
            if (!path.empty() && std::getenv("OB4800_WHITE_REF_SAVE")) {
                std::ofstream f(path, std::ios::binary);
                f << "OB4800WREF " << pixels_per_line << " 3\\n";
                for (unsigned i = 0; i < n && i < dev->white_average_data.size(); i++) {
                    std::uint16_t v = dev->white_average_data[i];
                    f.put(static_cast<char>(v & 0xff));
                    f.put(static_cast<char>(v >> 8));
                }
                DBG(DBG_info, "%s: white reference saved to %s\\n", __func__, path.c_str());
            } else if (!path.empty()) {
                std::ifstream f(path, std::ios::binary);
                std::string magic; unsigned fp = 0, fc = 0;
                if (f && (f >> magic >> fp >> fc) && magic == "OB4800WREF" &&
                    fp == pixels_per_line && fc == 3)
                {
                    f.get(); // newline
                    std::vector<char> buf(n * 2);
                    if (f.read(buf.data(), buf.size())) {
                        if (dev->white_average_data.size() < n) {
                            dev->white_average_data.resize(n);
                        }
                        for (unsigned i = 0; i < n; i++) {
                            dev->white_average_data[i] = static_cast<std::uint16_t>(
                                static_cast<unsigned char>(buf[2*i]) |
                                (static_cast<unsigned char>(buf[2*i+1]) << 8));
                        }
                        DBG(DBG_info, "%s: white reference loaded from %s\\n", __func__,
                            path.c_str());
                    }
                }
            }
        }
        length = pixels_per_line * 12;
        shading_data.clear();
        shading_data.resize(length, 0);
        compute_coefficients(dev, shading_data.data(), pixels_per_line, 3,
                             ColorOrder::RGB, 0, coeff, target_code);
        break;
''')
print('все правки применены')
