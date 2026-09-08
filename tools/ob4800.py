#!/usr/bin/env python3
"""
Сканирование на Plustek OpticBook 4800 (07b3:1301) под Linux.

Штатной поддержки этой модели в SANE нет. Скрипт работает в обход:
воспроизводит последовательность обмена, снятую с родного драйвера
Windows, и собирает пришедшие данные в изображение.

Из-за такого устройства доступны только заранее записанные режимы -
список смотрите командой --list. Произвольные размер и разрешение
задать нельзя.

Использование:
    python3 ob4800.py --list
    python3 ob4800.py a4-300 scan.png
    python3 ob4800.py a6-300 page.pdf --gray
    python3 ob4800.py a4-300 raw.bin --raw     # только сырые данные

ДЕРЖИТЕ РУКУ НА КАБЕЛЕ ПИТАНИЯ СКАНЕРА при первых запусках.
"""

import sys, os, time, json, zlib, base64, argparse

VID, PID = 0x07b3, 0x1301
EP_IN, EP_OUT = 0x81, 0x02
TIMEOUT = 5000
BULK_RETRIES = 5
DATA_FILE = 'ob4800_modes.dat'


def load_modes():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_FILE)
    if not os.path.exists(path):
        sys.exit('не найден файл с режимами: %s' % path)
    return json.loads(zlib.decompress(base64.b64decode(open(path).read())))


def list_modes(modes):
    print('%-10s %-34s %-14s %s' % ('режим', 'описание', 'пикселей', 'объём'))
    for key in sorted(modes):
        m = modes[key]
        print('%-10s %-34s %5d x %-6d %6.1f МБ'
              % (key, m['title'], m['width'], m['lines'],
                 m['expect'] / 1048576))


def stop(dev):
    for data in (bytes([0x03, 0x00]), bytes([0x0f, 0x00])):
        try:
            dev.ctrl_transfer(0x40, 0x04, 0x0083, 0x0000, data, 1000)
        except Exception:
            pass


def scan(mode, pace, quiet, progress=None):
    import usb.core, usb.util

    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit('сканер 07b3:1301 не найден - включён ли он?')
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass
    dev.set_configuration()
    usb.util.claim_interface(dev, 0)

    seq = mode['seq']
    data = bytearray()
    prev = seq[0]['dt']
    t0 = time.time()
    mismatch = 0

    try:
        for i, o in enumerate(seq):
            gap = min(o['dt'] - prev, pace)
            if gap > 0:
                time.sleep(gap)
            prev = o['dt']

            if o['op'] == 'wr':
                dev.ctrl_transfer(0x40, o['breq'], o['wval'], o['widx'],
                                  bytes.fromhex(o['data']), TIMEOUT)

            elif o['op'] == 'poll':
                want = bytes.fromhex(o['expect'])
                for _ in range(o['tries']):
                    got = bytes(dev.ctrl_transfer(0xc0, o['breq'], o['wval'],
                                                  o['widx'], o['wlen'], TIMEOUT))
                    if got == want:
                        break
                    time.sleep(0.013)
                else:
                    mismatch += 1

            elif o['op'] == 'bout':
                dev.write(EP_OUT, bytes.fromhex(o['data']), TIMEOUT)

            elif o['op'] == 'bin':
                for attempt in range(BULK_RETRIES):
                    try:
                        data += bytes(dev.read(EP_IN, o['n'], TIMEOUT))
                        break
                    except Exception:
                        if attempt == BULK_RETRIES - 1:
                            raise
                        time.sleep(0.2 * (attempt + 1))
                if progress is not None:
                    progress(len(data), mode['expect'])
                elif not quiet and len(data) % (2 * 1024 * 1024) < o['n']:
                    print('  %d / %d МБ' % (len(data) // 1048576,
                                            mode['expect'] // 1048576))
    except KeyboardInterrupt:
        print('\nпрервано')
    except Exception as exc:
        print('\nсбой на операции %d: %s' % (i, exc))
    finally:
        stop(dev)
        usb.util.release_interface(dev, 0)

    if not quiet:
        print('время %.1f с, получено %d из %d байт, несовпавших опросов %d'
              % (time.time() - t0, len(data), mode['expect'], mismatch))
    return bytes(data)


def make_image(raw, mode, gray=False, downscale=True):
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        sys.exit('нужны numpy и pillow:\n'
                 '  pip3 install numpy pillow --break-system-packages')

    w, h, ch = mode['width'], mode['lines'], mode.get('ch', 3)
    need = w * h * ch
    if len(raw) < need:
        h = len(raw) // (w * ch)
        need = w * h * ch
        print('данных меньше ожидаемого, собираю %d строк' % h)
    off = len(raw) - need

    img = np.frombuffer(raw, dtype=np.uint8, count=need, offset=off)
    img = img.reshape(h, w, ch)

    if ch == 3:
        # цветовые линии сняты со сдвигом, величина зависит от режима
        k = mode['hw'] // 300
        out = img.copy()
        out[:, :, 0] = np.roll(img[:, :, 0], 6 * k, axis=0)
        out[:, :, 2] = np.roll(img[:, :, 2], 12 * k, axis=0)
        out = out[12 * k:]
        pic = Image.fromarray(out)
        if gray:
            pic = pic.convert('L')
    else:
        pic = Image.fromarray(img[:, :, 0], mode='L')
    if downscale and mode['dpi'] != mode['hw']:
        s = mode['dpi'] / mode['hw']
        pic = pic.resize((max(1, int(pic.width * s)),
                          max(1, int(pic.height * s))), Image.LANCZOS)

    return pic


def to_image(raw, mode, dst, gray, downscale):
    pic = make_image(raw, mode, gray, downscale)
    pic.save(dst, dpi=(mode['dpi'], mode['dpi']))
    print('сохранено: %s  (%d x %d, %d dpi)'
          % (dst, pic.width, pic.height, mode['dpi']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?', help='режим (см. --list)')
    ap.add_argument('dst', nargs='?', help='файл результата')
    ap.add_argument('--list', action='store_true', help='показать режимы')
    ap.add_argument('--raw', action='store_true', help='сохранить сырые данные')
    ap.add_argument('--gray', action='store_true', help='в оттенки серого')
    ap.add_argument('--no-downscale', action='store_true',
                    help='оставить аппаратное разрешение')
    ap.add_argument('--from-raw', help='собрать картинку из готового дампа')
    ap.add_argument('--pace', type=float, default=0.3)
    ap.add_argument('-q', '--quiet', action='store_true')
    args = ap.parse_args()

    modes = load_modes()
    if args.list or not args.mode:
        list_modes(modes)
        return
    if args.mode not in modes:
        sys.exit('неизвестный режим %s, посмотрите --list' % args.mode)
    mode = modes[args.mode]
    dst = args.dst or ('scan_%s.png' % args.mode)

    if args.from_raw:
        raw = open(args.from_raw, 'rb').read()
    else:
        if not args.quiet:
            print('%s -> %s' % (mode['title'], dst))
        raw = scan(mode, args.pace, args.quiet)

    if not raw:
        sys.exit('данные не получены')

    if args.raw:
        open(dst, 'wb').write(raw)
        print('сырые данные: %s (%d байт)' % (dst, len(raw)))
    else:
        to_image(raw, mode, dst, args.gray, not args.no_downscale)


if __name__ == '__main__':
    main()
