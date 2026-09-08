#!/usr/bin/env python3
# OpticBook 4800: защита каретки — печатать понятное сообщение в stderr
# всегда (уровень DBG_error0 выводится и без SANE_DEBUG_GENESYS), а не только
# в отладочный лог. scanimage при этом по-прежнему завершится с
# "sane_start: Invalid argument", но перед ним будет текст причины.
# Запуск из корня sane-backends:  python3 patch_guard2.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''        if (move + calib_size_mm > scan_start) {
            throw SaneException(SANE_STATUS_INVAL,
'''
new = '''        if (move + calib_size_mm > scan_start) {
            DBG(DBG_error0, "OpticBook 4800: refusing to calibrate at %.1f-%.1f mm because the scan "
                           "starts at %.1f mm and the carriage cannot move backwards. Start the "
                           "scan further down (-t) or move the calibration area up.\\n",
                move, move + calib_size_mm, scan_start);
            throw SaneException(SANE_STATUS_INVAL,
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1 (нужно состояние после patch_guard.py)' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
