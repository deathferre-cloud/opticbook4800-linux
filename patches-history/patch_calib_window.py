#!/usr/bin/env python3
# patch_calib_window.py — пункт 1: окно одноканальной калибровки = окно скана.
#
# gl846 init_regs_for_shading: при channels==1 старт и ширина калибровочного
# окна считаются из сессии скана (x_offset+tl_x, pixels*res/xres). Одноканальный
# проход с нулевого пикселя чип на 1200 dpi не выполняет (bulk_read timeout),
# а совпадение окон даёт эталон, выровненный с кадром пиксель в пиксель —
# именно это убрало вертикальные полосы на 1200 (6.5% -> 0.7%).
# Диагностические OB4800_CALIB_STARTX/PIXELS (patch_calib_win.py) заменяются.
#
# genesys.cpp: эталон пишется с заголовком "OB4800WREF2 <px> 3 <startx>",
# при загрузке файл должен покрывать текущее окно и вырезается под него;
# старые файлы "OB4800WREF" читаются как окно со старта 0.
# Откат: --revert.
import sys, os, shutil

GL = os.path.expanduser("~/sane-backends/backend/genesys/gl846.cpp")
GE = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")

EDITS = [
 (GL,
  """    session.params.pixels = dev->model->x_size_calib_mm * resolution / MM_PER_INCH;
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        // diagnostic: calibration window geometry override
        if (const char* e = std::getenv("OB4800_CALIB_STARTX")) {
            unsigned sx = static_cast<unsigned>(std::atoi(e));
            if (sx < session.params.pixels) {
                session.params.startx = sx;
                session.params.pixels -= sx;
            }
        }
        if (const char* e = std::getenv("OB4800_CALIB_PIXELS")) {
            unsigned px = static_cast<unsigned>(std::atoi(e));
            if (px > 0 && px <= session.params.pixels) {
                session.params.pixels = px;
            }
        }
        DBG(DBG_info, "%s: OB4800 calibration window startx=%u pixels=%u channels=%u\\n",
            __func__, session.params.startx, session.params.pixels, channels);
    }
""",
  """    session.params.pixels = dev->model->x_size_calib_mm * resolution / MM_PER_INCH;
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 && channels == 1) {
        // Single-channel shading pass: use the scan's own window. The chip does
        // not deliver a single-channel read-out that starts at sensor pixel 0 at
        // the full 1200 dpi clock, and a window equal to the scan's lines the
        // reference up with the frame pixel for pixel.
        unsigned full = session.params.pixels;
        unsigned sx = static_cast<unsigned>((dev->model->x_offset + dev->settings.tl_x) *
                                            resolution / MM_PER_INCH);
        unsigned px = static_cast<unsigned>(static_cast<unsigned long long>(dev->settings.pixels) *
                                            resolution / dev->settings.xres);
        if (sx < full && px > 0) {
            if (sx + px > full) {
                px = full - sx;
            }
            session.params.startx = sx;
            session.params.pixels = px;
        }
        DBG(DBG_info, "%s: OB4800 single-channel shading window startx=%u pixels=%u\\n",
            __func__, session.params.startx, session.params.pixels);
    }
"""),
 (GE,
  """                f << "OB4800WREF " << pixels_per_line << " 3\\n";
""",
  """                f << "OB4800WREF2 " << pixels_per_line << " 3 "
                  << dev->calib_session.params.startx << "\\n";
"""),
 (GE,
  """                std::ifstream f(path, std::ios::binary);
                std::string magic; unsigned fp = 0, fc = 0;
                if (f && (f >> magic >> fp >> fc) && magic == "OB4800WREF" &&
                    fp == pixels_per_line && fc == 3)
                {
                    f.get(); // newline
                    std::vector<char> buf(n * 2);
                    if (f.read(buf.data(), buf.size())) {
""",
  """                std::ifstream f(path, std::ios::binary);
                std::string magic; unsigned fp = 0, fc = 0, fs = 0;
                bool hdr_ok = false;
                if (f && (f >> magic >> fp >> fc)) {
                    if (magic == "OB4800WREF") {
                        hdr_ok = (fc == 3);            // v1: window starts at sensor pixel 0
                    } else if (magic == "OB4800WREF2" && (f >> fs)) {
                        hdr_ok = (fc == 3);            // v2: header carries the window start
                    }
                }
                unsigned cur_sx = dev->calib_session.params.startx;
                if (hdr_ok && !(fs <= cur_sx && fs + fp >= cur_sx + pixels_per_line)) {
                    DBG(DBG_info, "%s: white reference %s covers %u..%u but the window is "
                        "%u..%u, ignoring it\\n", __func__, path.c_str(), fs, fs + fp,
                        cur_sx, cur_sx + pixels_per_line);
                    hdr_ok = false;
                }
                if (hdr_ok)
                {
                    f.get(); // newline
                    std::vector<char> full(static_cast<std::size_t>(fp) * 3 * 2);
                    std::vector<char> buf(n * 2);
                    bool read_ok = static_cast<bool>(f.read(full.data(), full.size()));
                    if (read_ok) {
                        std::size_t off = static_cast<std::size_t>(cur_sx - fs) * 3 * 2;
                        std::copy(full.begin() + off, full.begin() + off + buf.size(), buf.begin());
                    }
                    if (read_ok) {
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
    shutil.copy2(path, path + ".bak_calib_window")
for path, old, new in EDITS:
    src, dst = (new, old) if revert else (old, new)
    texts[path] = texts[path].replace(src, dst, 1)
for path, t in texts.items():
    open(path, "w", encoding="utf-8").write(t)
print("откат выполнен" if revert else "правка применена (gl846.cpp + genesys.cpp)")
