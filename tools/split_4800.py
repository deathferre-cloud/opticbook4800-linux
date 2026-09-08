#!/usr/bin/env python3
"""Из дерева '1.2.1 + патч 4800 поверх 3800' делает дерево, где OpticBook 3800
остаётся оригинальным, а OpticBook 4800 — отдельная модель.
Запуск из корня репозитория, в котором наложен opticbook4800-genesys-v2.patch."""
import re, subprocess, sys

G = 'backend/genesys/'

def sh(cmd):
    return subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True).stdout

def orig(path):
    return sh('git show HEAD:%s' % path)

def read(p): return open(p).read()
def write(p, s): open(p, 'w').write(s)

# ---------- 1. код: добавленные строки с 3800 -> 4800 ----------
for f in ('gl846.cpp', 'low.cpp'):
    path = G + f
    diff = sh('git diff -U0 -- %s' % path)
    added = set()
    new_ln = 0
    for line in diff.splitlines():
        m = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', line)
        if m:
            new_ln = int(m.group(1)); continue
        if line.startswith('+++') or line.startswith('---'):
            continue
        if line.startswith('+'):
            added.add(new_ln); new_ln += 1
        elif line.startswith('-'):
            pass
        else:
            new_ln += 1
    lines = read(path).split('\n')
    n = 0
    for i in sorted(added):
        if 'PLUSTEK_OPTICBOOK_3800' in lines[i - 1]:
            lines[i - 1] = lines[i - 1].replace('PLUSTEK_OPTICBOOK_3800', 'PLUSTEK_OPTICBOOK_4800'); n += 1
    s = '\n'.join(lines)
    if f == 'gl846.cpp':
        old = '''    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_3800) {
        dev->reg.init_reg(0x0b, 0x4a);
    }'''
        new = '''    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_3800) {
        dev->reg.init_reg(0x0b, 0x2a);
    }
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        dev->reg.init_reg(0x0b, 0x4a);   // 40 MHz clock, as the native driver
    }'''
        assert s.count(old) == 1, '0x0b block'
        s = s.replace(old, new); n += 1
    write(path, s)
    print('%s: заменено %d мест' % (f, n))

# ---------- 2. enums.h: новые идентификаторы ----------
p = G + 'enums.h'; s = read(p)
s = s.replace('    PLUSTEK_OPTICBOOK_3800,\n', '    PLUSTEK_OPTICBOOK_3800,\n    PLUSTEK_OPTICBOOK_4800,\n')
s = s.replace('    CCD_PLUSTEK_OPTICBOOK_3800,\n', '    CCD_PLUSTEK_OPTICBOOK_3800,\n    CCD_PLUSTEK_OPTICBOOK_4800,\n')
write(p, s)
print('enums.h: добавлено %d идентификаторов' % s.count('OPTICBOOK_4800'))

# ---------- 3. таблицы ----------
def block(text, start_pat, from_idx, next_pat):
    """[start .. до следующего start_pat) — блок одной записи таблицы."""
    a = text.index(start_pat, from_idx)
    b = text.find(next_pat, a + len(start_pat))
    if b < 0:
        b = text.rindex('}', 0, len(text))          # конец функции
        # обрезаем по последней записи: до закрывающей скобки функции
    return a, b

def split_table(fname, start_pat, key3800, rename):
    """3800 -> оригинал; после него вставляется блок 4800 из патченной версии."""
    path = G + fname
    patched = read(path); original = orig(path)
    # блок 3800 в патченном файле
    k = patched.index(key3800)
    a = patched.rindex(start_pat, 0, k)
    b = patched.find(start_pat, a + len(start_pat))
    if b < 0:
        b = patched.rindex('\n}', 0, len(patched)) + 1
    new_block = patched[a:b]
    for old, new in rename:
        new_block = new_block.replace(old, new)
    # место вставки в оригинале: после оригинального блока 3800
    k2 = original.index(key3800)
    a2 = original.rindex(start_pat, 0, k2)
    b2 = original.find(start_pat, a2 + len(start_pat))
    if b2 < 0:
        b2 = original.rindex('\n}', 0, len(original)) + 1
    out = original[:b2] + new_block + original[b2:]
    write(path, out)
    print('%s: 3800 восстановлен, 4800 добавлен (%d строк)' % (fname, new_block.count('\n')))

common = [('PLUSTEK_OPTICBOOK_3800', 'PLUSTEK_OPTICBOOK_4800')]

split_table('tables_model.cpp', '    model = Genesys_Model();\n', 'ModelId::PLUSTEK_OPTICBOOK_3800;',
            common + [('"plustek-opticbook-3800"', '"plustek-opticbook-4800"'),
                      ('"OpticBook 3800"', '"OpticBook 4800"'),
                      ('    s_usb_devices->emplace_back(0x07b3, 0x1300, model);\n', '')])
split_table('tables_sensor.cpp', '    sensor = Genesys_Sensor();\n', 'CCD_PLUSTEK_OPTICBOOK_3800;', common)
split_table('tables_motor.cpp', '    motor = Genesys_Motor();\n', 'MotorId::PLUSTEK_OPTICBOOK_3800;', common)
split_table('tables_gpo.cpp', '    gpo = Genesys_Gpo();\n', 'GpioId::PLUSTEK_OPTICBOOK_3800;', common)
split_table('tables_memory_layout.cpp', '    ml = MemoryLayout();\n', 'ModelId::PLUSTEK_OPTICBOOK_3800 }', common)

# frontend: оригинал не трогали, нужна копия записи под новый AdcId
p = G + 'tables_frontend.cpp'; s = read(p)
k = s.index('AdcId::PLUSTEK_OPTICBOOK_3800;')
a = s.rindex('    fe = Genesys_Frontend();\n', 0, k)
b = s.find('    fe = Genesys_Frontend();\n', a + 10)
blk = s[a:b].replace('PLUSTEK_OPTICBOOK_3800', 'PLUSTEK_OPTICBOOK_4800')
s = s[:b] + blk + s[b:]
write(p, s); print('tables_frontend.cpp: запись 4800 добавлена')

# ---------- 4. контроль ----------
left = sh('git diff -- %stables_model.cpp %stables_sensor.cpp %stables_motor.cpp %stables_gpo.cpp %stables_memory_layout.cpp'
          % (G, G, G, G, G))
removed = [l for l in left.splitlines() if l.startswith('-') and not l.startswith('---')]
print('удалённых строк в таблицах (должно быть 0, 3800 не тронут):', len(removed))
for l in removed[:5]: print('  ', l)
