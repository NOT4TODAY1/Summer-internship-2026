# Rapport de stage — Système RAG (LaTeX)

Rapport de stage rédigé en français, structuré selon le modèle du rapport
`Summer_Internship_2025.pdf` (classe `report`, méthodologie CRISP-DM, 6 chapitres).

---

## Compilation

### Option A — Overleaf (le plus simple, rien à installer)

1. Aller sur [overleaf.com](https://www.overleaf.com) → **New Project** → **Upload Project**
2. Déposer le fichier **`rapport-stage.zip`** directement (ne pas le décompresser)
3. Dans le menu **Menu → Compiler**, vérifier que le compilateur est **pdfLaTeX**
4. S'assurer que le document principal est **`main.tex`**
5. Cliquer sur **Recompile**

### Option B — Localement

Il faut une distribution LaTeX installée (MiKTeX sur Windows, TeX Live sur Linux/macOS).

```bash
# deux passes sont nécessaires pour la table des matières et les références croisées
pdflatex main.tex
pdflatex main.tex
```

Ou, avec `make` :

```bash
make          # compile (2 passes)
make clean    # nettoie les fichiers auxiliaires
```

Ou, avec `latexmk` (gère les passes automatiquement) :

```bash
latexmk -pdf main.tex
```

**Installer MiKTeX sur Windows :** <https://miktex.org/download>
Au premier passage, MiKTeX proposera d'installer automatiquement les paquets
manquants — accepter.

---

## Avant de rendre : 3 choses à faire

### 1. Vérifier l'identité en tête de `main.tex`

Les informations de la page de garde sont centralisées en haut de `main.tex` :

```latex
\newcommand{\authorname}{TLILI Mohamed Aziz}
\newcommand{\supervisor}{Mme ENNINE Hanene}
\newcommand{\organism}{ESPRIT-Tech}
\newcommand{\academicyear}{2025 / 2026}
```

Ces valeurs sont **pré-remplies d'après le rapport 2025** — les corriger si
l'encadrante ou l'organisme d'accueil ont changé pour 2026.

### 2. Compléter les valeurs marquées en orange

Les emplacements laissés à compléter apparaissent **en orange** dans le PDF
(commande `\aremplir{}`). Ils concernent tous le chapitre 5 :

| Où | Quoi |
|---|---|
| Tableau 5.4 (`ch5-evaluation.tex`) | les 4 scores RAGAS, après exécution de `make eval` |
| Tableau 5.6 (`ch5-evaluation.tex`) | l'état des leviers restants |

Pour obtenir les scores RAGAS :

```bash
# depuis la racine du projet RAG, pas depuis ce dossier
pip install ragas datasets
# remplir data/eval/testset.csv avec ~20 questions + réponses de référence
python -m src.evaluation.ragas_eval --testset data/eval/testset.csv
# les scores sont écrits dans docs/ragas_report.json
```

Chercher toutes les occurrences à compléter :

```bash
grep -rn "aremplir" chapters/
```

### 3. Relire le chapitre 1

Les sections 1.2 et 1.3 (présentation de l'organisme d'accueil) reprennent la
description d'ESPRIT-Tech du rapport 2025. Les adapter si nécessaire.

---

## Structure du projet

```
rapport-stage/
├── main.tex                    ← document principal (identité en haut)
├── preamble.tex                ← packages, styles, couleurs, commandes
├── frontmatter/
│   ├── titlepage.tex           ← page de garde
│   ├── dedicaces.tex
│   └── remerciements.tex
├── chapters/
│   ├── introduction.tex        ← Introduction Générale
│   ├── ch1-contexte.tex        ← Contexte général + CRISP-DM
│   ├── ch2-metier.tex          ← Compréhension métier + étude de l'existant
│   ├── ch3-donnees.tex         ← Corpus, statistiques, préparation
│   ├── ch4-modelisation.tex    ← Architecture RAG
│   ├── ch5-evaluation.tex      ← Évaluation, RAGAS, expérience FR/EN
│   ├── ch6-deploiement.tex     ← API, UI, Docker
│   └── conclusion.tex          ← Conclusion Générale + perspectives
├── bibliographie.tex           ← 24 références
├── images/
│   ├── ui-accueil.png          ← capture de l'interface
│   └── ui-reponse.png          ← capture d'une réponse sourcée
├── Makefile
└── README.md
```

Les deux figures d'architecture (CRISP-DM au chapitre 1, pipeline RAG au
chapitre 4, déploiement au chapitre 6) sont dessinées en **TikZ** — elles sont
donc vectorielles et éditables directement dans le `.tex`, sans fichier image
externe.

---

## Chiffres du rapport

Toutes les valeurs numériques du rapport ont été **mesurées sur le projet réel**,
pas estimées :

| Donnée | Valeur | Source |
|---|---|---|
| Fichiers du corpus | 2 676 PDF | comptage `data/raw/` |
| Segments indexés | 2 929 | `count(*)` sur `chroma.sqlite3` |
| Volume textuel | 1 332 652 caractères | extraction pypdf sur les 2 676 fichiers |
| Longueur moyenne / document | 498 caractères | idem |
| Échecs d'extraction | 0 | idem |
| Latence de recherche | 182 ms (moyenne, 7 requêtes) | mesure `time.perf_counter()` |
| Score moyen questions FR | 0,153 | expérience contrôlée, 5 paires FR/EN |
| Score moyen questions EN | 0,461 | idem |
| Latence de génération | ~110 s (CPU) | relevé dans l'interface |

Le **tableau 5.2** (expérience contrôlée sur la langue de la question) est le
résultat expérimental central du rapport : il montre qu'à contenu identique, une
question en anglais obtient un score de pertinence **3 fois supérieur** à la même
question en français, ce qui diagnostique le choix du modèle d'embeddings comme
cause de la faiblesse des scores.

---

## Notes de rédaction

- Les scores RAGAS **n'ont volontairement pas été inventés**. Le rapport indique
  explicitement que la campagne de mesure reste à conduire, et pourquoi. Présenter
  des métriques non mesurées comme mesurées serait une faute méthodologique.
- Les limites du travail sont énoncées dans le corps du rapport (corpus
  transactionnel, paramètre de découpage inopérant, latence, dépendances non
  figées). Un jury valorise davantage une limite identifiée et analysée qu'une
  limite passée sous silence.
