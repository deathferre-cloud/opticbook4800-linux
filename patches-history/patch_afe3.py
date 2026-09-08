#!/usr/bin/env python3
# OpticBook 4800: усиление АЦП (регистры 2-4) по группам. Группа 300 (75-300 dpi):
# 0x3e/0x34/0x39 как в дампе; группы 600 (200, 600) и 1200: на 24 меньше —
# иначе белая бумага упирается в потолок АЦП (замер по белому листу: -24 даёт
# ~205 на 600 и 196 на 1200). Переменная OB4800_AFE_OFS_DELTA прибавляется поверх.
# Запуск из корня sane-backends:  python3 patch_afe3.py
import sys
path = 'backend/genesys/gl846.cpp'
s = open(path).read()
old = '''        unsigned ofs[3] = { 0x3e, 0x34, 0x39 };
        if (const char* e = std::getenv("OB4800_AFE_OFS_DELTA")) {
'''
new = '''        // AFE registers 2-4 are the gains (5-7 turned out to be offsets).
        // Values are from the native driver's 300 dpi dump; the 600 and 1200
        // dpi CCD clockings deliver ~30% more signal and saturate on white
        // paper, so they run 24 codes lower (measured on a white sheet)
        unsigned ofs[3] = { 0x3e, 0x34, 0x39 };
        unsigned xres = dev->session.params.xres;
        if (xres == 200 || xres >= 600) {
            ofs[0] = 0x26; ofs[1] = 0x1c; ofs[2] = 0x21;
        }
        if (const char* e = std::getenv("OB4800_AFE_OFS_DELTA")) {
'''
if s.count(old) != 1:
    sys.exit('фрагмент найден %d раз, ожидался 1' % s.count(old))
open(path, 'w').write(s.replace(old, new)); print('ok:', path)
