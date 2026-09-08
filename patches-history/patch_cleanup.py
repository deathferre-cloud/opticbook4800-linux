#!/usr/bin/env python3
# OpticBook 4800: уборка перед отправкой в SANE.
#  1. Убирает неиспользуемый узел ImagePipelineNodeScaleLines (его заменил
#     ImagePipelineNodeResampleLines).
#  2. Убирает отладочную печать "OB4800 px1000" из genesys.cpp.
#     Вернуть её можно скриптом patch_dbg_cache.py.
# Запуск из корня sane-backends:  python3 patch_cleanup.py
import re, sys

def cut(path, start_marker, end_marker, what):
    s = open(path).read()
    b = s.find(start_marker)
    if b < 0:
        print('пропущено (уже убрано):', what); return
    e = s.find(end_marker, b)
    if e < 0:
        sys.exit('%s: не найден конец блока %s' % (path, what))
    open(path, 'w').write(s[:b] + s[e:])
    print('убрано:', what, '->', path)

# 1. объявление класса в image_pipeline.h
cut('backend/genesys/image_pipeline.h',
    '// A pipeline node that averages groups of source lines to reduce the image',
    '// A pipeline node that reduces the number of lines by an arbitrary ratio,',
    'ImagePipelineNodeScaleLines (объявление)')

# 2. реализация в image_pipeline.cpp
cut('backend/genesys/image_pipeline.cpp',
    'ImagePipelineNodeScaleLines::ImagePipelineNodeScaleLines(ImagePipelineNode& source,',
    'ImagePipelineNodeResampleLines::ImagePipelineNodeResampleLines(ImagePipelineNode& source,',
    'ImagePipelineNodeScaleLines (реализация)')

# 3. отладочная печать
s = open('backend/genesys/genesys.cpp').read()
m = re.search(r'\n *if \(pixels_per_line > 1000\) \{.*?\n *\}\n', s, re.S)
if m and 'OB4800 px1000' in m.group(0):
    open('backend/genesys/genesys.cpp', 'w').write(s[:m.start()] + '\n' + s[m.end():])
    print('убрано: отладочная печать OB4800 px1000 -> backend/genesys/genesys.cpp')
else:
    print('пропущено (уже убрано): отладочная печать')

print('готово. проверка, что ScaleLines больше не упоминается:')
import subprocess
subprocess.run(['grep', '-rn', 'ScaleLines', 'backend/genesys/'])
