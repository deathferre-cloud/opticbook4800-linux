#!/usr/bin/env python3
# patch_comment_dark.py — уточнить комментарий к тёмному проходу: он идёт на
# полном такте CCD для любого числа каналов, не только для одноканального.
import sys, os, shutil
SRC = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")
OLD = """            // OB4800: the single-channel shading window starts inside the lit
            // area, so there are no covered CCD pixels to take the dark level
            // from (dummy-pixel dark comes out as 0 and black scans as ~16% grey).
            // Measure it with a lamp-off pass in the same window; the motor does
            // not run for that pass, so it adds no carriage travel.
"""
NEW = """            // OB4800: at the full CCD clock the shading window equals the scan
            // window and starts inside the lit area, so there are no covered CCD
            // pixels to take the dark level from (dummy-pixel dark comes out as 0
            // and black scans as ~16% grey). Measure it with a lamp-off pass in
            // the same window; the motor does not run for that pass, so it adds
            // no carriage travel.
"""
revert = "--revert" in sys.argv
src, dst = (NEW, OLD) if revert else (OLD, NEW)
text = open(SRC, encoding="utf-8").read()
if text.count(src) != 1:
    print("фрагмент найден %d раз — файл не тронут" % text.count(src)); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_comment_dark")
open(SRC, "w", encoding="utf-8").write(text.replace(src, dst, 1))
print("откат выполнен" if revert else "правка применена")
