# Keep comments and preserve the macro groups from all.bib.
pass.comments         = on
sort                  = on
sort.format           = "%s($key)"
sort.macros           = off
sort.cased            = on
preserve.key.case     = on
expand.macros         = off
check.double          = on

# Match the repository layout.
print.indent          = 2
print.align           = 18
print.align.key       = 0
print.align.string    = 18
print.line.length     = 80
print.use.tab         = off
print.braces          = on
print.comma.at.end    = on
print.equal.right     = on
print.wide.equal      = off
print.newline         = 1

# Normalize delimiters, page ranges, and numeric values.
rewrite.rule { "^\"\([^#]*\)\"$" = "{\1}" }
rewrite.rule { "# \"\([^#]*\)\"$" = "# {\1}" }
rewrite.rule { "^\"\([^#]*\)\" #" = "{\1} #" }
rewrite.rule { "# \"\([^#]*\)\" #" = "# {\1} #" }
rewrite.rule { pages # "\([0-9]+\) *\(-\|---\) *\([0-9]+\)" = "\1--\3" }
rewrite.rule { "^[\"{] *\([0-9]+\) *[\"}]$" = "\1" }

# Put the standard fields first and retain the order of additional fields.
sort.order { article = author # title # journal # year # volume # number # pages # month # note }
sort.order { inproceedings = author # title # editor # booktitle # year # series # volume # pages # address # month # organization # publisher # note }
sort.order { book = author # editor # title # publisher # year # volume # series # address # edition # month # note }
sort.order { incollection = author # title # editor # booktitle # year # chapter # series # volume # pages # address # month # organization # publisher # note }
sort.order { misc = author # title # howpublished # year # month # note }
sort.order { techreport = author # title # institution # year # type # number # address # month # note }
sort.order { phdthesis = author # title # school # year # type # address # month # note }
sort.order { mastersthesis = author # title # school # year # type # address # month # note }
sort.order { proceedings = title # editor # year # series # volume # address # month # organization # publisher # note }
sort.order { manual = title # author # organization # address # edition # year # month # note }
sort.order { unpublished = author # title # year # month # note }
