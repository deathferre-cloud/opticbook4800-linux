#!/usr/bin/env python3
# patch_dark_pass.py — пункт 2: тёмный уровень для одноканального окна калибровки.
#
# Одноканальное окно (1200 dpi) начинается внутри освещённой зоны (startx 183),
# холостых столбцов CCD в нём нет, и genesys_dark_shading_by_dummy_pixel даёт
# dk=0. Пьедестал АЦП (~12 из 255, ~7% сырого белого) не вычитается: чёрный
# лист сканируется как 42/255 вместо 0. Измеряем пьедестал честно — проходом с
# выключенной лампой в том же окне (штатная ветка is_dark: лампа гаснет, мотор
# не стартует, каретка стоит; затем штатная парковка и белый проход). Для
# трёхканальной калибровки (300/600/цвет) ничего не меняется.
# OB4800_NO_DARK_PASS=1 отключает (A/B). Откат: --revert.
import sys, os, shutil
SRC = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")
EDITS = [
 ("""            if (has_flag(dev->model->flags, ModelFlag::DARK_CALIBRATION)) {
                dev->interface->record_progress_message("genesys_dark_shading_calibration");
                genesys_dark_shading_calibration(dev, sensor, local_reg);
                genesys_repark_sensor_before_shading(dev);
            }

            dev->interface->record_progress_message("genesys_white_shading_calibration");
            genesys_white_shading_calibration(dev, sensor, local_reg);

            genesys_repark_sensor_after_white_shading(dev);

            if (!has_flag(dev->model->flags, ModelFlag::DARK_CALIBRATION)) {
""",
  """            // OB4800: the single-channel shading window starts inside the lit
            // area, so there are no covered CCD pixels to take the dark level
            // from (dummy-pixel dark comes out as 0 and black scans as ~16% grey).
            // Measure it with a lamp-off pass in the same window; the motor does
            // not run for that pass, so it adds no carriage travel.
            bool ob4800_dark_pass = dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
                                    dev->calib_session.params.channels == 1 &&
                                    std::getenv("OB4800_NO_DARK_PASS") == nullptr;
            if (has_flag(dev->model->flags, ModelFlag::DARK_CALIBRATION) || ob4800_dark_pass) {
                dev->interface->record_progress_message("genesys_dark_shading_calibration");
                genesys_dark_shading_calibration(dev, sensor, local_reg);
                genesys_repark_sensor_before_shading(dev);
            }

            dev->interface->record_progress_message("genesys_white_shading_calibration");
            genesys_white_shading_calibration(dev, sensor, local_reg);

            genesys_repark_sensor_after_white_shading(dev);

            if (!has_flag(dev->model->flags, ModelFlag::DARK_CALIBRATION) && !ob4800_dark_pass) {
"""),
 ("""    if (is_dark) {
        // wait some time to let lamp to get dark
        dev->interface->sleep_ms(200);
    } else if (has_flag(dev->model->flags, ModelFlag::DARK_CALIBRATION)) {
        // make sure lamp is bright again
        // FIXME: what about scanners that take a long time to warm the lamp?
        dev->interface->sleep_ms(500);
    }
""",
  """    if (is_dark) {
        // wait some time to let lamp to get dark
        dev->interface->sleep_ms(200);
    } else if (has_flag(dev->model->flags, ModelFlag::DARK_CALIBRATION) ||
               (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
                dev->calib_session.params.channels == 1)) {
        // make sure lamp is bright again
        // FIXME: what about scanners that take a long time to warm the lamp?
        dev->interface->sleep_ms(500);
    }
"""),
]
revert = "--revert" in sys.argv
text = open(SRC, encoding="utf-8").read()
for i,(old, new) in enumerate(EDITS):
    src = new if revert else old
    n = text.count(src)
    if n != 1:
        print("фрагмент %d найден %d раз — файл не тронут" % (i+1, n)); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_dark_pass")
for old, new in EDITS:
    src, dst = (new, old) if revert else (old, new)
    text = text.replace(src, dst, 1)
open(SRC, "w", encoding="utf-8").write(text)
print("правка применена" if not revert else "откат выполнен")
