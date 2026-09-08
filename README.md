# Plustek OpticBook 4800 on Linux

Full support for the Plustek OpticBook 4800 book-edge scanner (USB
`07b3:1301`, Genesys Logic GL845, CCD) in the SANE `genesys` backend.
Before this the scanner was not supported on Linux at all.

Gray and color, 75/100/150/200/300/600/1200 dpi, full A4, with shading
calibration: white paper comes out at 195–199/255 with no vertical banding
at any resolution, color balance on white 197/197/199, geometry within
0.2 mm across the three CCD clockings of the sensor. Works from
`scanimage`, `simple-scan`, `xsane`, `gscan2pdf` and anything else built on
SANE.

The patch has been submitted upstream: [sane-project/backends!1009](https://gitlab.com/sane-project/backends/-/merge_requests/1009)

## What is here

| Path | Contents |
|---|---|
| `opticbook4800-genesys-v5.patch` | the patch itself, applies to the sane-backends master branch |
| `ob4800-conf-desc.patch` | entries for `genesys.conf.in` and `genesys.desc` |
| `make_patch_v5.sh` | rebuilds the patch from a working tree and verifies it on a clean clone |
| `docs/УСТАНОВКА-OpticBook-4800.md` | installation guide, in Russian: build, install, one-off white reference capture, troubleshooting |
| `docs/TECHNICAL-NOTES.md` | technical description for the SANE maintainers, in English: what the GL845 needed and why, plus the pitfalls met on the way |
| `docs/НАХОДКИ-GL845.md` | the same findings in Russian, as a digest for anyone continuing the work |
| `tools/` | measuring scripts, USB dump tools and a standalone Python driver used during reverse engineering |
| `patches-history/` | every code change of the project as a separate scripted step, in order, each with a header explaining what it does and why |

## Installation

See `docs/УСТАНОВКА-OpticBook-4800.md`. In short: clone sane-backends 1.2.1,
apply the patch, build the `genesys` backend, install, add the USB id to
`genesys.conf`, and capture the white reference once from a sheet of white
paper on the glass.

The white reference is per unit — it compensates the ripple of this
particular LED lamp — and is optional: without it the calibration strip
under the frame is used, at the cost of slight vertical banding.

## Why the scanner needed this much work

The GL845 differs from its documented siblings in ways that are invisible
until measured on hardware: it delivers 8-bit data where the backend expects
16, the shading table is paged with 12-byte records, each of the three CCD
clockings starts the frame at a different place, the AFE register roles are
swapped compared to the capture order, and the calibration strip sees the
lamp at a different contrast than a document on the glass does. Everything
in this repository was established by measurement, not by guessing: the
technical notes and the findings digest list each pitfall together with the
symptom it produces, so that the next person does not have to rediscover
them.

## Status and limits

- Solid black reads ~36/255 at 1200 dpi and 0 at ≤600 dpi — a black-point
  difference between the two dark sources, usable as is.
- The frame ends at the CCD line (212.7 mm); the glass is wider, but there
  is no sensor under the remaining ~6 mm.
- The `OB4800_*` environment variables are calibration and debugging aids;
  they are documented in the installation guide.

## License

The patch follows the license of sane-backends (GPL-2.0-or-later with the
SANE exception). The tools and documents in this repository are published
under the same terms.
