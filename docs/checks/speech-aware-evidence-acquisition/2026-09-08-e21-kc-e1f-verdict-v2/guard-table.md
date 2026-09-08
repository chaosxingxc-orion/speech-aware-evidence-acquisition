# KC-E1f v2 — the guard table under measured margins

**ADMITTED**

| guard | v1 bound | v1 | **v2 margin** | v2 bound vs margin | **v2** |
|---|---|---|---:|---|---|
| delivery integrity (construction) | for every window the delivered raw text equals the sealed predecessor outside the accepted substitution spans and carries the identical whitespace-token count -- it ABORTS THE READ rather than producing a number | PASS | -- | -- | **PASS** |
| corpus WER non-inferiority | -0.02936 pp (upper bound) | PASS | 0.05793 | -0.02936 <= +0.05793 | **PASS** |
| numeric-value accuracy not worse (call-pooled) | -0.02122 pp (lower bound) | FAIL | 0.15651 | -0.02122 >= -0.15651 | **PASS** |
| over-generation not worse | +0.00255 pp (upper bound) | FAIL | 0.02218 | +0.00255 <= +0.02218 | **PASS** |
| negation-critical rate not worse | advisory point estimate only; gates nothing | ADVISORY | -- | -- | **ADVISORY** |
