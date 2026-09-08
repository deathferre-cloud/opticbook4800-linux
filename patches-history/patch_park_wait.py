#!/usr/bin/env python3
# OpticBook 4800: парковка каретки всегда с ожиданием.
# После скана и при закрытии устройства genesys вызывает move_back_home без
# ожидания и завершает работу, пока каретка ещё едет («scanhead is still
# moving»); у GL846 остановка мотора у датчика дома делается программно и
# только в ветке ожидания. Следующий запуск (например, следующий скан в
# скрипте или в simple-scan) застаёт каретку в движении, читает «не дома» и
# даёт вторую команду движения поверх первой — мотор хрустит. Для этой модели
# парковка выполняется до конца: устройство закрывается на секунду-две дольше,
# каретка никогда не остаётся в движении, каждый запуск стартует из
# известного положения.
# Запуск из корня sane-backends:  python3 patch_park_wait.py
import sys
path = 'backend/genesys/genesys.cpp'
s = open(path).read()
old = '''void scanner_move_back_home(Genesys_Device& dev, bool wait_until_home)
{
    DBG_HELPER_ARGS(dbg, "wait_until_home = %d", wait_until_home);
'''
new = '''void scanner_move_back_home(Genesys_Device& dev, bool wait_until_home)
{
    DBG_HELPER_ARGS(dbg, "wait_until_home = %d", wait_until_home);

    if (dev.model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        // Never leave the carriage moving: on this chip the motor is stopped at
        // the home sensor only in the waiting branch below, and a command issued
        // by the next scan while the carriage is still travelling home drives
        // it into the stop.
        wait_until_home = true;
    }
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
