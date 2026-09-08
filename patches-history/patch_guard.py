#!/usr/bin/env python3
# OpticBook 4800: защита каретки. genesys не умеет двигать каретку назад, и если
# калибровочный проход заканчивается дальше начала скана, каретку гонит в упор.
# Правка: в init_regs_for_shading для 4800 проверяем, что конец калибровки
# (положение + y_size_calib_mm) раньше старта скана (y_offset + tl_y), иначе
# отказ с понятным сообщением ДО любого движения.
# Запуск из корня sane-backends:  python3 patch_guard.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''                if (y >= 18.0f && y <= 60.0f) {
                    move = y;
                }
            }
        }
    }

    move = static_cast<float>((move * move_dpi) / MM_PER_INCH);
'''
new = '''                if (y >= 18.0f && y <= 60.0f) {
                    move = y;
                }
            }
        }
        // the carriage cannot move backwards: the calibration area must end
        // before the scan starts, otherwise the head is driven into the stop
        float scan_start = dev->model->y_offset + dev->settings.tl_y;
        if (move + calib_size_mm > scan_start) {
            throw SaneException(SANE_STATUS_INVAL,
                                "calibration area %.1f-%.1f mm must end before the scan start "
                                "at %.1f mm (carriage cannot move backwards)",
                                move, move + calib_size_mm, scan_start);
        }
    }

    move = static_cast<float>((move * move_dpi) / MM_PER_INCH);
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1 (нужно состояние после patch_whiteref.py)' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
