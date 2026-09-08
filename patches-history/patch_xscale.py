#!/usr/bin/env python3
# OpticBook 4800: поправка горизонтального масштаба (шаг сенсора на 0.4% мельче
# номинала). Чип получает те же запросы, что и раньше; строка растягивается
# в конвейере на 1200/1195 и обрезается справа до запрошенной ширины.
# Запуск из корня sane-backends:  python3 patch_xscale.py
import sys

def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit('%s: фрагмент найден %d раз, ожидался 1:\n%s' % (path, s.count(old), old[:90]))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path)

# ---------- 1. image_pipeline.h: объявление узла обрезки ----------
edit('backend/genesys/image_pipeline.h',
'''// A pipeline node that mimics the calibration behavior on Genesys chips
class ImagePipelineNodeCalibrate : public ImagePipelineNode''',
'''// A pipeline node that keeps only the first `width` pixels of every row
// (used together with ScaleRows to correct a slightly wrong pixel pitch)
class ImagePipelineNodeCropColumns : public ImagePipelineNode
{
public:
    ImagePipelineNodeCropColumns(ImagePipelineNode& source, std::size_t width);

    std::size_t get_width() const override { return width_; }
    std::size_t get_height() const override { return source_.get_height(); }
    PixelFormat get_format() const override { return source_.get_format(); }

    bool eof() const override { return source_.eof(); }

    bool get_next_row_data(std::uint8_t* out_data) override;

private:
    ImagePipelineNode& source_;
    std::size_t width_ = 0;
    std::vector<std::uint8_t> cached_line_;
};

// A pipeline node that mimics the calibration behavior on Genesys chips
class ImagePipelineNodeCalibrate : public ImagePipelineNode''')

# ---------- 2. image_pipeline.cpp: реализация ----------
edit('backend/genesys/image_pipeline.cpp',
'''ImagePipelineNodeScaleRows::ImagePipelineNodeScaleRows(ImagePipelineNode& source,''',
'''ImagePipelineNodeCropColumns::ImagePipelineNodeCropColumns(ImagePipelineNode& source,
                                                           std::size_t width) :
    source_(source),
    width_{std::min(width, source.get_width())}
{
    cached_line_.resize(source_.get_row_bytes());
}

bool ImagePipelineNodeCropColumns::get_next_row_data(std::uint8_t* out_data)
{
    bool got_data = source_.get_next_row_data(cached_line_.data());
    // formats used here are byte aligned per pixel, so the row prefix is the crop
    std::memcpy(out_data, cached_line_.data(), get_row_bytes());
    return got_data;
}

ImagePipelineNodeScaleRows::ImagePipelineNodeScaleRows(ImagePipelineNode& source,''')

# заголовок для memcpy, если его нет
s = open('backend/genesys/image_pipeline.cpp').read()
if '#include <cstring>' not in s:
    s = s.replace('#include <cmath>', '#include <cmath>\n#include <cstring>', 1)
    open('backend/genesys/image_pipeline.cpp', 'w').write(s); print('ok: cstring')

# ---------- 3. low.cpp: узлы в конвейере ----------
edit('backend/genesys/low.cpp',
'''    if (pipeline.get_output_width() != session.params.get_requested_pixels()) {
        pipeline.push_node<ImagePipelineNodeScaleRows>(session.params.get_requested_pixels());
    }
''',
'''    if (pipeline.get_output_width() != session.params.get_requested_pixels()) {
        pipeline.push_node<ImagePipelineNodeScaleRows>(session.params.get_requested_pixels());
    }

    if (dev.model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
        get_pixel_format_depth(pipeline.get_output_format()) >= 8)
    {
        // the CCD pixel pitch is 0.4% finer than nominal (measured 85.26 mm for
        // an 85.60 mm card): stretch the row by 1200/1195 and drop the excess
        // on the right, so that the requested width covers the requested mm
        unsigned want = session.params.get_requested_pixels();
        unsigned stretched = (want * 1200 + 1194) / 1195;
        if (stretched > want) {
            pipeline.push_node<ImagePipelineNodeScaleRows>(stretched);
            pipeline.push_node<ImagePipelineNodeCropColumns>(want);
        }
    }
''')
print('все правки применены')
