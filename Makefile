INSTALLDIR = test_install

toinstall = webservice.py \
	static/snana_summary.css static/snana_summary.js static/snana_summary_start.js static/rkwebutil.js \
	templates/base.html templates/snana-summary-root.html

default :
	@echo Do "make install INSTALLDIR=<dir>"
	@echo Dev : make install INSTALLDIR=/global/cfs/cdirs/m4385/survey_strategy_optimization/code/snana-summary-dev-webserver
	@echo Production : make install INSTALLDIR=/global/cfs/cdirs/m4385/survey_strategy_optimization/code/snana-summary-webserver

install : $(patsubst %, $(INSTALLDIR)/%, $(toinstall))

$(INSTALLDIR)/% : %
	install -Dcp $< $@

static/rkwebutil.js : rkwebutil/rkwebutil.js
	ln -s ../rkwebutil/rkwebutil.js static/rkwebutil.js

