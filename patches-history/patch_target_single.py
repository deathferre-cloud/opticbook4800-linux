#!/usr/bin/env python3
# patch_target_single.py — одна цель белого на все группы вместо трёх констант.
# После перебазирования эталона на измеренное тёмное (patch_whiteref2) и
# калибровки в окне скана группы 300/600/1200 в сером и цвете сходятся на
# одной цели с разбросом ~2% (белая бумага 194-199 после гаммы 1.7 при 0xa400).
# Прежние 0x6800/0x7000/0xe000 компенсировали ошибку тёмного. OB4800_SHADING_TARGET
# остаётся отладочным переопределением. Откат: --revert.
import sys, os, shutil
SRC = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")
OLD = """        // The calibration strip is ~25% darker than plain paper, hence the target.
        // white target per CCD clocking group, measured on a white sheet so
        // that paper comes out at ~232 after the 1.7 gamma
        switch (sensor.shading_resolution) {
            case 300:  target_code = 0x6800; break;
            case 600:  target_code = 0x7000; break;
            default:   target_code = 0xe000; break;   // 1200
        }
"""
NEW = """        // White target, one value for all CCD clocking groups: with the white
        // reference rebased onto the measured dark level the groups agree to
        // within ~2% (white paper comes out at ~195-199 after the 1.7 gamma).
        // OB4800_SHADING_TARGET overrides it for tuning.
        target_code = 0xa400;
"""
revert = "--revert" in sys.argv
src, dst = (NEW, OLD) if revert else (OLD, NEW)
text = open(SRC, encoding="utf-8").read()
if text.count(src) != 1:
    print("фрагмент найден %d раз — файл не тронут" % text.count(src)); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_target_single")
open(SRC, "w", encoding="utf-8").write(text.replace(src, dst, 1))
print("откат выполнен" if revert else "правка применена")
