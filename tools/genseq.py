import struct, sys, json, zlib, base64, collections
sys.path.insert(0, '/home/claude')
from umon import usbmon

def build_from_usbmon(path, stop_after_start=None):
    """Последовательность операций genesys из usbmon. stop_after_start:
    номер старта мотора (0f01), после которого обрываем (сам старт включаем)."""
    pk = usbmon(path)
    c = collections.Counter((r['dev'], r['xfer']) for r in pk)
    dev = [k[0] for k, v in c.items() if k[1] == 2 and v > 300][0]
    out = []; t0 = None; pend = None; starts = 0
    for r in pk:
        if r['dev'] != dev:
            continue
        if t0 is None:
            t0 = r['ts']
        dt = round(r['ts'] - t0, 3)
        if r['xfer'] == 2 and r['typ'] == 'S' and r['fsetup'] == '\x00':
            bmr, breq, wval, widx, wlen = struct.unpack('<BBHHH', r['setup'])
            if bmr == 0x40:
                out.append(dict(op='wr', breq=breq, wval=wval, widx=widx,
                                data=r['data'].hex(), dt=dt))
                if wval == 0x83 and r['data'] == b'\x0f\x01':
                    starts += 1
                    if stop_after_start is not None and starts == stop_after_start:
                        return out, dev
            elif bmr == 0xc0:
                pend = dict(op='poll', breq=breq, wval=wval, widx=widx,
                            wlen=wlen, dt=dt)
        elif r['xfer'] == 2 and r['typ'] == 'C' and pend is not None:
            pend['expect'] = r['data'].hex(); pend['tries'] = 4
            out.append(pend); pend = None
        elif r['xfer'] == 3 and r['typ'] == 'S' and r['ep'] == 0x02 and r['data']:
            out.append(dict(op='bout', data=r['data'].hex(), dt=dt))
        elif r['xfer'] == 3 and r['typ'] == 'S' and r['ep'] == 0x81:
            out.append(dict(op='bin', n=r['length'], dt=dt))
    return out, dev

if __name__ == '__main__':
    seq, dev = build_from_usbmon(sys.argv[1], stop_after_start=int(sys.argv[2]))
    # сжимаем длинные серии одинаковых опросов
    packed = []
    for o in seq:
        if (packed and o['op'] == 'poll' and packed[-1]['op'] == 'poll'
                and packed[-1]['widx'] == o['widx'] and packed[-1]['wval'] == o['wval']):
            packed[-1]['expect'] = o['expect']; packed[-1]['tries'] += 4
            continue
        packed.append(o)
    k = collections.Counter(o['op'] for o in packed)
    print('устройство', dev, '| операций', len(packed), dict(k))
    blob = base64.b64encode(zlib.compress(json.dumps(packed).encode(), 9)).decode()
    open(sys.argv[3], 'w').write(blob)
    print('записано', sys.argv[3], len(blob), 'байт')
