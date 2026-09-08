#!/usr/bin/env python3
# patch_xsize.py — x_size по концу сенсора. Линейка 10200 px = 215.9 мм от
# начала сенсора; кадр начинается с x_offset 3.88, после коррекции шага
# 1200/1195 конец сенсора приходится на 212.75 мм кадра, дальше нули.
# x_size 215.9 обещал кадр до 219.8 и давал ~2 мм чёрных столбцов справа.
# Откат: --revert.
import sys, os, shutil
SRC = os.path.expanduser("~/sane-backends/backend/genesys/tables_model.cpp")
OLD = """    model.x_offset = 3.88;
    model.y_offset = 34.0;
    model.x_size = 215.9;
    model.y_size = 298.0;
"""
NEW = """    model.x_offset = 3.88;
    model.y_offset = 34.0;
    // width to the end of the CCD line (10200 px = 215.9 mm from the sensor
    // origin, i.e. 212.75 mm of frame after the 1200/1195 pitch correction);
    // anything wider only adds empty columns on the right
    model.x_size = 212.7;
    model.y_size = 298.0;
"""
revert = "--revert" in sys.argv
src, dst = (NEW, OLD) if revert else (OLD, NEW)
text = open(SRC, encoding="utf-8").read()
if text.count(src) != 1:
    print("фрагмент найден %d раз — файл не тронут" % text.count(src)); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_xsize")
open(SRC, "w", encoding="utf-8").write(text.replace(src, dst, 1))
print("откат выполнен" if revert else "правка применена")
