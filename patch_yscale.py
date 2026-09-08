#!/usr/bin/env python3
# OpticBook 4800: поправка вертикального масштаба (0.4%, как по горизонтали).
# Сканер отдаёт на 1200/1195 больше строк, конвейер уплотняет их до запрошенных
# новым узлом ResampleLines (дробный коэффициент, усреднение).
# Запуск из корня sane-backends:  python3 patch_yscale.py
import sys

def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit('%s: фрагмент найден %d раз, ожидался 1:\n%s' % (path, s.count(old), old[:90]))
    open(path, 'w').write(s.replace(old, new)); print('ok:', path)

# ---------- 1. image_pipeline.h ----------
edit('backend/genesys/image_pipeline.h',
'''// A pipeline node that keeps only the first `width` pixels of every row''',
'''// A pipeline node that reduces the number of lines by an arbitrary ratio,
// averaging the source lines that fall into each output line
class ImagePipelineNodeResampleLines : public ImagePipelineNode
{
public:
    ImagePipelineNodeResampleLines(ImagePipelineNode& source, std::size_t height);

    std::size_t get_width() const override { return source_.get_width(); }
    std::size_t get_height() const override { return height_; }
    PixelFormat get_format() const override { return source_.get_format(); }

    bool eof() const override { return source_.eof(); }

    bool get_next_row_data(std::uint8_t* out_data) override;

private:
    ImagePipelineNode& source_;
    std::size_t height_ = 0;
    std::size_t source_height_ = 0;
    std::size_t out_row_ = 0;
    std::size_t consumed_ = 0;

    std::vector<std::uint8_t> cached_line_;
    std::vector<std::uint32_t> accum_;
};

// A pipeline node that keeps only the first `width` pixels of every row''')

# ---------- 2. image_pipeline.cpp ----------
edit('backend/genesys/image_pipeline.cpp',
'''ImagePipelineNodeCropColumns::ImagePipelineNodeCropColumns(ImagePipelineNode& source,''',
'''ImagePipelineNodeResampleLines::ImagePipelineNodeResampleLines(ImagePipelineNode& source,
                                                               std::size_t height) :
    source_(source),
    height_{height},
    source_height_{source.get_height()}
{
    cached_line_.resize(source_.get_row_bytes());
    accum_.resize(get_width() * get_pixel_channels(get_format()));
}

bool ImagePipelineNodeResampleLines::get_next_row_data(std::uint8_t* out_data)
{
    auto format = get_format();
    auto channels = get_pixel_channels(format);
    auto width = get_width();

    // source lines belonging to this output line: [consumed_, target)
    std::size_t target = ((out_row_ + 1) * source_height_) / height_;
    if (target <= consumed_) {
        target = consumed_ + 1;
    }
    std::fill(accum_.begin(), accum_.end(), 0);

    bool got_data = true;
    std::size_t taken = 0;
    while (consumed_ < target) {
        if (!source_.get_next_row_data(cached_line_.data())) {
            got_data = false;
            break;
        }
        consumed_++;
        taken++;
        for (std::size_t x = 0; x < width; x++) {
            for (unsigned c = 0; c < channels; c++) {
                accum_[x * channels + c] += get_raw_channel_from_row(cached_line_.data(), x, c,
                                                                     format);
            }
        }
    }
    out_row_++;
    if (taken == 0) {
        return false;
    }
    for (std::size_t x = 0; x < width; x++) {
        for (unsigned c = 0; c < channels; c++) {
            set_raw_channel_to_row(out_data, x, c, accum_[x * channels + c] / taken, format);
        }
    }
    return got_data;
}

ImagePipelineNodeCropColumns::ImagePipelineNodeCropColumns(ImagePipelineNode& source,''')

# ---------- 3. low.cpp: больше строк от сканера ----------
edit('backend/genesys/low.cpp',
'''    s.output_line_count = s.params.lines * ob4800_line_scale + s.max_color_shift_lines
                          + s.num_staggered_lines;''',
'''    unsigned ob4800_lines = s.params.lines * ob4800_line_scale;
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800) {
        // the motor step is 0.4% finer than nominal (same as the CCD pitch):
        // fetch 1200/1195 more lines, the pipeline resamples them down
        ob4800_lines = (ob4800_lines * 1200 + 1194) / 1195;
    }
    s.output_line_count = ob4800_lines + s.max_color_shift_lines + s.num_staggered_lines;''')

# ---------- 4. low.cpp: узел в конвейере (вместо ScaleLines) ----------
edit('backend/genesys/low.cpp',
'''    if (dev.model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 && session.params.yres < 300 &&
        pipeline.get_output_height() > session.params.lines)
    {
        pipeline.push_node<ImagePipelineNodeScaleLines>(session.params.lines);
    }''',
'''    if (dev.model->model_id == ModelId::PLUSTEK_OPTICBOOK_4800 &&
        pipeline.get_output_height() > session.params.lines)
    {
        pipeline.push_node<ImagePipelineNodeResampleLines>(session.params.lines);
    }''')
print('все правки применены')
