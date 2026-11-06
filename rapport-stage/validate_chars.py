"""Controles complementaires : equilibre du mode mathematique et
caracteres speciaux non echappes hors verbatim."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
VERB = re.compile(r"\\begin\{(lstlisting|verbatim)\}.*?\\end\{\1\}", re.DOTALL)

DOLLAR = "$"
HASH = "#"
UNDER = "_"


def strip_comments(t):
    out = []
    for line in t.split("\n"):
        idx, esc = None, False
        for i, ch in enumerate(line):
            if ch == "\\":
                esc = not esc
            elif ch == "%" and not esc:
                idx = i
                break
            else:
                esc = False
        out.append(line if idx is None else line[:idx])
    return "\n".join(out)


errs = []
for f in sorted(ROOT.rglob("*.tex")):
    body = VERB.sub("", strip_comments(f.read_text(encoding="utf-8")))

    # equilibre des $ (en retirant d'abord les sequences echappees \X)
    tmp = re.sub(r"\\.", "", body, flags=re.DOTALL)
    n = tmp.count(DOLLAR)
    if n % 2:
        errs.append(f"{f.name}: nombre impair de {DOLLAR} ({n}) -> math non ferme")

    for ln, line in enumerate(body.split("\n"), 1):
        l = re.sub(r"\\[a-zA-Z@]+\*?", "", line)      # commandes
        l = re.sub(r"\\.", "", l)                     # echappements
        l = re.sub(re.escape(DOLLAR) + "[^" + re.escape(DOLLAR) + "]*"
                   + re.escape(DOLLAR), "", l)        # math inline
        for ch, name in ((UNDER, "underscore"), (HASH, "diese")):
            if ch in l:
                errs.append(f"{f.name}:{ln}: {name} non echappe -> "
                            f"{line.strip()[:70]}")

print("=" * 62)
if errs:
    print(f"  {len(errs)} probleme(s) :")
    for e in errs:
        print("   [X]", e)
else:
    print(f"  {DOLLAR} equilibres ; aucun {UNDER} ou {HASH} non echappe "
          f"hors verbatim.")
print("=" * 62)
sys.exit(1 if errs else 0)
