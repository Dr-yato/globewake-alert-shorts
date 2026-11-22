# NASA Blue Marble rasters

Do not commit the images. They are public domain, but each file is tens of megabytes.

Place these two files in `tools/raster/bluemarble/` (or point `GW_BM_DIR` at a directory that already has them):

- `bm24000.jpg` — NASA Blue Marble “Whole world - land and oceans” (equirectangular land/ocean mosaic)
- `bm_clouds8192.jpg` — matching cloud layer, used when `bake_bluemarble.py` is given a cloud mix > 0

Fetch them:

```bash
python3 scripts/fetch_bluemarble.py
# or, if you already have a copy on this machine:
export GW_BM_DIR=/workspace/news-channel/tools/raster/bluemarble
```

Then bake a greyscale intel-tone texture into the project:

```bash
python3 template/short-alert/scripts/bake_bluemarble.py template/short-alert 0
```
