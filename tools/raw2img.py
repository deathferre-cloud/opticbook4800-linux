#!/usr/bin/env python3
"""
Превращает сырой дамп с Plustek OpticBook 4800 в картинку.

Формат данных, установленный по дампу режима A4 / 300 dpi / 24-bit color:
  - первые 1355780 байт - служебные данные калибровки, в картинку не идут
  - дальше 2550 x 3520 пикселей, по три байта на пиксель (RGB)
  - цветовые линии сняты со сдвигом: красный на 6 строк, синий на 12
  - затенение сканер применяет сам, дополнительная коррекция не нужна

Использование:
    python3 raw2img.py raw_a4_300.bin scan.png
    python3 raw2img.py raw_a4_300.bin scan.pdf --dpi 300
"""

import argparse, sys

CALIB_BYTES = 1355780
WIDTH, HEIGHT = 2550, 3520
LD_SHIFT = {'r': 6, 'g': 0, 'b': 12}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--dpi', type=int, default=300)
    ap.add_argument('--gray', action='store_true', help='в оттенки серого')
    ap.add_argument('--offset', type=int, default=CALIB_BYTES)
    ap.add_argument('--width', type=int, default=WIDTH)
    ap.add_argument('--height', type=int, default=HEIGHT)
    args = ap.parse_args()

    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        sys.exit('нужны numpy и pillow:\n'
                 '  pip3 install numpy pillow --break-system-packages')

    raw = open(args.src, 'rb').read()
    need = args.offset + args.width * args.height * 3
    if len(raw) < need:
        sys.exit('файл короче ожидаемого: %d вместо %d' % (len(raw), need))

    data = np.frombuffer(raw, dtype=np.uint8, count=args.width*args.height*3,
                         offset=args.offset)
    img = data.reshape(args.height, args.width, 3)

    out = img.copy()
    for idx, key in ((0, 'r'), (1, 'g'), (2, 'b')):
        s = LD_SHIFT[key]
        if s:
            out[:, :, idx] = np.roll(img[:, :, idx], s, axis=0)

    trim = max(LD_SHIFT.values())
    out = out[trim:]

    pic = Image.fromarray(out)
    if args.gray:
        pic = pic.convert('L')

    pic.save(args.dst, dpi=(args.dpi, args.dpi))
    print('сохранено: %s  (%d x %d, %d dpi)'
          % (args.dst, pic.width, pic.height, args.dpi))


if __name__ == '__main__':
    main()
