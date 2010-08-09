
bin_SCRIPTS = prcs2hg
CLEANFILES = $(bin_SCRIPTS)
EXTRA_DIST = prcs2hg.pl

prcs2hg: prcs2hg.pl $(top_builddir)/config.status
	$(SHELL) ./config.status --file=$@:prcs2hg.pl
	chmod a+x $@
