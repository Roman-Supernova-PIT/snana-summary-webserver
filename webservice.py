# Put this first so we can be sure that there are no calls that subvert
#  this in other includes.
import matplotlib
matplotlib.use( "Agg" )
matplotlib.rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
# matplotlib.rc('text', usetex=True)  #  Need LaTeX in Dockerfile
from matplotlib import pyplot

import sys
import traceback
import io
import json
import pathlib
import logging

import flask


from lib.parse_snana import RomanSurveySummary

workdir = pathlib.Path( __name__ ).resolve().parent

app = flask.Flask( __name__, instance_relative_config=True )
app.logger.setLevel( logging.INFO )

def pandas_to_dict( df ):
    if df.index.nlevels == 1:
        return df.to_dict( orient='index' )
    dfdict = {}
    for level in df.index.levels[0]:
        dfdict[level] = pandas_to_dict( df.xs( level, level=0 ) )
    return dfdict

@app.route( "/" )
def mainpage():
    return flask.render_template( 'snana-summary-root.html' )

@app.route( "/summarydata", methods=['POST'] )
def summary_data():
    ss = RomanSurveySummary( "/dev/null", "/data/output_2TIER" )
    rval= {
        'status': 'ok',
        'info': pandas_to_dict( ss.infodf ),
        'snrmax': pandas_to_dict( ss.snrmaxdf ),
        'tier': pandas_to_dict( ss.tierdf ),
        'obs': pandas_to_dict( ss.obsdf ),
        'zhist': pandas_to_dict( ss.zhistdf ),
        'cosmo': pandas_to_dict( ss.cosmodf )
    }
    return rval

@app.route( "/snzhist/<sim>/<fitopt>/<mu>", methods=['GET','POST'] )
def snzhist( sim, fitopt, mu ):
    try:
        sys.stderr.write( f"Hello!  sim={sim}, fitopt={fitopt}, mu={mu}\n" )
        data = {}
        if flask.request.is_json:
            data = flask.request.json()
        width = data['width'] if 'width' in data else 600
        height = data['height'] if 'height' in data else 500
        ss = RomanSurveySummary( "/dev/null", "/data/output_2TIER" )
        tiers = ss.tierdf.index.get_level_values('TIER').unique().values
        ntiers = len(tiers)
        dpi = 72

        fig = pyplot.figure( figsize=(width/dpi, height/dpi), dpi=dpi, tight_layout=True )
        ax = fig.add_subplot( 1, 1, 1 )
        hist = ss.zhistdf.xs( (sim, tiers[0], int(mu)), level=('NAME', 'FIELD', 'MU') )
        dz = hist.index.values[1] - hist.index.values[0] 
        totwid = 0.95
        onewid = totwid * dz / ntiers
        offset = 0.
        for tier in tiers:
            hist = ss.zhistdf.xs( (sim, tier, int(mu)), level=('NAME', 'FIELD', 'MU') )
            # ax.hist( hist.index.values + offset, weights=hist.n.values, rwidth=onewid, align='center', label=tier )
            ax.bar( hist.index.values + offset, height=hist.n.values, width=onewid, align='edge', label=tier )
            offset += totwid * ( hist.index.values[1] - hist.index.values[0] ) / ntiers
            
        ax.legend( fontsize=12 )
        ax.tick_params( "both", labelsize=12 )
        ax.set_xlabel( r'z', fontsize=16 )
        ax.set_ylabel( r'n Roman-discovered SNe', fontsize=16 )

        bio = io.BytesIO()
        fig.savefig( bio, format='png' )
        pyplot.close( fig )

        sys.stderr.write( f"len(bio.getvalue()) = {len(bio.getvalue())}\n" )

        response = flask.make_response( bio.getvalue() )
        response.headers['Content-Type'] = 'image/png'

        sys.stderr.write( f"Response={response}\n" )

        return response
    except Exception as e:
        sys.stderr.write( f"Exception: {e}\n" )
        sys.stderr.write( f"{traceback.format_exc()}\n" )
        return flask.abort( 500 )
    
# @app.route( "/byfom" )
# def summary_by_fom():
    
