"""Validation syntaxique d'un projet LaTeX sans compilateur.

Verifie : accolades equilibrees, environnements apparies, fichiers \\input
existants, images referencees presentes, coherence \\label / \\ref,
et commandes personnalisees non definies.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
errors, warnings = [], []


def strip_comments(text: str) -> str:
    out = []
    for line in text.split("\n"):
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


VERBATIM = re.compile(
    r"\\begin\{(lstlisting|verbatim)\}.*?\\end\{\1\}", re.DOTALL
)


def tex_files():
    return sorted(p for p in ROOT.rglob("*.tex"))


# ---------------------------------------------------------------- 1. accolades
for f in tex_files():
    raw = strip_comments(f.read_text(encoding="utf-8"))
    body = VERBATIM.sub("", raw)          # le verbatim peut contenir { }
    depth, line_no, i = 0, 1, 0
    # On marche caractere par caractere : un '\' echappe le caractere suivant.
    # Cela traite correctement \\ (saut de ligne), \{ et \} sans confondre
    # le '{' de "\\{\scriptsize ...}" avec une accolade echappee.
    while i < len(body):
        ch = body[i]
        if ch == "\\":
            if i + 1 < len(body) and body[i + 1] == "\n":
                line_no += 1
            i += 2
            continue
        if ch == "\n":
            line_no += 1
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                errors.append(f"{f.name}: '}}' en trop vers la ligne {line_no}")
                depth = 0
        i += 1
    if depth != 0:
        errors.append(f"{f.name}: {depth} accolade(s) '{{' non fermee(s)")

# ------------------------------------------------------- 2. environnements
for f in tex_files():
    body = strip_comments(f.read_text(encoding="utf-8"))
    stack = []
    for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", body):
        kind, env = m.group(1), m.group(2)
        line = body[: m.start()].count("\n") + 1
        if kind == "begin":
            stack.append((env, line))
        else:
            if not stack:
                errors.append(f"{f.name}:{line}: \\end{{{env}}} sans \\begin")
            elif stack[-1][0] != env:
                errors.append(
                    f"{f.name}:{line}: \\end{{{env}}} ferme "
                    f"\\begin{{{stack[-1][0]}}} (ligne {stack[-1][1]})"
                )
                stack.pop()
            else:
                stack.pop()
    for env, line in stack:
        errors.append(f"{f.name}:{line}: \\begin{{{env}}} jamais ferme")

# ------------------------------------------------------------ 3. \input
for f in tex_files():
    body = strip_comments(f.read_text(encoding="utf-8"))
    for m in re.finditer(r"\\(?:input|include)\{([^}]+)\}", body):
        target = m.group(1)
        cands = [ROOT / target, ROOT / (target + ".tex")]
        if not any(c.exists() for c in cands):
            errors.append(f"{f.name}: \\input{{{target}}} -> fichier introuvable")

# ----------------------------------------------------------- 4. images
for f in tex_files():
    body = strip_comments(f.read_text(encoding="utf-8"))
    for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body):
        name = m.group(1)
        found = (ROOT / "images" / name).exists() or (ROOT / name).exists()
        if not found:
            for ext in (".png", ".jpg", ".jpeg", ".pdf"):
                if (ROOT / "images" / (name + ext)).exists():
                    found = True
                    break
        if not found:
            errors.append(f"{f.name}: image introuvable -> {name}")

# ------------------------------------------------------ 5. \label / \ref
labels, refs = {}, []
for f in tex_files():
    body = strip_comments(f.read_text(encoding="utf-8"))
    for m in re.finditer(r"\\label\{([^}]+)\}", body):
        key = m.group(1)
        if key in labels:
            errors.append(f"label duplique '{key}' ({labels[key]} et {f.name})")
        labels[key] = f.name
    # listings : \begin{lstlisting}[...,label={lst:x}] declare aussi un label
    for m in re.finditer(r"\\begin\{lstlisting\}\[(.*?)\]", body, re.DOTALL):
        for lm in re.finditer(r"label=\{?([A-Za-z0-9:._-]+)\}?", m.group(1)):
            key = lm.group(1)
            if key in labels:
                errors.append(f"label duplique '{key}' ({labels[key]} et {f.name})")
            labels[key] = f.name
    for m in re.finditer(r"\\(?:ref|autoref|pageref|eqref)\{([^}]+)\}", body):
        refs.append((m.group(1), f.name))

for key, fname in refs:
    if key not in labels:
        errors.append(f"{fname}: \\ref{{{key}}} sans \\label correspondant")

unused = set(labels) - {k for k, _ in refs}
for key in sorted(unused):
    warnings.append(f"label jamais reference : '{key}' ({labels[key]})")

# --------------------------------------------- 6. commandes personnalisees
defined = set()
for f in tex_files():
    body = strip_comments(f.read_text(encoding="utf-8"))
    for m in re.finditer(r"\\(?:newcommand|renewcommand|providecommand)\*?"
                         r"\{?\\([A-Za-z]+)\}?", body):
        defined.add(m.group(1))
    for m in re.finditer(r"\\newmdenv\[[^\]]*\]\{([A-Za-z]+)\}", body):
        defined.add("ENV:" + m.group(1))

CUSTOM = {"eng", "aremplir", "reporttitle", "reportsubtitle", "authorname",
          "supervisor", "organism", "academicyear", "speciality",
          "internshipduration"}
for f in tex_files():
    body = VERBATIM.sub("", strip_comments(f.read_text(encoding="utf-8")))
    for name in CUSTOM:
        if re.search(r"\\" + name + r"\b", body) and name not in defined:
            errors.append(f"{f.name}: \\{name} utilise mais non defini")

used_envs = set()
for f in tex_files():
    body = strip_comments(f.read_text(encoding="utf-8"))
    used_envs |= set(re.findall(r"\\begin\{([A-Za-z]+)\}", body))
if "encadre" in used_envs and "ENV:encadre" not in defined:
    errors.append("environnement 'encadre' utilise mais non defini")

# --------------------------------------------------------------- rapport
print("=" * 64)
print(f"  Fichiers .tex analyses : {len(tex_files())}")
print(f"  Labels : {len(labels)}    References : {len(refs)}")
print("=" * 64)

if errors:
    print(f"\n  {len(errors)} ERREUR(S) :\n")
    for e in errors:
        print(f"   [X] {e}")
else:
    print("\n  Aucune erreur de syntaxe detectee.")

if warnings:
    print(f"\n  {len(warnings)} avertissement(s) (non bloquant) :\n")
    for w in warnings:
        print(f"   [!] {w}")

print()
sys.exit(1 if errors else 0)
