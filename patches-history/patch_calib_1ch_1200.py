#!/usr/bin/env python3
# patch_calib_1ch_1200.py — одноканальную калибровку включать только на полном
# такте CCD (shading_factor==1, т.е. группа 1200), где она нужна против полос.
# На 200/600 (pitch 1/2) и 75-300 (pitch 1/4) одноканальный проход портит
# левый край (клин -60%), а полос там нет — эти группы калибруются 3 канала,
# как раньше. Правит условие в gl846 init_regs_for_shading. Откат: --revert.
import sys, os, shutil
SRC = os.path.expanduser("~/sane-backends/backend/genesys/gl846.cpp")
OLD = """    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
        std::getenv("OB4800_CALIB_3CH") == nullptr &&
        dev->settings.get_channels() == 1) {
        channels = 1;
    }
    unsigned resolution = sensor.shading_resolution;
"""
NEW = """    unsigned resolution = sensor.shading_resolution;
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
        std::getenv("OB4800_CALIB_3CH") == nullptr &&
        dev->settings.get_channels() == 1 &&
        resolution == sensor.full_resolution) {
        // single-channel calibration is only needed at the full CCD clock
        // (1200 dpi), where it removes the vertical stripes. At the half/quarter
        // clock (200/600 and 75-300) it wrecks the left edge and those groups
        // have no stripes, so they keep the 3-channel calibration.
        channels = 1;
    }
"""
revert = "--revert" in sys.argv
src, dst = (NEW, OLD) if revert else (OLD, NEW)
text = open(SRC, encoding="utf-8").read()
if text.count(src) != 1:
    print("фрагмент найден %d раз — файл не тронут" % text.count(src)); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_1ch_1200")
open(SRC, "w", encoding="utf-8").write(text.replace(src, dst, 1))
print("откат выполнен" if revert else "правка применена")
