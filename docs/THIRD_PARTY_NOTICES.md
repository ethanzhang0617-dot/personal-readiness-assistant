# Third-party notices

## MuscleMap — body visualisation (MIT)

The Train screen's muscle visualisation uses **MuscleMap** by Jsplice.

- Project: <https://github.com/Jsplice/MuscleMap>
- Packages: `@musclemap/react@1.1.0`, `@musclemap/core@1.1.0`, `@musclemap/assets@1.1.0`
- License: MIT (code, traced muscle path data and the bundled reference body photographs)
- Asset provenance: <https://github.com/Jsplice/MuscleMap/blob/main/ASSET_PROVENANCE.md>

We use the library's **photoreal hybrid** mode: the traced muscle surfaces render
as SVG paths over a realistic body photograph, with only the muscles trained by
today's recommendation highlighted.

### Derived assets

`frontend/public/musclemap/male-front-{light,dark}.webp` and
`male-back-{light,dark}.webp` are **derived** from the MIT-licensed reference
photographs bundled in `@musclemap/assets` (`bodies/male-front.webp`,
`bodies/male-back.webp`). They were converted to a desaturated, theme-tuned
grayscale so the body reads as a restrained sports-tech figure rather than a
coloured anatomy chart, per the product's visual direction. The derived files
remain under the MIT terms below.

Only the male body is used; the female reference photographs are shipped by the
package but not consumed by this product.

### Upstream license text

```
MIT License

Copyright (c) 2026 Jsplice / MuscleMap contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Where it appears

- `frontend/components/muscle-focus-map.tsx` — the display adapter that maps the
  product's training-focus vocabulary onto MuscleMap muscle groups and renders
  the front/back figures.
- `frontend/features/train/train-view.tsx` — where the visualisation is shown on
  the pre-session screen.

The visualisation is presentation only: it consumes the recommendation the
deterministic engines already produced and never decides what is trained.
