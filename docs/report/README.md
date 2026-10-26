# Technical Report

`technical-report.tex` retains the technical content, architecture diagram,
evaluation discussion, historical measurements, and references from the final
July 2026 project report. The portfolio adaptation removes task allocations,
student numbers, signatures, and the academic submission declaration.

Build with Tectonic:

```bash
tectonic technical-report.tex
```

Alternatively, run `pdflatex technical-report.tex` twice with a TeX distribution
that includes TikZ, German babel support, and the packages named in the source.
The generated PDF is technical documentation, not a replacement for the
original signed university submission.

Its measurements describe the original implementation. For current installation,
test results, and portfolio fixes, use the repository README and
`docs/benchmarking.md`.
