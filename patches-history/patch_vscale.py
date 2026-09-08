#!/usr/bin/env python3
# OpticBook 4800: ниже 300 dpi мотор идёт с шагом 300, лишние строки
# усредняются в конвейере (так делает родной драйвер).
# Запуск из корня sane-backends:  python3 patch_vscale.py
import sys

def edit(path, old, new, must=1):
    s = open(path).read()
    n = s.count(old)
    if n != must:
        sys.exit('%s: ожидалось %d вхождений, найдено %d:\n%s' % (path, must, n, old[:80]))
    open(path, 'w').write(s.replace(old, new))
    print('ok:', path)

# ---------- 1. image_pipeline.h: объявление узла ----------
edit('backend/genesys/image_pipeline.h',
'''// A pipeline node that mimics the calibration behavior on Genesys chips
class ImagePipelineNodeCalibrate : public ImagePipelineNode''',
'''// A pipeline node that averages groups of source lines to reduce the image
// height (used when the scanner delivers lines at a fixed pitch above the
// requested vertical resolution, e.g. Plustek OpticBook 4800 below 300 dpi)
class ImagePipelineNodeScaleLines : public ImagePipelineNode
{
public:
    ImagePipelineNodeScaleLines(ImagePipelineNode& source, std::size_t height);

    std::size_t get_width() const override { return source_.get_width(); }
    std::size_t get_height() const override { return height_; }
    PixelFormat get_format() const override { return source_.get_format(); }

    bool eof() const override { return source_.eof(); }

    bool get_next_row_data(std::uint8_t* out_data) override;

private:
    ImagePipelineNode& source_;
    std::size_t height_ = 0;
    std::size_t factor_ = 1;

    std::vector<std::uint8_t> cached_line_;
    std::vector<std::uint32_t> accum_;
};

// A pipeline node that mimics the calibration behavior on Genesys chips
class ImagePipelineNodeCalibrate : public ImagePipelineNode''')

# ---------- 2. image_pipeline.cpp: реализация ----------
edit('backend/genesys/image_pipeline.cpp',
'''ImagePipelineNodeScaleRows::ImagePipelineNodeScaleRows(ImagePipelineNode& source,''',
'''ImagePipelineNodeScaleLines::ImagePipelineNodeScaleLines(ImagePipelineNode& source,
                                                         std::size_t height) :
    source_(source),
    height_{height}
{
    if (height_ > 0 && source_.get_height() > height_) {
        factor_ = source_.get_height() / height_;
    }
    cached_line_.resize(source_.get_row_bytes());
    accum_.resize(get_width() * get_pixel_channels(get_format()));
}

bool ImagePipelineNodeScaleLines::get_next_row_data(std::uint8_t* out_data)
{
    auto format = get_format();
    auto channels = get_pixel_channels(format);
    auto width = get_width();

    std::fill(accum_.begin(), accum_.end(), 0);

    bool got_data = true;
    std::size_t taken = 0;
    for (std::size_t i = 0; i < factor_; i++) {
        if (!source_.get_next_row_data(cached_line_.data())) {
            got_data = false;
            break;
        }
        taken++;
        for (std::size_t x = 0; x < width; x++) {
            for (unsigned c = 0; c < channels; c++) {
                accum_[x * channels + c] += get_raw_channel_from_row(cached_line_.data(), x, c,
                                                                     format);
            }
        }
    }
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

ImagePipelineNodeScaleRows::ImagePipelineNodeScaleRows(ImagePipelineNode& source,''')

# ---------- 3. low.cpp: расчёт сессии ----------
edit('backend/genesys/low.cpp',
'''    s.color_shift_lines_r = (s.color_shift_lines_r * s.params.yres) / dev->motor.base_ydpi;
    s.color_shift_lines_g = (s.color_shift_lines_g * s.params.yres) / dev->motor.base_ydpi;
    s.color_shift_lines_b = (s.color_shift_lines_b * s.params.yres) / dev->motor.base_ydpi;''',
'''    // OpticBook 4800: below 300 dpi the motor keeps the 300 dpi pitch and the
    // extra lines are averaged down in the image pipeline
    unsigned ob4800_line_scale = 1;
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_3800 && s.params.yres < 300) {
        ob4800_line_scale = 300 / s.params.yres;
    }
    unsigned motor_yres = s.params.yres * ob4800_line_scale;

    s.color_shift_lines_r = (s.color_shift_lines_r * motor_yres) / dev->motor.base_ydpi;
    s.color_shift_lines_g = (s.color_shift_lines_g * motor_yres) / dev->motor.base_ydpi;
    s.color_shift_lines_b = (s.color_shift_lines_b * motor_yres) / dev->motor.base_ydpi;''')

edit('backend/genesys/low.cpp',
'''    s.output_line_count = s.params.lines + s.max_color_shift_lines + s.num_staggered_lines;''',
'''    s.output_line_count = s.params.lines * ob4800_line_scale + s.max_color_shift_lines
                          + s.num_staggered_lines;''')

# ---------- 4. low.cpp: узел в конвейере ----------
edit('backend/genesys/low.cpp',
'''    if (pipeline.get_output_width() != session.params.get_requested_pixels()) {
        pipeline.push_node<ImagePipelineNodeScaleRows>(session.params.get_requested_pixels());
    }

    return pipeline;''',
'''    if (pipeline.get_output_width() != session.params.get_requested_pixels()) {
        pipeline.push_node<ImagePipelineNodeScaleRows>(session.params.get_requested_pixels());
    }

    if (dev.model->model_id == ModelId::PLUSTEK_OPTICBOOK_3800 && session.params.yres < 300 &&
        pipeline.get_output_height() > session.params.lines)
    {
        pipeline.push_node<ImagePipelineNodeScaleLines>(session.params.lines);
    }

    return pipeline;''')

# ---------- 5. gl846.cpp: мотор ниже 300 идёт как на 300 ----------
edit('backend/genesys/gl846.cpp',
'''  slope_dpi = slope_dpi * (1 + dummy);''',
'''  slope_dpi = slope_dpi * (1 + dummy);

    // OpticBook 4800: the motor never runs slower than the 300 dpi pitch,
    // lower resolutions are produced by averaging lines in the pipeline
    if (dev->model->model_id == ModelId::PLUSTEK_OPTICBOOK_3800 && slope_dpi < 300) {
        slope_dpi = 300;
    }''')

print('все правки применены')
