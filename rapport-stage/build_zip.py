"""Construit l'archive ZIP du rapport avec des separateurs '/' (compatibles
Overleaf, Linux, macOS), en excluant les fichiers auxiliaires LaTeX."""
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path.home() / "Downloads" / "rapport-stage.zip"
SKIP_SUFFIX = {".aux", ".log", ".toc", ".lof", ".lot", ".out", ".lol",
               ".gz", ".fls", ".fdb_latexmk", ".synctex"}
BACKSLASH = chr(92)

if OUT.exists():
    OUT.unlink()

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.suffix in SKIP_SUFFIX or p.name == "build_zip.py":
            continue
        arc = p.relative_to(ROOT).as_posix()      # separateurs '/' garantis
        z.write(p, arc)
        print(f"  + {arc}")

print()
with zipfile.ZipFile(OUT) as z:
    names = z.namelist()
    bad = [n for n in names if BACKSLASH in n]
    print(f"Archive     : {OUT}")
    print(f"Taille      : {OUT.stat().st_size / 1024:.0f} Ko")
    print(f"Entrees     : {len(names)}")
    print(f"Antislash   : {len(bad)} (doit etre 0)")
    print(f"Integrite   : {z.testzip() or 'OK'}")
    print(f"main.tex    : {'present' if 'main.tex' in names else 'ABSENT'}")
