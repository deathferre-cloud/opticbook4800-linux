#!/usr/bin/env python3
"""
Стенд: воспроизводим родной драйвер (режим max-300 из ob4800_modes.dat),
но прямо перед стартом последнего, основного скана подменяем часть
регистров на значения genesys. Если данные пропадают - виновник среди
подменённых.

Требует рядом ob4800.py и ob4800_modes.dat.

    python3 probe_4800.py                      # без подмен, контроль
    python3 probe_4800.py --set 1e=f0,20=03    # подменить регистры
    python3 probe_4800.py --group 1            # готовые группы 1..4

Скрипт останавливает чтение при первом же таймауте, но доводит до конца
все служебные команды (парковка, лампа), так что каретка вернётся домой.
"""

import os, sys, time, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ob4800

GROUPS = {
    1: '1e=f0,20=03',
    2: '3b=00,51=07',
    3: '03=13,0d=05,0e=00,bd=18',
    4: '0c=00,61=02,62=d6,64=06,65=7e,94=ff,98=20,99=00,9a=90,9b=00,'
       '9e=00,a1=e0,ab=c0,bb=00,bc=0f,db=ff,fe=08,ff=02',
}

def parse_set(s):
    out = []
    for item in s.split(','):
        item = item.strip()
        if not item:
            continue
        a, v = item.split('=')
        out.append((int(a, 16), int(v, 16)))
    return out


def run(mode, overrides, out_path, skip_readback=False, read_style='native',
        skip_passes=False, width_test=False):
    import usb.core, usb.util
    seq = mode['seq']
    starts = [i for i, o in enumerate(seq)
              if o['op'] == 'wr' and o['wval'] == 0x83 and o['data'] == '0f01']
    inject_at = starts[-1]
    wt_done = False
    if width_test:
        st = {}
        for o in seq[:inject_at]:
            if o['op'] == 'wr' and o['wval'] == 0x83:
                d = bytes.fromhex(o['data'])
                for i in range(0, len(d) - 1, 2):
                    st[d[i]] = d[i + 1]
        lincnt = (st.get(0x25, 0) << 16) | (st.get(0x26, 0) << 8) | st.get(0x27, 0)
        strp = (st.get(0x30, 0) << 8) | st.get(0x31, 0)
        endp = (st.get(0x32, 0) << 8) | st.get(0x33, 0)
        for a, v in overrides:
            st[a] = v
        endp2 = (st.get(0x32, 0) << 8) | st.get(0x33, 0)
        print('строк %d, STR %d, END %d -> %d (запрошенная ширина %d)'
              % (lincnt, strp, endp, endp2, endp2 - strp))
        mode = dict(mode)
        mode['_width_test'] = (lincnt, endp2 - strp)
    skip = set()
    if skip_passes:
        for i in range(0, starts[-1]):
            o = seq[i]
            if o['op'] in ('bin', 'poll') or (o['op'] == 'wr' and o['wval'] == 0x83
                                             and o['data'] == '0f01'):
                skip.add(i)
            if o['op'] == 'wr' and o['wval'] == 0x82 and o['widx'] == 0:
                skip.add(i)   # запросы на чтение данных проходов
        print('  убрано %d операций проходов до основного скана' % len(skip))
    if skip_readback:
        for i in range(starts[-2], starts[-1]):
            o = seq[i]
            if o['op'] == 'bin' or (o['op'] == 'wr' and o['wval'] == 0x82
                                    and o['widx'] == 0):
                skip.add(i)
        print('  пропускаю %d операций обратного чтения перед стартом' % len(skip))

    dev = usb.core.find(idVendor=ob4800.VID, idProduct=ob4800.PID)
    if dev is None:
        sys.exit('сканер не найден')
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass
    dev.set_configuration()
    usb.util.claim_interface(dev, 0)

    data = bytearray()
    prev = seq[0]['dt']
    failed_at = None
    mismatch_after = 0
    t0 = time.time()
    # операции чтения основного скана (после последнего старта до первой
    # записи регистров после него)
    scan_reads = [i for i in range(inject_at + 1, len(seq))
                  if seq[i]['op'] == 'bin']
    scan_reqs = [i for i in range(inject_at + 1, len(seq))
                 if seq[i]['op'] == 'wr' and seq[i]['wval'] == 0x82]
    total = sum(seq[i]['n'] for i in scan_reads)
    if read_style != 'native':
        skip |= set(scan_reads) | set(scan_reqs)
        first_read = scan_reads[0] if scan_reads else None
        print('  стиль чтения: %s, объём %d байт' % (read_style, total))

    def custom_read():
        got = bytearray()
        if read_style == 'whole':
            hdr = bytes([0, 0, 0, 0x10]) + total.to_bytes(4, 'little')
            dev.ctrl_transfer(0x40, 0x04, 0x0082, 0x0000, hdr, ob4800.TIMEOUT)
            while len(got) < total:
                try:
                    chunk = bytes(dev.read(ob4800.EP_IN, min(65536, total - len(got)), 3000))
                except Exception:
                    print('  таймаут после %d байт' % len(got)); break
                if not chunk:
                    print('  пустой ответ после %d байт' % len(got)); break
                got += chunk
        else:  # chunked, как genesys
            zero = 0
            while len(got) < total:
                n = min(61440, total - len(got))
                hdr = bytes([0, 0, 0, 0x10]) + n.to_bytes(4, 'little')
                dev.ctrl_transfer(0x40, 0x04, 0x0082, 0x0000, hdr, ob4800.TIMEOUT)
                try:
                    chunk = bytes(dev.read(ob4800.EP_IN, n, 3000))
                except Exception:
                    print('  таймаут после %d байт' % len(got)); break
                if not chunk:
                    zero += 1
                    if zero >= 20:
                        print('  20 пустых ответов подряд после %d байт' % len(got)); break
                    time.sleep(0.05); continue
                zero = 0
                got += chunk
        return got

    try:
        for i, o in enumerate(seq):
            if i in skip:
                if read_style != 'native' and i == first_read:
                    data += custom_read()
                continue
            if i == inject_at and overrides:
                for a, v in overrides:
                    dev.ctrl_transfer(0x40, 0x04, 0x0083, 0x0000,
                                      bytes([a, v]), ob4800.TIMEOUT)
                print('  подменено %d регистров перед стартом скана' % len(overrides))

            gap = min(o['dt'] - prev, 0.3)
            if gap > 0:
                time.sleep(gap)
            prev = o['dt']

            if width_test and i > inject_at and (
                    o['op'] == 'bin' or (o['op'] == 'wr' and o['wval'] == 0x82 and o['widx'] == 0)):
                if wt_done:
                    continue   # родные чтения после измерения пропускаем
                # первый родной запрос чтения: вместо него тянем всё до тишины
                wt_done = True
                lincnt, width = mode['_width_test']
                expect = mode['expect']

                def req(n):
                    hdr = bytes([0, 0, 0, 0x10]) + n.to_bytes(4, 'little')
                    dev.ctrl_transfer(0x40, 0x04, 0x0082, 0x0000, hdr, ob4800.TIMEOUT)
                    return bytes(dev.read(ob4800.EP_IN, n, 4000))

                # 1. ровно ожидаемый объём, как родной драйвер
                ok = True
                while len(data) < expect:
                    n = min(61440, expect - len(data))
                    try:
                        chunk = req(n)
                    except Exception:
                        print('  основной объём: обрыв на %d из %d байт' % (len(data), expect))
                        ok = False; break
                    if not chunk:
                        ok = False; break
                    data += chunk
                # 2. хвост: по одному байту на строку, пока отдаёт
                extra = 0
                if ok:
                    for _ in range(16):
                        try:
                            chunk = req(lincnt)
                        except Exception:
                            break
                        if len(chunk) < lincnt:
                            break
                        extra += 1; data += chunk
                print('ИЗМЕРЕНИЕ: запрошено %d px -> реально %d байт на строку (лишних %d), всего %d байт'
                      % (width, expect // lincnt + extra, extra, len(data)))
                continue
            if o['op'] == 'wr':
                dev.ctrl_transfer(0x40, o['breq'], o['wval'], o['widx'],
                                  bytes.fromhex(o['data']), ob4800.TIMEOUT)
            elif o['op'] == 'poll':
                want = bytes.fromhex(o['expect'])
                for _ in range(o['tries']):
                    got = bytes(dev.ctrl_transfer(0xc0, o['breq'], o['wval'],
                                                  o['widx'], o['wlen'], ob4800.TIMEOUT))
                    if got == want:
                        break
                    time.sleep(0.013)
                else:
                    if i > inject_at:
                        mismatch_after += 1
                        if mismatch_after <= 5:
                            print('  [%4d] опрос %04x: ждали %s, получили %s'
                                  % (i, o['widx'], want.hex(), got.hex()))
            elif o['op'] == 'bout':
                dev.write(ob4800.EP_OUT, bytes.fromhex(o['data']), ob4800.TIMEOUT)
            elif o['op'] == 'bin':
                if failed_at is not None:
                    continue
                try:
                    data += bytes(dev.read(ob4800.EP_IN, o['n'], 3000))
                except Exception:
                    failed_at = i
                    print('  чтение данных остановилось на операции %d, получено %d байт'
                          % (i, len(data)))
    except KeyboardInterrupt:
        print('прервано')
    finally:
        ob4800.stop(dev)
        usb.util.release_interface(dev, 0)

    print('время %.1f с' % (time.time() - t0))
    print('получено %d из %d байт' % (len(data), mode['expect']))
    if data:
        tail = data[-200000:]
        nz = sum(1 for b in tail if b)
        print('ненулевых в последних 200 КБ: %d (%.0f%%)' % (nz, 100.0 * nz / len(tail)))
        if out_path:
            open(out_path, 'wb').write(data)
    verdict = ('ДАННЫЕ ЕСТЬ' if len(data) >= mode['expect'] * 0.95
               else 'ДАННЫЕ ПРОПАЛИ' if failed_at is not None else 'НЕПОЛНЫЕ')
    print('вердикт:', verdict, '| несовпавших опросов после подмены:', mismatch_after)


def native_override(spec):
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'native_regs.json')
    nat = json.load(open(path))
    regs = {int(k, 16): int(v, 16) for k, v in nat['regs'].items()}
    fe = {int(k): v for k, v in nat['fe'].items()}
    motor = ({0x02} | set(range(0x21, 0x25)) | set(range(0x38, 0x3a))
             | set(range(0x5f, 0x6b)) | set(range(0x6b, 0x70)) | {0x80}
             | set(range(0xa6, 0xaa)) | set(range(0x67, 0x69)))
    want = set(); use_fe = False
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        if part == 'all':
            want |= set(regs); use_fe = True
        elif part == 'sensor':      # всё, кроме мотора и GPIO
            want |= set(regs) - motor; use_fe = True
        elif part == 'sensor-lo':   # сенсорная часть, адреса до 0x40
            want |= {a for a in regs if a < 0x40} - motor; use_fe = True
        elif part == 'sensor-hi':   # сенсорная часть, адреса от 0x40
            want |= {a for a in regs if a >= 0x40} - motor; use_fe = True
        elif part == 'afe':
            use_fe = True
        elif '-' in part:
            a, b = part.split('-'); want |= set(range(int(a, 16), int(b, 16) + 1))
        else:
            want.add(int(part, 16))
    if 'all' not in spec:
        want -= motor
    return [(a, regs[a]) for a in sorted(want) if a in regs], (fe if use_fe else {})


def run_genesys(seq, expect, out_path, native_spec=''):
    import usb.core, usb.util
    dev = usb.core.find(idVendor=ob4800.VID, idProduct=ob4800.PID)
    if dev is None:
        sys.exit('сканер не найден')
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass
    dev.set_configuration()
    usb.util.claim_interface(dev, 0)
    print('воспроизвожу последовательность genesys: %d операций' % len(seq))
    ov_regs, ov_fe = native_override(native_spec) if native_spec else ([], {})
    last_start = max(i for i, o in enumerate(seq)
                     if o['op'] == 'wr' and o['wval'] == 0x83 and o['data'] == '0f01')
    mism = 0; prev = seq[0]['dt']
    try:
        for i, o in enumerate(seq):
            if i == last_start and (ov_regs or ov_fe):
                for a, v in ov_regs:
                    dev.ctrl_transfer(0x40, 0x04, 0x0083, 0x0000, bytes([a, v]), ob4800.TIMEOUT)
                for a, v in sorted(ov_fe.items()):
                    dev.ctrl_transfer(0x40, 0x04, 0x0083, 0x0000,
                                      bytes([0x51, a, 0x3a, v >> 8, 0x3b, v & 0xff]), ob4800.TIMEOUT)
                print('  перед стартом записано регистров родного: %d, АЦП: %d'
                      % (len(ov_regs), len(ov_fe)))
            gap = min(o['dt'] - prev, 0.3)
            if gap > 0:
                time.sleep(gap)
            prev = o['dt']
            if o['op'] == 'wr':
                dev.ctrl_transfer(0x40, o['breq'], o['wval'], o['widx'],
                                  bytes.fromhex(o['data']), ob4800.TIMEOUT)
            elif o['op'] == 'poll':
                want = bytes.fromhex(o['expect'])
                for _ in range(o['tries']):
                    got = bytes(dev.ctrl_transfer(0xc0, o['breq'], o['wval'],
                                                  o['widx'], o['wlen'], ob4800.TIMEOUT))
                    if got == want:
                        break
                    time.sleep(0.013)
                else:
                    mism += 1
                    if mism <= 6:
                        print('  [%4d] опрос %04x: ждали %s, получили %s'
                              % (i, o['widx'], want.hex(), got.hex()))
            elif o['op'] == 'bout':
                dev.write(ob4800.EP_OUT, bytes.fromhex(o['data']), ob4800.TIMEOUT)
            elif o['op'] == 'bin':
                try:
                    dev.read(ob4800.EP_IN, o['n'], 3000)
                except Exception:
                    print('  [%4d] чтение %d байт не удалось' % (i, o['n']))
        # после старта: следим за 0x41 и читаем блоками, как родной драйвер
        t0 = time.time(); got = bytearray(); zero = 0
        seen = set()
        while len(got) < expect and time.time() - t0 < 25:
            st = bytes(dev.ctrl_transfer(0xc0, 0x04, 0x008e, 0x4122, 2, ob4800.TIMEOUT))[0]
            cnt = tuple(bytes(dev.ctrl_transfer(0xc0, 0x04, 0x008e, (a << 8) | 0x22, 2,
                                                ob4800.TIMEOUT))[0] for a in (0x42, 0x43, 0x44, 0x45))
            key = (st, cnt)
            if key not in seen:
                print('  0x41=%02x  счётчик 42..45 = %02x %02x %02x %02x  через %.2f с'
                      % ((st,) + cnt + (time.time() - t0,))); seen.add(key)
            n = min(61440, expect - len(got))
            hdr = bytes([0, 0, 0, 0x10]) + n.to_bytes(4, 'little')
            dev.ctrl_transfer(0x40, 0x04, 0x0082, 0x0000, hdr, ob4800.TIMEOUT)
            try:
                chunk = bytes(dev.read(ob4800.EP_IN, n, 2000))
            except Exception:
                chunk = b''
            if chunk:
                got += chunk; zero = 0
            else:
                zero += 1; time.sleep(0.1)
        print('получено %d из %d байт за %.1f с' % (len(got), expect, time.time() - t0))
        if got:
            nz = sum(1 for b in got[:200000] if b)
            print('ненулевых в первых 200 КБ: %d' % nz)
            if out_path:
                open(out_path, 'wb').write(got)
        print('вердикт:', 'ДАННЫЕ ЕСТЬ' if len(got) >= expect * 0.9 else 'ДАННЫЕ ПРОПАЛИ')
    finally:
        ob4800.stop(dev)
        usb.util.release_interface(dev, 0)
    print('каретка не запаркована: выключите и включите сканер перед следующим прогоном')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--set', default='', help='регистры, напр. 1e=f0,20=03')
    ap.add_argument('--group', type=int, help='готовая группа 1..4')
    ap.add_argument('--mode', default='max-300')
    ap.add_argument('--genesys-seq', help='файл последовательности genesys: '
                    'воспроизвести её целиком вместо родной, затем читать')
    ap.add_argument('--native-regs', default='',
                    help='перед стартом в последовательности genesys записать регистры '
                         'родного драйвера: all, или диапазоны вида 00-3f,60-ff, или afe')
    ap.add_argument('--drop', default='',
                    help='пропустить в последовательности genesys записи 0x8c по индексам, напр. 0f')
    ap.add_argument('--dram-edge', action='store_true',
                    help='в последовательность genesys вставить фронт ENBDRAM: '
                         '0b=42, a2=0f, 0b=4a сразу после первой записи a2')
    ap.add_argument('--drop-upload', default='',
                    help='убрать из последовательности genesys загрузки в память по типу '
                         '(байт 3 заголовка 0x82), напр. 01 - гамма, 10 - таблицы')
    ap.add_argument('--expect', type=int, default=590*588,
                    help='сколько байт ждать после последовательности genesys')
    ap.add_argument('--read-style', choices=['native', 'chunked', 'whole'],
                    default='native',
                    help='как читать основной скан: native - как в дампе; '
                         'chunked - запрос перед каждым чтением по 61440 (как genesys); '
                         'whole - один запрос на весь объём, затем чтения по 65536')
    ap.add_argument('--width-test', action='store_true',
                    help='подменить ENDPIXEL и измерить реальную ширину строки (байт/строку)')
    ap.add_argument('--skip-passes', action='store_true',
                    help='в родной последовательности убрать все проходы до основного '
                         'скана: старты мотора, опросы и чтения; записи остаются')
    ap.add_argument('--skip-readback', action='store_true',
                    help='убрать обратные чтения таблиц перед стартом скана')
    ap.add_argument('-o', '--out')
    args = ap.parse_args()

    if args.genesys_seq:
        import json, zlib, base64
        seq = json.loads(zlib.decompress(base64.b64decode(open(args.genesys_seq).read())))
        if args.drop:
            drop = {int(x, 16) for x in args.drop.split(',') if x}
            before = len(seq)
            seq = [o for o in seq if not (o['op'] == 'wr' and o['wval'] == 0x8c
                                          and o['widx'] in drop)]
            print('пропущено записей 0x8c: %d' % (before - len(seq)))
        if args.drop_upload:
            types = {int(x, 16) for x in args.drop_upload.split(',') if x}
            out = []; skip_next = False; n = 0
            for o in seq:
                if o['op'] == 'wr' and o['wval'] == 0x82 and o['widx'] == 1 \
                        and bytes.fromhex(o['data'])[3] in types:
                    skip_next = True; n += 1; continue
                if skip_next and o['op'] == 'bout':
                    skip_next = False; continue
                skip_next = False
                out.append(o)
            seq = out
            print('убрано загрузок в память: %d' % n)
        if args.dram_edge:
            out = []; done = False
            for o in seq:
                out.append(o)
                if (not done and o['op'] == 'wr' and o['wval'] == 0x83
                        and o['data'] == 'a20f'):
                    for d in ('0b42', 'a20f', '0b4a'):
                        out.append(dict(op='wr', breq=4, wval=0x83, widx=0, data=d, dt=o['dt']))
                    done = True
            seq = out
            print('вставлен фронт ENBDRAM:', 'да' if done else 'НЕТ, запись a2 не найдена')
        run_genesys(seq, args.expect, args.out, args.native_regs)
        return
    modes = ob4800.load_modes()
    mode = modes[args.mode]
    ov = parse_set(GROUPS[args.group]) if args.group else parse_set(args.set)
    print('режим %s, подмен: %s' % (args.mode,
          ' '.join('%02x=%02x' % x for x in ov) or 'нет'))
    run(mode, ov, args.out, args.skip_readback, args.read_style, args.skip_passes,
        args.width_test)


if __name__ == '__main__':
    main()
