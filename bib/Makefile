.PHONY: all check format clean cleanall test

all: all_bib_doc.pdf

all_bib_doc.pdf: all_bib_doc.tex all.bib IEEEtran.bst
	latexmk -pdf all_bib_doc.tex

check:
	./check_library.py

format:
	./format_library.sh
	./check_library.py

test:
	python3 -m unittest discover -s tests

clean:
	latexmk -c all_bib_doc.tex
	$(RM) all_bib_doc.bbl

cleanall:
	latexmk -C all_bib_doc.tex
	$(RM) all_bib_doc.bbl
