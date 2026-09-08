#!/usr/bin/env python3
# patch_log_text.py — текст лога окна калибровки: печатается для любого числа
# каналов на полном такте, слово single-channel вводит в заблуждение.
import sys, os, shutil
SRC = os.path.expanduser("~/sane-backends/backend/genesys/gl846.cpp")
OLD = 'DBG(DBG_info, "%s: OB4800 single-channel shading window startx=%u pixels=%u\\n",\n'
NEW = 'DBG(DBG_info, "%s: OB4800 shading window startx=%u pixels=%u (channels %u)\\n",\n'
OLD2 = '            __func__, session.params.startx, session.params.pixels);\n'
NEW2 = '            __func__, session.params.startx, session.params.pixels, channels);\n'
revert = "--revert" in sys.argv
text = open(SRC, encoding="utf-8").read()
a,b = (NEW,OLD) if revert else (OLD,NEW)
c,d = (NEW2,OLD2) if revert else (OLD2,NEW2)
if text.count(a)!=1 or text.count(c)!=1:
    print("фрагменты найдены %d/%d раз — файл не тронут" % (text.count(a), text.count(c))); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_log_text")
open(SRC,"w",encoding="utf-8").write(text.replace(a,b,1).replace(c,d,1))
print("откат выполнен" if revert else "правка применена")
