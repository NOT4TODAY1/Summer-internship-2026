# ============================================================
#  Compilation du rapport de stage
# ============================================================
#  make          -> compile le PDF (2 passes)
#  make quick    -> une seule passe (apercu rapide)
#  make clean    -> supprime les fichiers auxiliaires
#  make cleanall -> supprime aussi le PDF
# ============================================================

MAIN    = main
LATEX   = pdflatex
FLAGS   = -interaction=nonstopmode -halt-on-error -file-line-error

.PHONY: all quick clean cleanall view

all:
	$(LATEX) $(FLAGS) $(MAIN).tex
	$(LATEX) $(FLAGS) $(MAIN).tex
	@echo ""
	@echo "=== $(MAIN).pdf genere ==="

quick:
	$(LATEX) $(FLAGS) $(MAIN).tex

# Variante avec latexmk si disponible (gere les passes automatiquement)
latexmk:
	latexmk -pdf -interaction=nonstopmode $(MAIN).tex

clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot *.lol *.fls *.fdb_latexmk \
	      *.synctex.gz *.bbl *.blg *.idx *.ilg *.ind

cleanall: clean
	rm -f $(MAIN).pdf

view: all
	@echo "Ouvrez $(MAIN).pdf"
