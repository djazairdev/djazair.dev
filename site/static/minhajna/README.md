# Minhajna artwork and release screenshots

These files have their own licences, not the site's MIT / CC BY 4.0 licences.

## Logo

`minhajna-icon.svg` and `minhajna-wordmark-chalk.svg` are unmodified copies of
the [Minhajna contributors' original artwork](https://github.com/djazairdev/minhajna/tree/31516111702d2c9347b0cc85f464262ba50660fd/docs/design/system/logo).
Copyright 2026 The Minhajna contributors. SPDX-License-Identifier: CC-BY-SA-4.0.
See [the licence](https://creativecommons.org/licenses/by-sa/4.0/) and
[trademark policy](https://github.com/djazairdev/minhajna/blob/main/TRADEMARKS.md).
The outlined Arabic wordmark and original icon keep their right-to-left lockup
in both page languages, rather than substituting a different typeface.

## Screenshots

`today-0.1.0.png`, `week-0.1.0.png` and `roll-0.1.0.png` are unedited Android
screen captures taken on 19 October 2026 from the published, signed
[0.1.0 installer](https://github.com/djazairdev/minhajna/releases/tag/app-v0.1.0),
source commit `31516111702d2c9347b0cc85f464262ba50660fd`.
They are not design mockups, a component gallery or a development build.

- APK SHA-256: `334f2b0b991f9d25b13438a1b6b2ba119e0f90f34056c6bbb06c3ddb413036ba`.
- Signing certificate SHA-256: `de2a5a7839bb88733456078bb937179f43ff99004d2408cb965093aa0aed6a5b`.
- Separate Android 15 AOSP emulator, fresh temporary app storage, 720×1600,
  density 280 for Today and Roll call, 240 for the full weekly grid,
  font scale 1.0, Arabic interface.
- Built-in demo class only: 45 invented pupils. The school and timetable are
  fictional. No real teacher or pupil data was used.
- The emulator's demonstration date is 21 September 2026, the first school day,
  to show Today without accumulated reminders. It is not the release date.
- `week` shows timetable entry during setup. `roll` shows a fictional absence
  and late arrival. The app itself is unchanged.
- `*-thumb.jpg` are proportional 270×600 JPEG previews made from the PNGs;
  only resizing and compression were applied. The original capture opens on tap.

Copyright 2026 The Minhajna contributors. Screenshot composition and original
artwork are shared under CC-BY-SA-4.0. The app interface remains under
AGPL-3.0-or-later; these images do not relicense it. App source and notices:
https://github.com/djazairdev/minhajna/tree/31516111702d2c9347b0cc85f464262ba50660fd

## Sharing cards

`share-en.png` and `share-ar.png` are 1200×630 cards composed from the original,
unmodified logo and the page's reviewed title, introduction label and free-download
label. They were drawn locally with the existing HTML/CSS sharing tool and
self-hosted Tajawal fonts (SIL OFL 1.1); no AI-generated art is used.
Regenerate with `python3 site/tools/share.py --minhajna` after reviewing copy changes.
Copyright 2026 The Minhajna contributors and djazairdev contributors.
SPDX-License-Identifier: CC-BY-SA-4.0. This composition keeps the imported artwork's
share-alike licence and trademark notice above.

All files are self-hosted, with content-hashed URLs. Full-size screenshots load only
when a visitor follows their links. No embedded viewer, remote fonts or scripts
are added. Re-capture and review all images when the pinned app release changes.
