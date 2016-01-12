# mendeley2biblatex
Converter from Mendeley to Biblatex format. Based on Mendely to BibTex converter by Francois Bianco.

Usage:
copy Mendeleypath\yourusername@domain"@www.mendeley.com.sqlite" mendeley.sqlite
mendeley2bibtex.py -f Dissertation -o bibliography\\mend.bib mendeley.sqlite

Creates a mend.bib based on the mendeley sqlite file.