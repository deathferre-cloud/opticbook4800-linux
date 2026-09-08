#!/usr/bin/env python3
# patch_dark_pass2.py — поправка условия тёмного прохода: calib_session в точке
# ветвления ещё не заполнен (init_regs_for_shading вызывается внутри прохода),
# поэтому условие берётся по тому же правилу, что в gl846 init_regs_for_shading:
# серый скан и полный такт сенсора. Откат: --revert.
import sys, os, shutil
SRC = os.path.expanduser("~/sane-backends/backend/genesys/genesys.cpp")
OLD = """            bool ob4800_dark_pass = dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
                                    dev->calib_session.params.channels == 1 &&
                                    std::getenv("OB4800_NO_DARK_PASS") == nullptr;
"""
NEW = """            // same rule as gl846 init_regs_for_shading; calib_session is not set
            // yet at this point (init_regs_for_shading runs inside the pass)
            bool ob4800_dark_pass = dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
                                    std::getenv("OB4800_NO_DARK_PASS") == nullptr &&
                                    std::getenv("OB4800_CALIB_3CH") == nullptr &&
                                    dev->settings.get_channels() == 1 &&
                                    sensor.shading_resolution == sensor.full_resolution;
"""
revert = "--revert" in sys.argv
src, dst = (NEW, OLD) if revert else (OLD, NEW)
text = open(SRC, encoding="utf-8").read()
if text.count(src) != 1:
    print("фрагмент найден %d раз — файл не тронут" % text.count(src)); sys.exit(1)
shutil.copy2(SRC, SRC + ".bak_dark_pass2")
open(SRC, "w", encoding="utf-8").write(text.replace(src, dst, 1))
print("откат выполнен" if revert else "правка применена")
