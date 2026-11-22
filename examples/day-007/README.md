# Day-007 example configs (22 Nov 2026)

Riemann hypothesis / Claude Shorts. Copy a file onto `template/short-alert/alert.json`, generate the matching official seal, then build.

| Config | Centre emblem | Commons file | `make_seal.py` notes |
| --- | --- | --- | --- |
| `short-01.alert.json` | University of Göttingen seal | `File:Uni Göttingen Siegel.svg` (PD) | `--bg white` (black line-art vanishes on a dark map) |
| `short-02.alert.json` | Clay Mathematics Institute logo | `File:Clay Mathematics Institute CMI Logo.svg` (PD) | Restack knot + CMI + wordmark, then `--layout fit --bg white` |
| `short-03.alert.json` | Great Seal of the United States, obverse | U.S. Government, PD | Full-colour official artwork, default plate |

Audio in these configs is the standing quieter-SFX + `bed_hvitserk.wav` cue (`bed_start` 0 on the 16 s fetch). The wav is not in the repo.
