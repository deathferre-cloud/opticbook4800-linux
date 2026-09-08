#!/usr/bin/env python3
# patch_calib_gray2.py — дополнение к patch_calib_gray.py.
# В одноканальной калибровочной сессии чип отдаёт ровно
# output_line_bytes * lines байт, а genesys_shading_calibration_impl считает
# размер с запасом в одну строку (lines + 1) и ждёт её до таймаута USB —
# скан падает с Error during device I/O. Читаем столько, сколько чип шлёт
# (dev->total_bytes_to_read); усреднение использует только params.lines
# строк, поэтому хвост буфера не нужен. Трёхканальный путь не трогаем.
import sys, os, shutil

SRC = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")

OLD = """        std::vector<std::uint8_t> raw8(size / 2);
        sanei_genesys_read_data_from_scanner(dev, raw8.data(), raw8.size());
"""

NEW = """        std::vector<std::uint8_t> raw8(size / 2);
        // 'size' allows for one extra line from the chip. In the
        // single-channel (gray) session the chip delivers exactly
        // output_line_bytes * lines, so waiting for the extra line times out;
        // read what the chip actually sends. The averaging below only uses
        // params.lines lines, the unread tail stays zero and unused.
        std::size_t to_read = raw8.size();
        if (channels == 1 && dev->total_bytes_to_read > 0 &&
            dev->total_bytes_to_read < to_read) {
            to_read = dev->total_bytes_to_read;
        }
        sanei_genesys_read_data_from_scanner(dev, raw8.data(), to_read);
"""

revert = "--revert" in sys.argv
src, dst = (NEW, OLD) if revert else (OLD, NEW)
text = open(SRC, encoding="utf-8").read()
if text.count(src) != 1:
    print("фрагмент найден %d раз — файл не тронут" % text.count(src)); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_calib_gray2")
open(SRC, "w", encoding="utf-8").write(text.replace(src, dst, 1))
print("откат выполнен" if revert else "правка применена")
