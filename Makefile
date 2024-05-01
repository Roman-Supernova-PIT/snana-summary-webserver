INSTALLDIR = test_install

toinstall = webservice.py \
	static/snana_summary.css static/snana_summary.js static/snana_summary_start.js static/rkwebutil.js \
	static/svgplot.css static/svgplot.js \
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

static/svgplot.css : rkwebutil/svgplot.css
	ln -s ../rkwebutil/svgplot.css static/svgplot.css

static/svgplot.js : rkwebutil/svgplot.js
	ln -s ../rkwebutil/svgplot.js static/svgplot.js
