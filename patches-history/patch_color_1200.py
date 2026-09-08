#!/usr/bin/env python3
# patch_color_1200.py — цвет 1200: калибровка в окне скана + тёмный проход.
# Замер регистров: цветной скан читает CCD так же, как серый (0x18=13,
# фазы 06/08/0a/00/02/04), а калибровка для обоих — по блоку 1200 (0x18=01,
# 08/0a/00/02/04/06). Одноканальная калибровка серого фазы не меняла и всё
# равно убрала полосы — значит дело в окне, не в фазах. Для цвета делаем то же:
# (1) окно калибровки = окно скана на полном такте независимо от каналов;
# (2) тёмный проход с выключенной лампой на полном такте независимо от каналов;
# (3) чтение калибровочных данных точным размером для любого числа каналов.
# Старый трёхканальный эталон -1200.dat (v1, окно с нуля) надо удалить и
# переснять — иначе загрузчик примет его как покрывающий окно. Откат: --revert.
import sys, os, shutil
GL = os.path.expanduser("~/sane-backends/backend/genesys/gl846.cpp")
GE = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")
EDITS = [
 (GL,
  "    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 && channels == 1) {\n",
  "    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&\n"
  "        resolution == sensor.full_resolution) {\n"),
 (GE,
  """                                    dev->settings.get_channels() == 1 &&
                                    sensor.shading_resolution == sensor.full_resolution;
""",
  """                                    sensor.shading_resolution == sensor.full_resolution;
"""),
 (GE,
  """               (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
                dev->calib_session.params.channels == 1)) {
""",
  """               (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
                dev->calib_session.params.xres == sensor.full_resolution)) {
"""),
 (GE,
  """        if (channels == 1 && dev->total_bytes_to_read > 0 &&
            dev->total_bytes_to_read < to_read) {
""",
  """        if (dev->total_bytes_to_read > 0 &&
            dev->total_bytes_to_read < to_read) {
"""),
]
revert = "--revert" in sys.argv
texts = {}
for path, old, new in EDITS:
    texts.setdefault(path, open(path, encoding="utf-8").read())
    src = new if revert else old
    n = texts[path].count(src)
    if n != 1:
        print("%s: фрагмент найден %d раз — ничего не тронуто" % (os.path.basename(path), n)); sys.exit(1)
for path in texts:
    shutil.copy2(path, path + ".bak_color_1200")
for path, old, new in EDITS:
    src, dst = (new, old) if revert else (old, new)
    texts[path] = texts[path].replace(src, dst, 1)
for path, t in texts.items():
    open(path, "w", encoding="utf-8").write(t)
print("откат выполнен" if revert else "правка применена (gl846.cpp + genesys.cpp)")
