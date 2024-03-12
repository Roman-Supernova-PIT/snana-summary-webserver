import pathlib
import logging

import flask


from lib.parse_snana import RomanSurveySummary

workdir = pathlib.Path( __name__ ).resolve().parent

app = flask.Flask( __name__, instance_relative_config=True )
app.logger.setLevel( logging.INFO )

def pandas_to_dict( df ):
    if df.index.nlevels == 1:
        return df.to_dict()
    dfdict = {}
    for level in df.index.levels[0]:
        dfdict[level] = pandas_to_dict( df.xs( level, level=0 ) )
    return dfdict

@app.route( "/" )
def mainpage():
    return flask.render_template( 'snana-summary-root.html' )

@app.route( "/summarydata", methods=['POST'] )
def summary_data():
    ss = RomanSurveySummary( "/data/output_2TIER" )
    return {
        'status': 'ok',
        'info': pandas_to_dict( ss.infodf ),
        'snrmax': pandas_to_dict( ss.snrmaxdf ),
        'tier': pandas_to_dict( ss.tierdf ),
        'obs': pandas_to_dict( ss.obsdf ),
        'zhist': pandas_to_dict( ss.zhistdf ),
        'cosmo': pandas_to_dict( ss.cosmodf )
    }

    

# @app.route( "/byfom" )
# def summary_by_fom():
    
