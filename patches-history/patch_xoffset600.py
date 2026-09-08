#!/usr/bin/env python3
# OpticBook 4800: в группе «шаг 600» (200 и 600 dpi) кадр начинается на ~0.95 мм
# правее, чем в группе «шаг 300» (замер: левый край карты 15.20 мм на 300,
# 14.27 мм на 600; вертикаль совпадает). Чиним штатным полем
# sensor.output_pixel_offset (пиксели выходного разрешения, прибавляются к
# startx). Отрицательный offset нельзя: калибровка идёт с startx = 0 и
# compute_session бросит исключение. Поэтому model.x_offset уменьшаем на
# 0.95 мм, а группе 300 возвращаем сдвиг положительным offset-ом (свой на
# каждое dpi, т.к. поле в пикселях). Группы 600 и 1200 получают 0; для 1200
# значение ещё предстоит померить.
# Запуск из корня sane-backends:  python3 patch_xoffset600.py
import re, sys

SHIFT_MM = 0.95

# ---------- 1. tables_sensor.cpp ----------
path = 'backend/genesys/tables_sensor.cpp'
src = open(path).read()
beg = src.find('SensorId::CCD_PLUSTEK_OPTICBOOK_4800')
if beg < 0:
    sys.exit('блок OpticBook 4800 не найден в ' + path)
end = src.find('sensor = Genesys_Sensor();', beg)
blk = src[beg:end]

def edit(old, new):
    global blk
    if blk.count(old) != 1:
        sys.exit('%s: фрагмент найден %d раз, ожидался 1:\n%s' % (path, blk.count(old), old[:80]))
    blk = blk.replace(old, new)

edit('''            unsigned exposure_lperiod;
            GenesysRegisterSettingSet custom_regs;''',
'''            unsigned exposure_lperiod;
            int output_pixel_offset; // frame start shift, output pixels
            GenesysRegisterSettingSet custom_regs;''')

def px(dpi):
    return int(round(SHIFT_MM * dpi / 25.4))

g300 = ''.join('            { { %d }, 1200, Ratio{1, 4}, 4, 3500, %d, {} },\n' % (d, px(d))
               for d in (75, 100, 150, 300))
edit('            { { 75, 100, 150, 300 }, 1200, Ratio{1, 4}, 4, 3500, {} },\n',
     '            // the 600 dpi CCD clocking starts the frame ~0.95 mm to the right of\n'
     '            // the 300 dpi one; model.x_offset is set for the 600 dpi group and the\n'
     '            // 300 dpi group gets the 0.95 mm back via output_pixel_offset\n' + g300)
edit('{ { 200, 600 }, 1200, Ratio{1, 2}, 2, 5500, {',
     '{ { 200, 600 }, 1200, Ratio{1, 2}, 2, 5500, 0, {')
edit('{ { 1200 }, 1200, Ratio{1, 1}, 1, 11000, {',
     '{ { 1200 }, 1200, Ratio{1, 1}, 1, 11000, 0, {')
edit('''            sensor.exposure_lperiod = setting.exposure_lperiod;
''',
'''            sensor.exposure_lperiod = setting.exposure_lperiod;
            sensor.output_pixel_offset = setting.output_pixel_offset;
''')
open(path, 'w').write(src[:beg] + blk + src[end:])
print('ok:', path, ' offsets 75/100/150/300 =', [px(d) for d in (75, 100, 150, 300)])

# ---------- 2. tables_model.cpp: x_offset -= 0.95 ----------
path = 'backend/genesys/tables_model.cpp'
src = open(path).read()
beg = src.find('ModelId::PLUSTEK_OPTICBOOK_4800')
if beg < 0:
    sys.exit('блок OpticBook 4800 не найден в ' + path)
end = src.find('s_usb_devices->push_back', beg)
m = re.search(r'model\.x_offset = ([0-9.]+);', src[beg:end])
if not m:
    sys.exit('model.x_offset не найден')
old = float(m.group(1))
new = round(old - SHIFT_MM, 2)
src = src[:beg] + src[beg:end].replace(m.group(0), 'model.x_offset = %.2f;' % new, 1) + src[end:]
open(path, 'w').write(src)
print('ok:', path, ' x_offset %.2f -> %.2f' % (old, new))
print('все правки применены')
