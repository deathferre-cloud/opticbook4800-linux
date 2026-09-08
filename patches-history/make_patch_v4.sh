#!/bin/bash
# Собирает opticbook4800-genesys-v4.patch из рабочего дерева ~/sane-backends
# (клон тега 1.2.1 с наложенными правками) и проверяет, что патч ложится на
# чистый клон 1.2.1 и собирается.
#
# Запуск:  bash make_patch_v4.sh
# Результат: ~/opticbook4800-genesys-v4.patch
set -e
TREE=~/sane-backends
OUT=~/opticbook4800-genesys-v4.patch

cd "$TREE"
if ! git rev-parse --verify 1.2.1 >/dev/null 2>&1; then
    git fetch --depth 1 origin tag 1.2.1
fi
echo "== файлы, отличающиеся от 1.2.1:"
git diff --stat 1.2.1 -- backend doc | tail -20

# только исходники, без результатов сборки
git diff 1.2.1 -- \
    backend/genesys \
    backend/genesys.conf.in \
    doc/descriptions/genesys.desc \
    > "$OUT"
echo "== патч: $OUT, $(wc -l < "$OUT") строк, $(grep -c '^diff --git' "$OUT") файлов"

# проверка на чистом клоне
CHK=$(mktemp -d /tmp/ob4800-check.XXXX)
echo "== проверка на чистом 1.2.1 в $CHK"
git clone --quiet --branch 1.2.1 --depth 1 https://gitlab.com/sane-project/backends.git "$CHK/src"
cd "$CHK/src"
git apply --check "$OUT" && echo "   ложится чисто"
git apply "$OUT"
echo "== сборка genesys на чистом клоне (2-5 минут)"
./autogen.sh >/dev/null 2>&1
./configure --prefix=/usr/local BACKENDS="genesys" >/dev/null
if make -j"$(nproc)" 2>&1 | grep -E " error"; then
    echo "   ОШИБКИ СБОРКИ — патч не готов"; exit 1
fi
echo "   собралось: $(ls -l backend/.libs/libsane-genesys.so.1.2.1 | awk '{print $5}') байт"
rm -rf "$CHK"
echo "== готово: $OUT"
