#!/usr/bin/env python3
# patch_calib_gray.py — калибровать затенение в том же канальном режиме, что и скан.
#
# Факты (1200 dpi, серый): тень пылинки в сыром скане -4.8% на px 1501/6910,
# ширина ~30 px; в цветном скане тени стоят в других местах; в трёхканальном
# калибровочном проходе их нет ни в одном канале. Положение и глубина узких
# дефектов отклика зависят от режима считывания CCD (1 или 3 канала), поэтому
# трёхканальный эталон не может поправить серый кадр — полосы остаются.
#
# Правка: (1) gl846 init_regs_for_shading — для серого скана channels=1;
# (2) genesys.cpp — перед эталоном/коэффициентами разложить 1 канал в 3
# одинаковых (чип всегда читает 3-канальные записи, .dat трёхканальный);
# эталон серого хранится как opticbook4800-white-<res>-gray.dat.
# OB4800_CALIB_3CH=1 возвращает старое поведение. Откат: --revert.
import sys, os, shutil

GL = os.path.expanduser("~/sane-backends/backend/genesys/gl846.cpp")
GE = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")

EDITS = [
 (GL,
  """    unsigned channels = 3;
    unsigned resolution = sensor.shading_resolution;
""",
  """    unsigned channels = 3;
    // OB4800: calibrate in the same channel mode as the scan. The CCD read-out
    // differs between 1- and 3-channel sessions and narrow response defects
    // (dust close to the sensor) sit at different pixels in each mode, so a
    // 3-channel reference cannot correct a gray scan at 1200 dpi. The single
    // channel is spread to R,G,B later (the chip always consumes 3-channel
    // shading records). OB4800_CALIB_3CH=1 restores the old behaviour.
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
        std::getenv("OB4800_CALIB_3CH") == nullptr &&
        dev->settings.get_channels() == 1) {
        channels = 1;
    }
    unsigned resolution = sensor.shading_resolution;
"""),
 (GE,
  """            unsigned n = pixels_per_line * 3;
""",
  """            // OB4800: a single-channel shading pass (gray scan) is spread to
            // three identical channels here, before the white reference and
            // the coefficient computation, which both expect 3 channels.
            if (dev->white_average_data.size() == pixels_per_line) {
                std::vector<std::uint16_t> w3(pixels_per_line * 3);
                std::vector<std::uint16_t> d3(pixels_per_line * 3, 0);
                for (unsigned i = 0; i < pixels_per_line; i++) {
                    std::uint16_t wv = dev->white_average_data[i];
                    std::uint16_t dv = i < dev->dark_average_data.size()
                                           ? dev->dark_average_data[i] : 0;
                    for (unsigned c = 0; c < 3; c++) {
                        w3[i * 3 + c] = wv;
                        d3[i * 3 + c] = dv;
                    }
                }
                dev->white_average_data = w3;
                dev->dark_average_data = d3;
                DBG(DBG_info, "%s: OB4800 single-channel shading pass spread to "
                    "3 channels (%u px)\\n", __func__, pixels_per_line);
            }
            unsigned n = pixels_per_line * 3;
"""),
 (GE,
  """                       std::to_string(sensor.shading_resolution) + ".dat";
""",
  """                       std::to_string(sensor.shading_resolution) +
                       (dev->calib_session.params.channels == 1 ? "-gray" : "") +
                       ".dat";
"""),
]

revert = "--revert" in sys.argv
texts = {}
for path, old, new in EDITS:
    texts.setdefault(path, open(path, encoding="utf-8").read())
    src = new if revert else old
    if texts[path].count(src) != 1:
        print("%s: фрагмент найден %d раз — ничего не тронуто" % (os.path.basename(path), texts[path].count(src)))
        sys.exit(1)
for path in texts:
    shutil.copy2(path, path + ".bak_calib_gray")
for path, old, new in EDITS:
    src, dst = (new, old) if revert else (old, new)
    texts[path] = texts[path].replace(src, dst, 1)
for path, t in texts.items():
    open(path, "w", encoding="utf-8").write(t)
print("откат выполнен" if revert else "правка применена (gl846.cpp + genesys.cpp)")
