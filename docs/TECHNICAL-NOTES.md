# Plustek OpticBook 4800 support for the SANE genesys backend (v5)

**Device:** Plustek OpticBook 4800, USB `07b3:1301`, ASIC GL845 (reported by
`sane-find-scanner`), CCD, LED lamp, book-edge flatbed.
**Base:** sane-backends 1.2.1, `backend/genesys`.
**Status:** working. Gray and color, 75/100/150/200/300/600/1200 dpi, all
verified on paper (full A4 pages at 300/600/1200), shading calibration
enabled with a single white target for all modes; white paper comes out at
195–199/255 in every mode (gray and color, all three CCD clockings agree to
within ~2 %), color balance on white 197/197/199, no vertical banding at any
resolution including 1200 dpi. Full page gray 300 dpi ≈ 9 s, 600 dpi ≈ 18 s;
the first scan in a mode adds 3–6 s of shading calibration (at 1200 dpi a
lamp-off dark pass plus the white pass), which is then cached.

The scanner is a separate model (`ModelId::PLUSTEK_OPTICBOOK_4800`, with its
own sensor, motor, GPIO, ADC and memory-layout entries); the existing
OpticBook 3800 tables and code paths are left untouched, except that the
3800-specific register initialisation in `gl846.cpp` is shared with the 4800
(all but register 0x0b, which is 0x4a on the 4800). Register values were
taken from USB captures of the Windows driver; everything below was verified
on hardware, most of it with a measuring script on real scans.

## What was needed (and why) — GL845 specifics

1. **BUFEMPTY never clears** in the register configuration used by the
   backend, although data can be read. `wait_until_buffer_non_empty()`
   returns immediately for this model; `read_valid_words()` works.
2. **Register 0x0e must stay 1** after the boot pulse, otherwise the word
   counter (0x42–0x45) never updates. `asic_boot()` writes 0x0e=1 again.
3. **SCANMOD (0x06) must be 0** during the scan; the native driver sets 0x06
   from 0xf0 to 0x10 right before starting.
4. **Memory layout depends on channel count**: gray uses two large segments
   repeated three times and 0xf8=0x23; color uses six segments and 0xf8=0x05.
   Written per scan in `gl846_init_optical_regs_scan()`; 0xf8 is set through
   the register set because the bulk write would overwrite it.
5. **AFE (Wolfson-style ADC)**: written directly in `gl846_set_adi_fe()`.
   Registers 2–4 are the **gains** (0x3e/0x34/0x39 for R/G/B from the
   native 300 dpi capture), registers 5–7 (0x114/0x10c/0x10d, 9-bit values)
   are offsets — measured, not assumed: changing 2–4 scales the image,
   changing 5–7 by ±64 does nothing visible. The 600 dpi and 1200 dpi CCD
   clockings deliver ~30 % more signal and saturate on plain white paper, so
   for 200/600/1200 dpi the gains are 24 codes lower (0x26/0x1c/0x21; the
   gain code is not linear, there is a range bit at 0x20). ADC and exposure
   calibrations remain disabled (`DISABLE_ADC_CALIBRATION`,
   `DISABLE_EXPOSURE_CALIBRATION`). The clocking group is taken from the
   sensor passed to `set_fe()` (`shading_resolution`), not from
   `dev->session`, which is not yet updated at that point — using it broke
   scans restored from the calibration cache (they got the 1200 dpi AFE
   setup).
6. **Shading calibration is enabled** and needed several model-specific
   steps, all in `genesys.cpp` / `gl846.cpp` / `tables_sensor.cpp`:
   - the chip delivers **8-bit data only**; the calibration scans (which the
     generic code reads at 16 bit, bypassing the pipeline) run at 8 bit and
     are widened to 16 bit (`v<<8|v`); the read is limited to what the chip
     actually sends (`dev->total_bytes_to_read`) — see item 16;
   - the white strip lies at **20–34 mm** from the home position (black
     frame before that); calibration is done at 24–28 mm;
   - each CCD clocking group calibrates with **its own profile**
     (`shading_resolution` = 300/600/1200, `shading_factor` = 1): calibrating
     everything at 1200 dpi gave coefficients for the wrong exposure;
   - coefficients are computed with `compute_coefficients()` (channel-
     interleaved averages → one 12-byte record per delivered pixel:
     dark_R gain_R dark_G gain_G dark_B gain_B, 16-bit LE, unity gain 0x2000,
     linear, no ceiling — verified with synthetic ×0.5/×1.5/×2/×4 stripes);
   - the **shading table memory is paged**: 512 bytes per page, 42 records
     per page, the last 8 bytes of each page unused (writing records back to
     back produced 42-pixel wide steps with a 3-page cycle);
   - the chip indexes the table **from the first pixel of the scan window,
     counted from `params.startx` without the sensor's `output_pixel_offset`**
     (verified by aligning a dust speck on the glass: the residual offset was
     exactly the 17-pixel `output_pixel_offset` of the 300 dpi group);
   - **one white target for all groups** (0xa400, see item 18); the earlier
     per-group targets compensated a dark-level error, not a property of the
     clockings;
   - the calibration strip under the frame sees the LED lamp ripple at a
     different contrast than a document on the glass does (the strip is above
     the glass plane): calibrating from the strip left ±8 % vertical bands on
     full-width scans, identical at any strip position. The backend therefore
     supports a per-unit **white reference file**
     (`~/.sane/opticbook4800-white-<300|600|1200>.dat`, plus
     `-1200-gray.dat` for the single-channel 1200 dpi calibration), captured
     once with a white sheet on the glass through the normal calibration path
     (`OB4800_CALIB_Y_MM=40 OB4800_WHITE_REF_SAVE=1`, scan started behind the
     calibration area with `-t 20`, in the mode — Gray or Color — the file is
     for). The file header carries the calibration window start
     (`OB4800WREF2 <pixels> 3 <startx>`); the averaged lines are stored from
     sensor pixel 0 (zeros below the window start), so the loader takes the
     first `pixels_per_line` records and requires the file to start no later
     and to be no shorter than the current window. When the file exists it
     replaces the strip's white average, rebased onto the dark level measured
     in the current pass (the file keeps its own pedestal in its dummy
     columns; mixing the file's white with today's dark left an additive
     error that showed as a 3–5 % bright zone on the steep left slope of the
     lamp dome). This is essentially what the native driver's "calibrate with
     a white sheet" does.
7. **Color raw line width**: `output_line_bytes_raw` must be multiplied by
   the channel count (same as CANON_5600F) — otherwise the pipeline reads one
   channel's worth of bytes per line and the image is horizontally smeared.
8. **Motor**: `base_ydpi = 1200`, half steps, 292-step acceleration ramp
   down to period 875 (the backend halves table values). A short ramp or a
   faster target speed stalls the motor. Profiles for LPERIOD 3500 (≤300 dpi),
   5500 (200/600 dpi) and 11000 (1200 dpi).
9. **Sensor pitch is fixed per hardware mode**: DPISET is always 1200; the
   300-dpi pitch is selected by the default CCD clocking, the 600-dpi pitch by
   0x18=0x01, 0x1a=0x30, 0x58=0x01, 0x59=0x31, 0x70–0x73 = 00 01 01 02, and
   the 1200-dpi pitch by a third clocking set (0x1c, 0x52–0x5a, 0x70–0x76)
   plus AFE configuration register 0 = 0xf8 and GPIO 0x6d = 0.
   Resolutions below 300 are scanned at the 300 pitch, 200 dpi at the 600
   pitch (like the native driver), and reduced in software: rows by the
   existing `ScaleRows` node, lines by the new `ImagePipelineNodeResampleLines`
   node (averaging), with the motor kept at the hardware pitch.
10. **Home sensor** is bit 5 (0x20) of 0x41 on this ASIC, not bit 3 — already
    handled by the existing 3800 code path.
11. **Pixel pitch correction.** Measured with an ISO/IEC 7810 card, the CCD
    pitch and the motor step are both 0.4 % coarser than nominal (the native
    Windows driver has the same error). The ASIC requests are left
    unchanged; the pipeline stretches each row by 1200/1195 (`ScaleRows`)
    and a new `ImagePipelineNodeCropColumns` drops the excess on the right;
    vertically 1195/1200 of the lines are requested and
    `ImagePipelineNodeResampleLines` stretches them. A 210 mm sheet now
    measures 210.0 mm in both directions.
12. **Per-clocking frame origin.** The three CCD clockings start the frame at
    different places: 600 dpi ~0.95 mm and 1200 dpi ~1.42 mm to the right of
    the 300 dpi clocking (measured with the same card at all three
    resolutions). `x_offset` is set for the 1200 dpi group and the others get
    the difference back through `Genesys_Sensor::output_pixel_offset`
    (+4/+6/+8/+17 px for 75/100/150/300, +4/+11 px for 200/600). Negative
    offsets are not possible (the shading calibration of these groups runs
    with startx = 0).
13. Geometry: `x_offset 3.88`, `x_size 212.7`, `y_offset 34.0`, `y_size 298`,
    `y_offset_calib_white 24.0`, `y_size_calib_mm 4.0`. `x_size` ends the
    frame at the end of the CCD line (10200 px = 215.9 mm from the sensor
    origin; 212.75 mm of frame after the pitch correction) — the native
    driver's "full size" mode reads the same 10200 px; the glass extends
    ~6 mm further to the right with no sensor under it. The offsets start
    0.5 mm inside the paper edge so that a sheet at the stop never shows the
    frame; consequently an exact A4 request covers 0.5 mm of lid backing on
    the right (the native driver's A4 is 210.2 mm from the same origin and
    does the same). That strip is what is really on the glass and is left
    as is; frontends that take a numeric width (scanimage, xsane, gscan2pdf)
    can stop the frame inside the sheet.
14. **`SHADING_REPARK`.** After the white calibration the head is parked, so
    that a scan starts from the home position whether or not it was preceded
    by calibration. Without it the head-position bookkeeping after the
    calibration pass shifted the frame by ~3.8 mm at 300 dpi.
15. **Carriage protection.** The carriage cannot move backwards; if a
    calibration area were requested behind the scan start the head would be
    driven into the end stop. `init_regs_for_shading()` refuses such a
    configuration with `SANE_STATUS_INVAL` before any movement.
16. **Shading at the full CCD clock (1200 dpi) is done in the scan's window
    and read-out mode.** genesys always calibrates with three channels from
    sensor pixel 0. At the full clock this reference does not describe the
    frame: narrow response defects of the CCD line (dust in the optical path,
    ~30 px wide, −5…−7 %) sit at different pixels — or vanish — in a
    three-channel pass started at pixel 0, so shading left them as vertical
    stripes with a bright ghost next to each. For the full-clock group the
    calibration session now uses the scan's window (`startx = (x_offset +
    tl_x)·res`, `pixels = pixels·res/xres`) and the scan's channel count
    (one channel for gray, three for color). The single-channel averages are
    spread to three identical channels before the reference file and
    `compute_coefficients()`, since the chip always consumes 12-byte records.
    With that the calibration pass sees the same defects at the same depth as
    the scan (−8 % linear, matching the raw scan through the 1.7 gamma) and
    the standard correction removes them: 1501 px −6.5 % → −0.9 %, 6910 px
    −5.6 % → −1.0 % on gray, −0.3…−1.3 % per channel on color. Two hardware
    facts made this the only workable shape: the chip does **not** deliver a
    single-channel read-out that starts at pixel 0 at the full clock (the
    bulk read times out and the USB state needs a power cycle), and in a
    single-channel session it delivers exactly `lines` lines, while
    `genesys_shading_calibration_impl()` reads one extra line and waits for
    it forever — hence the read limited to `dev->total_bytes_to_read`. The
    half- and quarter-clock groups (200/600, 75–300) keep the generic
    three-channel calibration from pixel 0: they show no such stripes (the
    defects are smaller than a pixel there) and a single-channel pass wrecks
    their left edge.
17. **Lamp-off dark pass at the full clock.** With the calibration window
    starting inside the lit area there are no covered CCD columns for
    `genesys_dark_shading_by_dummy_pixel()`, and the dark level came out as
    0: black paper scanned as 42/255. The full-clock calibration therefore
    runs the generic dark pass (`genesys_dark_shading_calibration()`, lamp
    off, motor not started, followed by the normal repark) before the white
    pass. The measured pedestal is 771/65535 (3.0/255). What remains on solid
    black toner at 1200 dpi (36/255) is light — toner reflectance plus veiling
    glare of a dusty optical path — and the model reproduces it exactly; the
    lower-clock groups read 0 on the same target because their dummy-column
    dark from the bright strip (20.3/255) is inflated by stray light and
    over-subtracts. That is a black-point difference, not a calibration error.
18. **Single white target.** Once the reference is rebased onto the measured
    dark level, all clocking groups in gray and color agree on one target
    (0xa400 → white paper at 194–199 after the 1.7 gamma). The earlier
    0x6800 / 0x7000 / 0xe000 per group were compensating the dark error.
    `OB4800_SHADING_TARGET` still overrides it for tuning.

## Pitfalls met on the way (so nobody has to hit them again)

Everything below cost real time; each item is a wrong turn that looked
right until measured.

**Shading data path**
- `genesys_shading_calibration_impl()` reads the calibration scan with
  `sanei_genesys_read_data_from_scanner()` — raw, at 16 bit, *bypassing the
  image pipeline*. On a chip that only delivers 8 bit this yields
  period-3 garbage (two RGB bytes per 16-bit word) and the shading looks
  like vertical stripes with a 3-column period. Symptom → cause mapping is
  worth remembering: period 3 = byte/word mismatch in calibration data.
- The averaged lines (`white_average_data`, `dark_average_data`) are
  **channel-interleaved** (R,G,B per pixel). `compute_planar_coefficients()`
  (used by the LiDE/5600F group) reads them as planar, so the coefficient
  of pixel x is computed from the white of pixel x/3: the correction curve
  comes out stretched 3× and the lamp dome remains. Use
  `compute_coefficients()` for a CCD with interleaved averages.
- The dark level comes from `genesys_dark_shading_by_dummy_pixel()`: the
  average of columns 5..36 of the white calibration line (the CCD area
  before the glass). Keep the black margin at the start of the line in
  mind when moving the calibration area or the frame origin — and see the
  read-out section below for what that value really contains.
- In gray mode the chip still reads **12-byte records** (three channels).
  Uploading 4-byte records produces a correct first third of the frame and
  stale memory after it (the symptom: chaos starting at width/3).
- Shading records are paged: 512 bytes per page, 42 records, 8 bytes unused.
  Writing them back to back gives 42-pixel steps with a 3-page cycle.
- The chip applies the table linearly with unity 0x2000 and no ceiling; the
  1.7 gamma is applied *after* shading, so a ×2 stripe shows as ×1.5 in
  the 8-bit output. Measure with the synthetic table
  (`OB4800_SHADING_TEST=1`: unity everywhere, ×0.5/×1.5/×2/×4/×6 stripes at
  records 500–760) before trusting any coefficient math.
- The table is indexed from the first pixel of the scan window counted
  from `params.startx` *without* `output_pixel_offset`. Verified by
  aligning a dust speck on the glass: its dark image and its bright
  correction ghost coincide only at the right offset — a cheap and exact
  alignment method.
- The calibration reading of the 300 dpi clocking is about half of the
  scan-domain value (the 600 dpi clocking reads 1:1). This does *not* call
  for different targets: with the dark level right, one target fits all
  groups. Sweep `OB4800_SHADING_TARGET` on a white sheet if it ever needs
  re-tuning.
- Mixing the reference file's white (with its own pedestal) and today's
  dark level in `target / (white − dark)` is an additive error, constant
  across the line; relative to the signal it is largest on the steep left
  slope of the lamp dome and showed as a 3–5 % bright zone at 8–25 mm in
  every mode. It varies with the AFE offsets (`OB4800_AFE_OFS_DELTA` moved
  the profile), which is how it was told apart from a shape error of the
  reference. Rebase the reference onto the current dark before dividing.

**Calibration target**
- The white strip is at 20–34 mm from home; before it is the black frame
  (a calibration at 9 mm reads ~10/255). At 29–33 mm the strip is already in
  the frame's shadow (half brightness) — 24–28 mm is the usable window.
- The strip sits above the glass plane and sees the LED lamp ripple at a
  different contrast than paper does: calibrating from it leaves ±8 %
  vertical bands on full-width scans, identical at any strip position and
  independent of table shifts. The fix is a reference in the glass plane
  (white sheet), hence the white reference file.
- Calibrating all groups with the 1200 dpi profile saturates the reading
  (exposure 11000) and produces gain 0.86 for the 300 dpi scan — each
  clocking group must calibrate with its own profile.

**Read-out mode and calibration window (1200 dpi)**
- **Calibrate in the scan's window and read-out mode.** A three-channel
  calibration pass from pixel 0 does not see narrow CCD response defects
  that the single-channel gray scan (or the color scan) sees at the full
  clock: in the averaged calibration line they are absent or three times
  wider with half the area, in every channel. The symptom is a vertical
  stripe that survives shading and gains a bright ghost next to it; the
  test is to compare the same dip in the raw scan (unity table) and in the
  calibration pass by centre, width (σ) and area — blur preserves area,
  "not seen" does not. Mind the 1.7 gamma: −4.8 % in the 8-bit output is
  −8 % linear.
- The chip does not deliver a single-channel read-out starting at pixel 0
  at the full clock: `bulk_read` times out, the USB state breaks, power
  cycle required. Starting at the scan origin (183 px) works; three
  channels work from either start. That is why the calibration window is
  the scan window rather than the full line.
- In a single-channel session the chip delivers exactly `lines` lines;
  the generic code sizes its buffer for `lines + 1` and blocks on the
  missing line. In a three-channel session the extra line does arrive,
  which is why the over-read never hurt before.
- CCD phase registers differ between the calibration pass (sensor-table
  1200 dpi block: 0x18=01, 0x52..0x57 = 08/0a/00/02/04/06) and the scan
  (base values: 0x18=13, 06/08/0a/00/02/04), for gray and color alike.
  This turned out to be irrelevant: the single-channel calibration kept the
  block's phases and still removed the stripes. Do not chase the phases —
  it is the window and the channel count.
- At the half and quarter clock a single-channel calibration pass ruins the
  left edge (−60 % at 0 mm) while those groups have no stripes to fix.
  Enable the mode-matched calibration by `shading_resolution ==
  full_resolution`, not per channel count.
- `white_average_data` is laid out from sensor pixel 0 with zeros below the
  window start, and `pixels_per_line` already includes the start. A
  reference file must be treated the same way: absolute coordinates, no
  slicing by offset (a sliced load silently shifted the reference by 945 px
  on a narrow window; the result looked "clean" only because the frame had
  clipped at 255 — check the maximum before believing a profile).
- With the calibration window inside the lit area the dummy-column dark is
  0, and a white sheet still looks perfect (mid-tone on target) — the error
  only shows on dark content (black at 42/255). Test dark handling on solid
  matte black, never on white alone; the lid or a glossy card are useless
  as black references.
- The dummy-column dark measured on the strip (20.3/255) is not the ADC
  pedestal (3.0/255 with the lamp off): the covered pixels pick up stray
  light from the bright strip above the glass. It happens to crush black to
  0 at ≤600 dpi; the full-clock path with the lamp-off dark is the honest
  one. Any black-point preference belongs in the frontend.
- `dev->calib_session` is filled inside `genesys_shading_calibration_impl()`
  (`init_regs_for_shading()` runs there, for each pass). Conditions in
  `genesys_flatbed_calibration()` that read `calib_session` see the previous
  scan — decide from `dev->settings` and the `sensor` argument (the same
  trap as `dev->session` in `set_fe()`).

**AFE**
- Registers 2–4 are the gains, 5–7 the offsets (the captured register
  order suggested the opposite). ±64 on 5–7 changes nothing visible; −16 on
  2–4 lowers white from 252 to 221. The gain code is not linear (range bit
  at 0x20): −40 was brighter than −24.
- White paper saturates the 600 and 1200 dpi clockings with the 300 dpi
  gains; a saturated raw divided by an unsaturated reference looks exactly
  like 1/reference (bright edges, dark middle) — check the raw level with
  the unity table first.
- The ADC pedestal is the same in the single- and three-channel read-out
  (3.0/255 lamp-off); the "native dark" of a three-channel reference taken
  on the glass (11.8/255) is pedestal plus stray light.

**Session state**
- `dev->session` is **not yet updated** when `set_fe()` runs during
  `init_regs_for_scan`; anything decided from `dev->session.params.xres`
  there uses the previous session (or garbage). This is why scans restored
  from the calibration cache got the 1200 dpi AFE setup and came out 4×
  darker while the shading table was byte-identical. Decide from the
  `sensor` argument (`shading_resolution`).
- Without `SHADING_REPARK` the head-position bookkeeping after the
  calibration pass shifted the frame by ~3.8 mm at 300 dpi (FEEDL differed
  between the calibrated and the cached path). Park after calibration.
- The carriage cannot move backwards. A calibration area behind the scan
  start (or `y_offset` ≤ calibration end) drives the head into the stop.
  The backend now refuses such a configuration; keep it that way. The
  lamp-off dark pass adds no travel (the motor is not started for it).

**Diagnostics that worked**
- `SANE_DEBUG_GENESYS_IMAGE=1` writes `gl_white_shading.tiff` (the full
  calibration pass, 16-bit RGB) and `gl_white_average.tiff` (one line), and
  `gl_black_*.tiff` for the dark pass; the 2-D pass shows whether a feature
  is real (same in all rows) or noise. The files go to the *current*
  directory — easy to analyse a stale dump from another folder.
- Register-write diff between two runs (grep `write_register`,
  `write_fe_register`, `write_ahb` from the last `init_regs_for_scan` to
  `begin_scan`) found the cache bug in one look after several hours of
  reasoning about the table. The same diff between `init_regs_for_shading`
  and `init_regs_for_scan` (0x04, 0x18, 0x52–0x5a, 0x70–0x73) showed how
  the calibration pass differs from the scan.
- Profile measurement on a white sheet: median of 50–150 blank rows, column
  profile printed every 4–16 mm, min/max/spread. Every change above was
  accepted or rejected on those numbers, not on how the image looked.
- A single logging line with the values that went into one shading record
  (white, dark, target, coeff, resulting dark/gain — `patch_dbg_cache.py`
  in the package) separates "wrong table" from "wrong chip state"
  immediately; printing the first records (x = 0..7, 20, 40, 100 …) showed
  `white − dark < 0` at the line start.
- The synthetic table's stripes (records 500–760) double as an index
  marker: where they land in the frame is where record 500 is applied
  (502 px at both 600 and 1200 dpi).
- Three different shifts tell paper, glass and frame apart: rotate the sheet
  (paper), shift the window with `-l` (frame — the sheet does *not* move, so
  this does not separate glass from paper), slide the sheet sideways (glass).
- A per-row `argmin` over a 200-px window on a line with 3–5 % pixel noise
  "jitters" with σ ≈ 200/√12 = 58 px — that is the window's statistics, not
  a moving shadow. Check for a uniform distribution before concluding that a
  defect is non-stationary.

## Known limits

- The white reference files are per unit; without them the strip under the
  frame is used and full-width scans show ±8 % vertical banding. The
  full-clock files (`-1200.dat` for color, `-1200-gray.dat` for gray) must
  be captured in the corresponding mode; the loader ignores a file that
  does not cover the current window. The reference sheet must cover the
  whole sensor line (an A4 sheet in landscape orientation): a portrait A4
  leaves the last ~3 mm without a reference and paper there saturates.
- The frame ends at the CCD line (212.7 mm); the glass is wider, but there
  is no sensor under the remaining ~6 mm.
- Solid black reads ~36/255 at 1200 dpi (honest: toner reflectance plus
  glare) and 0 at ≤600 dpi (over-subtracted dummy-column dark). Both are
  usable; equalising them is a black-point choice for the frontend, not a
  calibration fix.
- Environment variables `OB4800_*` (see `gl846.cpp` / `genesys.cpp`):
  `OB4800_CALIB_Y_MM` and `OB4800_WHITE_REF_SAVE` are the one-off white
  reference capture; `OB4800_CALIB_3CH`, `OB4800_NO_DARK_PASS`,
  `OB4800_WREF_NODARK` switch the 1200 dpi calibration back to the generic
  behaviour for A/B comparison; `OB4800_SHADING_TARGET`,
  `OB4800_SHADING_TEST`, `OB4800_SHADING_SHIFT`, `OB4800_AFE_GAIN_DELTA`,
  `OB4800_AFE_OFS_DELTA` are debugging aids. All of them can be removed or
  turned into backend options.

## Files touched

`enums.h`, `genesys.cpp`, `gl846.cpp`, `low.cpp`, `image_pipeline.h`,
`image_pipeline.cpp` (two new nodes), `tables_frontend.cpp`,
`tables_gpo.cpp`, `tables_memory_layout.cpp`, `tables_model.cpp`,
`tables_motor.cpp`, `tables_sensor.cpp`, `backend/genesys.conf.in`,
`doc/descriptions/genesys.desc` — see the attached patch
(`opticbook4800-genesys-v5.patch`, applies cleanly to the 1.2.1 tag).
