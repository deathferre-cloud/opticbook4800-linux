#!/usr/bin/env python3
# OpticBook 4800: группа «шаг 1200» начинает кадр ещё на ~0.47 мм правее группы
# 600 (карта: 14.64 мм против 15.1; край листа 209.2 против 209.7). Схема та же,
# что в patch_xoffset600.py: model.x_offset уменьшаем ещё на 0.47 мм (теперь
# он выставлен по группе 1200, offset 0), а группам 300 и 600 возвращаем сдвиг
# положительным output_pixel_offset. Запись { 200, 600 } делится на две.
# Запуск из корня sane-backends после patch_xoffset600.py:  python3 patch_xoffset1200.py
import re, sys

SHIFT_1200 = 0.47          # мм, группа 600 относительно 1200
SHIFT_300 = 0.95 + 0.47    # мм, группа 300 относительно 1200

def px(mm, dpi):
    return int(round(mm * dpi / 25.4))

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

for d, old in ((75, 3), (100, 4), (150, 6), (300, 11)):
    edit('{ { %d }, 1200, Ratio{1, 4}, 4, 3500, %d, {} },' % (d, old),
         '{ { %d }, 1200, Ratio{1, 4}, 4, 3500, %d, {} },' % (d, px(SHIFT_300, d)))

edit('''            // the 600 dpi CCD clocking starts the frame ~0.95 mm to the right of
            // the 300 dpi one; model.x_offset is set for the 600 dpi group and the
            // 300 dpi group gets the 0.95 mm back via output_pixel_offset
''',
'''            // each CCD clocking starts the frame at a slightly different place:
            // 600 dpi ~0.95 mm right of 300 dpi, 1200 dpi another ~0.47 mm right.
            // model.x_offset is set for the 1200 dpi group; the others get the
            // difference back via output_pixel_offset (output pixels)
''')

m = re.search(r'( *)\{ \{ 200, 600 \}, 1200, Ratio\{1, 2\}, 2, 5500, 0, \{(.*?)\n( *)\} \},\n',
              blk, re.S)
if not m:
    sys.exit('запись { 200, 600 } не найдена')
ind, regs, ind2 = m.group(1), m.group(2), m.group(3)
regs = regs.split('\n', 1)[1]
e200 = ('%s{ { 200 }, 1200, Ratio{1, 2}, 2, 5500, %d, {   // 200 dpi: 600 dpi pitch, 3 lines averaged\n'
        '%s\n%s} },\n' % (ind, px(SHIFT_1200, 200), regs, ind2))
e600 = ('%s{ { 600 }, 1200, Ratio{1, 2}, 2, 5500, %d, {\n'
        '%s\n%s} },\n' % (ind, px(SHIFT_1200, 600), regs, ind2))
blk = blk[:m.start()] + e200 + e600 + blk[m.end():]
open(path, 'w').write(src[:beg] + blk + src[end:])
print('ok:', path, ' offsets 75/100/150/300 =', [px(SHIFT_300, d) for d in (75, 100, 150, 300)],
      ' 200/600 =', [px(SHIFT_1200, d) for d in (200, 600)], ' 1200 = 0')

path = 'backend/genesys/tables_model.cpp'
src = open(path).read()
beg = src.find('ModelId::PLUSTEK_OPTICBOOK_4800')
end = src.find('s_usb_devices->push_back', beg)
m = re.search(r'model\.x_offset = ([0-9.]+);', src[beg:end])
if beg < 0 or not m:
    sys.exit('model.x_offset OpticBook 4800 не найден')
old = float(m.group(1)); new = round(old - SHIFT_1200, 2)
src = src[:beg] + src[beg:end].replace(m.group(0), 'model.x_offset = %.2f;' % new, 1) + src[end:]
open(path, 'w').write(src)
print('ok:', path, ' x_offset %.2f -> %.2f' % (old, new))
print('все правки применены')
