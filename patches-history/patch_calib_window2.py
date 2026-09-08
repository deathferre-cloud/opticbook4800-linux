#!/usr/bin/env python3
# patch_calib_window2.py — поправка загрузчика эталона к patch_calib_window.py.
# white_average_data хранится от нулевого пикселя сенсора (нули до старта окна),
# pixels_per_line включает старт; файл того же вида. Значит резать файл со
# смещением нельзя — берём первые pixels_per_line записей, а файл должен иметь
# данные со старта не позже текущего и длину не меньше окна. Откат: --revert.
import sys, os, shutil
SRC = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")
EDITS = [
 ("""                unsigned cur_sx = dev->calib_session.params.startx;
                if (hdr_ok && !(fs <= cur_sx && fs + fp >= cur_sx + pixels_per_line)) {
                    DBG(DBG_info, "%s: white reference %s covers %u..%u but the window is "
                        "%u..%u, ignoring it\\n", __func__, path.c_str(), fs, fs + fp,
                        cur_sx, cur_sx + pixels_per_line);
                    hdr_ok = false;
                }
""",
  """                // average data are laid out from sensor pixel 0 (zeros below the
                // window start) and so is the file; pixels_per_line already includes
                // the window start. The file must have valid data from a start no
                // later than the current one and be at least as long as the window.
                unsigned cur_sx = dev->calib_session.params.startx;
                if (hdr_ok && !(fs <= cur_sx && fp >= pixels_per_line)) {
                    DBG(DBG_info, "%s: white reference %s (start %u, %u px) does not cover "
                        "the window (start %u, %u px), ignoring it\\n", __func__,
                        path.c_str(), fs, fp, cur_sx, pixels_per_line);
                    hdr_ok = false;
                }
"""),
 ("""                    if (read_ok) {
                        std::size_t off = static_cast<std::size_t>(cur_sx - fs) * 3 * 2;
                        std::copy(full.begin() + off, full.begin() + off + buf.size(), buf.begin());
                    }
""",
  """                    if (read_ok) {
                        std::copy(full.begin(), full.begin() + buf.size(), buf.begin());
                    }
"""),
]
revert = "--revert" in sys.argv
text = open(SRC, encoding="utf-8").read()
for old, new in EDITS:
    src = new if revert else old
    if text.count(src) != 1:
        print("фрагмент найден %d раз — файл не тронут" % text.count(src)); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_calib_window2")
for old, new in EDITS:
    src, dst = (new, old) if revert else (old, new)
    text = text.replace(src, dst, 1)
open(SRC, "w", encoding="utf-8").write(text)
print("откат выполнен" if revert else "правка применена")
