#!/usr/bin/env python3
"""
Графическая оболочка для Plustek OpticBook 4800.

Требует рядом ob4800.py и ob4800_modes.dat.
Запуск:  python3 ob4800_gui.py
"""

import os, sys, threading, traceback, datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ob4800

# режимы, которых пока нет - показываем неактивными, чтобы было видно,
# какие дампы стоит снять с Windows
PLANNED = [
    ('a4-300-gray',  'A4, серый, 300 dpi'),
    ('a4-600-gray',  'A4, серый, 600 dpi'),
    ('a6-300-gray',  'A6, серый, 300 dpi'),
    ('max-300-bw',   'Полный размер, ч/б штриховой, 300 dpi'),
    ('max-600-bw',   'Полный размер, ч/б штриховой, 600 dpi'),
    ('max-1200',     'Полный размер, цвет, 1200 dpi'),
]

ORDER = ['max-300', 'max-600', 'max-300-gray', 'max-600-gray',
         'a4-300', 'a4-600',
         'a6-100', 'a6-200', 'a6-300', 'a6-400', 'a6-600']


class App:
    def __init__(self, root):
        self.root = root
        root.title('OpticBook 4800')
        root.geometry('660x560')

        try:
            import numpy, PIL          # noqa: F401
        except ImportError:
            messagebox.showerror(
                'Не хватает библиотек',
                'Нужны numpy и pillow:\n\n'
                'pip3 install numpy pillow --break-system-packages')
            raise SystemExit

        try:
            self.modes = ob4800.load_modes()
        except SystemExit as exc:
            messagebox.showerror('Ошибка', str(exc))
            raise

        self.pages = []
        self.busy = False
        self.outdir = os.path.join(os.path.expanduser('~'), 'Scans')
        os.makedirs(self.outdir, exist_ok=True)
        self.build()

    # ---------- интерфейс ----------

    def build(self):
        pad = dict(padx=10, pady=6)

        top = ttk.LabelFrame(self.root, text='Режим сканирования')
        top.pack(fill='x', **pad)

        self.mode_var = tk.StringVar()
        listwrap = ttk.Frame(top)
        listwrap.pack(fill='x', padx=8, pady=6)

        self.tree = ttk.Treeview(listwrap, columns=('size', 'vol'),
                                 show='tree headings', height=11)
        self.tree.heading('#0', text='Режим')
        self.tree.heading('size', text='Пикселей')
        self.tree.heading('vol', text='Объём')
        self.tree.column('#0', width=330)
        self.tree.column('size', width=130, anchor='e')
        self.tree.column('vol', width=90, anchor='e')
        self.tree.pack(side='left', fill='x', expand=True)

        sb = ttk.Scrollbar(listwrap, orient='vertical', command=self.tree.yview)
        sb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.tag_configure('planned', foreground='#999999')

        keys = [k for k in ORDER if k in self.modes]
        keys += [k for k in sorted(self.modes) if k not in keys]
        for k in keys:
            m = self.modes[k]
            self.tree.insert('', 'end', iid=k, text=m['title'],
                             values=('%d x %d' % (m['width'], m['lines']),
                                     '%.0f МБ' % (m['expect'] / 1048576)))
        for k, title in PLANNED:
            self.tree.insert('', 'end', iid='!' + k, text=title,
                             values=('не записан', ''), tags=('planned',))

        if keys:
            self.tree.selection_set(keys[0])

        opts = ttk.Frame(self.root)
        opts.pack(fill='x', **pad)
        self.gray_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text='перевести в серый',
                        variable=self.gray_var).pack(side='left')
        self.full_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text='без уменьшения до заявленного dpi',
                        variable=self.full_var).pack(side='left', padx=14)
        ttk.Label(opts, text='формат:').pack(side='left', padx=(14, 4))
        self.fmt_var = tk.StringVar(value='jpg')
        ttk.Combobox(opts, textvariable=self.fmt_var, width=6,
                     state='readonly',
                     values=('jpg', 'png', 'tif')).pack(side='left')

        btns = ttk.Frame(self.root)
        btns.pack(fill='x', **pad)
        self.b_scan = ttk.Button(btns, text='Сканировать в файл',
                                 command=self.scan_single)
        self.b_scan.pack(side='left')
        self.b_add = ttk.Button(btns, text='Добавить страницу',
                                command=self.scan_page)
        self.b_add.pack(side='left', padx=8)
        self.b_pdf = ttk.Button(btns, text='Сохранить PDF',
                                command=self.save_pdf, state='disabled')
        self.b_pdf.pack(side='left')
        self.b_clear = ttk.Button(btns, text='Очистить',
                                  command=self.clear_pages, state='disabled')
        self.b_clear.pack(side='left', padx=8)

        self.pbar = ttk.Progressbar(self.root, mode='determinate')
        self.pbar.pack(fill='x', padx=10)

        row = ttk.Frame(self.root)
        row.pack(fill='x', padx=10)
        ttk.Button(row, text='Папка сохранения...',
                   command=self.pick_dir).pack(side='left')
        self.dir_var = tk.StringVar()
        ttk.Label(row, textvariable=self.dir_var,
                  foreground='#555555').pack(side='left', padx=8)

        self.status = tk.StringVar(value='готов')
        ttk.Label(self.root, textvariable=self.status,
                  anchor='w').pack(fill='x', padx=12, pady=8)

        self.dir_var.set(self.outdir)

        hint = ('Неактивные режимы ещё не записаны с родного драйвера.\n'
                'Чтобы добавить: снимите дамп нужного режима на Windows.')
        ttk.Label(self.root, text=hint, foreground='#777777',
                  anchor='w', justify='left').pack(fill='x', padx=12)

    # ---------- вспомогательное ----------

    def selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        key = sel[0]
        if key.startswith('!'):
            messagebox.showinfo(
                'Режим не записан',
                'Этот режим пока недоступен: для него нет записи обмена '
                'с родного драйвера.\n\nСнимите дамп этого режима на Windows '
                'и добавьте его в набор.')
            return None
        return key

    def set_busy(self, busy, text=''):
        self.busy = busy
        state = 'disabled' if busy else 'normal'
        for b in (self.b_scan, self.b_add):
            b.configure(state=state)
        self.b_pdf.configure(
            state='normal' if (self.pages and not busy) else 'disabled')
        self.b_clear.configure(
            state='normal' if (self.pages and not busy) else 'disabled')
        if text:
            self.status.set(text)

    def progress(self, got, total):
        pct = 100.0 * got / total if total else 0
        self.pbar['value'] = pct
        self.status.set('получено %.1f из %.1f МБ'
                        % (got / 1048576, total / 1048576))

    def save_pic(self, pic, mode, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            pic.convert('RGB' if pic.mode != 'L' else 'L').save(
                path, quality=92, dpi=(mode['dpi'], mode['dpi']))
        elif ext == '.png':
            pic.save(path, compress_level=1, dpi=(mode['dpi'], mode['dpi']))
        else:
            pic.save(path, compression='tiff_deflate',
                     dpi=(mode['dpi'], mode['dpi']))

    def run_scan(self, key, done, save_to=None):
        mode = self.modes[key]

        def worker():
            try:
                raw = ob4800.scan(mode, 0.3, True,
                                  progress=lambda g, t: self.root.after(
                                      0, self.progress, g, t))
                if not raw:
                    raise RuntimeError('данные не получены')
                self.root.after(0, self.status.set, 'сборка изображения...')
                pic = ob4800.make_image(raw, mode, self.gray_var.get(),
                                        not self.full_var.get())
                if save_to:
                    self.root.after(0, self.status.set, 'сохранение файла...')
                    self.save_pic(pic, mode, save_to)
                self.root.after(0, done, pic, mode)
            except BaseException as exc:
                traceback.print_exc()
                self.root.after(0, self.failed, exc)

        self.set_busy(True, 'сканирование, держите руку на кабеле питания')
        self.pbar['value'] = 0
        threading.Thread(target=worker, daemon=True).start()

    def failed(self, exc):
        self.set_busy(False, 'сбой: %s' % exc)
        self.pbar['value'] = 0
        messagebox.showerror('Не получилось', str(exc))

    # ---------- действия ----------

    def scan_single(self):
        key = self.selected()
        if not key:
            return

        name = 'scan_%s_%s.%s' % (
            key, datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),
            self.fmt_var.get())
        dst = os.path.join(self.outdir, name)

        def done(pic, mode):
            self.set_busy(False, 'сохранено: %s' % dst)
            self.pbar['value'] = 0

        self.run_scan(key, done, save_to=dst)

    def scan_page(self):
        key = self.selected()
        if not key:
            return

        def done(pic, mode):
            self.pages.append(pic.convert('RGB'))
            self.set_busy(False, 'страниц в наборе: %d' % len(self.pages))
            self.pbar['value'] = 0

        self.run_scan(key, done)

    def pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.outdir)
        if d:
            self.outdir = d
            self.dir_var.set(d)

    def save_pdf(self):
        if not self.pages:
            return
        name = 'scan_%s.pdf' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        dst = os.path.join(self.outdir, name)
        head, rest = self.pages[0], self.pages[1:]
        n = len(self.pages)

        def worker():
            head.save(dst, save_all=True, append_images=rest, resolution=300)
            self.root.after(0, self.set_busy, False,
                            'сохранено %d страниц: %s' % (n, dst))

        self.set_busy(True, 'сборка PDF...')
        threading.Thread(target=worker, daemon=True).start()

    def clear_pages(self):
        self.pages = []
        self.set_busy(False, 'набор очищен')


def main():
    root = tk.Tk()
    try:
        App(root)
    except Exception:
        return
    root.mainloop()


if __name__ == '__main__':
    main()
