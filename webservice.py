# Put this first so we can be sure that there are no calls that subvert
#  this in other includes.
import matplotlib
matplotlib.use( "Agg" )
# matplotlib.rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
# matplotlib.rc('text', usetex=True)  #  Need LaTeX in Dockerfile
from matplotlib import pyplot

import sys
import traceback
import io
import json
import pathlib
import logging
import numpy

import flask

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

@app.route( "/", strict_slashes=False )
def mainpage():
    return flask.render_template( 'snana-summary-root.html' )

@app.route( "/collections", methods=['POST'], strict_slashes=False )
def collections():
    d = pathlib.Path( "/data" )
    jsonlist = list( d.glob( '*surveys.json' ) )
    jsonlist = [ str(i.name).replace( '_surveys.json', '' ) for i in jsonlist ]
    return { 'status': 'ok',
             'collections': jsonlist }

def readjson( collection, which ):
    f = pathlib.Path( f"/data/{collection}_{which}.json" )
    if not f.is_file():
        raise Exception( f'No {which} file for {collection}' )
    with open( f ) as ifp:
        jsontext = ifp.read()
    return jsontext
        
def returnjson( collection, which ):
    jsontext = readjson( collection, which )
    response = flask.make_response( jsontext )
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route( "/surveyinfo/<collection>", methods=['POST'], strict_slashes=False )
def surveyinfo( collection ):
    return returnjson( collection, 'surveyinfo' )

@app.route( "/instrinfo/<collection>", methods=['POST'], strict_slashes=False )
def instrinfo( collection ):
    return returnjson( collection, 'instrinfo' )

@app.route( "/analysisinfo/<collection>", methods=['POST'], strict_slashes=False )
def analysisinfo( collection ):
    return returnjson( collection, 'analysisinfo' )

@app.route( "/tiers/<collection>", methods=['POST'], strict_slashes=False )
def tiers( collection ):
    return returnjson( colletion, 'tiers' )

@app.route( "/surveys/<collection>", methods=['POST'], strict_slashes=False )
def surveys( collection ):
    return returnjson( collection, 'surveys' )

@app.route( "/summarydata/<collection>", methods=['POST'], strict_slashes=False )
def summarydata( collection ):
    try:
        si = readjson( collection, 'surveyinfo' )
        ii = readjson( collection, 'instrinfo' )
        ai = readjson( collection, 'analysisinfo' )
        t = readjson( collection, 'tiers' )
        s = readjson( collection, 'surveys' )
    except Exception as e:
        return str(e), 500

    response = flask.make_response( f'{{"status": "ok", "surveyinfo": {si}, "instrinfo": {ii}, '
                                    f'"analysisinfo": {ai}, "tiers": {t}, "surveys": {s} }}' )
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route( "/snzhist/<string:collection>/<string:sim>", methods=['GET','POST'], strict_slashes=False )
@app.route( "/snzhist/<string:collection>/<string:sim>/<int:snrmax>", methods=['GET','POST'], strict_slashes=False )
@app.route( "/snzhist/<string:collection>/<string:sim>/<int:snrmax>/<path:gentype>",
            methods=['GET','POST'], strict_slashes=False )
@app.route( "/snzhist/<string:collection>/<string:sim>/<int:snrmax>/<path:gentype>/<string:tier>",
            methods=['GET','POST'], strict_slashes=False )
def snzhist( collection, sim, snrmax=0, gentype='Ia', tier=None ):
    try:
        sys.stderr.write( f"Hello!  collection={collection}, sim={sim}, gentype={gentype}\n" )
        data = {}
        if flask.request.is_json:
            data = flask.request.json()
        width = data['width'] if 'width' in data else 600
        height = data['height'] if 'height' in data else 500

        surveys = json.loads( readjson( collection, 'surveys' ) )
        if sim not in surveys.keys():
            sys.stderr.write( f"error, could not find survey {sim} in collection {collection}\n" )
            return f'error, could not find survey {sim} in collection {collection}', 500

        survey = surveys[sim]
        
        gentypes = []
        gentypemap = survey['gentypemap']
        if gentype is None:
            gentypes = [ 10 ]
        else:
            if str(gentype) == "all":
                gentypes = list( gentypemap.keys() )
            else:
                gentypes = []
                for s in str(gentype).split('/'):
                    if len(s) == 0: continue
                    if s not in survey['gentypemap'].values():
                        sys.stderr.write( f"error, unknown gentype {s}\n" )
                        return f'error, unknown gentype {s}', 500
                    gentypes.append( list(gentypemap.keys())[ list(gentypemap.values()).index(s) ] )
        sys.stderr.write( f"Got gentypes: {gentypes}\n" )
                    
        hist = None
        if snrmax == 0:
            histdata = survey['zhist']
        elif snrmax == 1:
            histdata = survey['snrmaxzhist']
        elif snrmax == 2:
            histdata = survey['snrmax2zhist']
        elif snrmax == 3:
            histdata = survey['snrmax3zhist']
        else:
            sys.stderr.write( f'Unknown snrmax {snrmax}, must be one of (0,1,2,3)\n' )
            return f'Unknown snrmax {snrmax}, must be one of (0,1,2,3)', 500

        if tier is None:
            tiers = []
            for t in histdata['tier']:
                if t not in tiers:
                    tiers.append( t )
        else:
            if tier not in histdata['tier']:
                return f'Unknown tier {tier}', 500
            tiers = [ tier ]
        sys.stderr.write( f"Got tiers: {tiers}\n" )
            
        if ( len(tiers) < 1 ) or ( len(gentypes) < 1 ):
            return f'Ended up with {len(tiers)} tiers and {len(gentypes)}; must have at least 1 of both'

        nbars = len( tiers ) * len( gentypes )
        dpi = 72

        # TODO : types.  gentypemap, gentype, gentypes, blah.  int or str?
        
        fig = pyplot.figure( figsize=(width/dpi, height/dpi), dpi=dpi, tight_layout=True )
        ax = fig.add_subplot( 1, 1, 1 )
        # dz = histdata['zCMB'][1] - histdata['zCMB'][0] # this is wrong
        dz = 0.1 # TODO NOT HARDCODE
        totwid = 0.90
        onewid = totwid * dz / nbars
        offset = 0.
        sys.stderr.write( f"histdata.keys() = {histdata.keys()}\n" )
        sys.stderr.write( f"zcmb: {histdata['zCMB']}\n"
                          f"n: {histdata['n']}\n"
                          f"tier: {histdata['tier']}\n"
                          f"gentype: {histdata['gentype']}\n" )
        sys.stderr.write( f"histdata['tier'][0]=='DEEP' = {histdata['tier'][0]=='DEEP'}\n" )
        sys.stderr.write( f"histdata['gentype'][0]==10 = {histdata['gentype'][0]==10}\n" )
        histzcmb = numpy.array( histdata['zCMB'] )
        histn = numpy.array( histdata['n'] )
        histtier = numpy.array( histdata['tier'] )
        histtype = numpy.array( histdata['gentype' ] )
        for gentype in gentypes:
            gentype = int(gentype)
            for tier in tiers:
                sys.stderr.write( f"Doing tier \"{tier}\" ({type(tier)}) gentype {gentype} ({type(gentype)})\n" )
                x = histzcmb[ ( histtier == tier ) & ( histtype == gentype ) ]
                y = histn[ ( histtier == tier ) & ( histtype == gentype ) ]
                sys.stderr.write( f"x={x}\n" )
                sys.stderr.write( f"y={y}\n" )
                ax.bar( x + offset, height=y, width=onewid, align='edge',
                        label=f'{tier} {gentypemap[str(gentype)]}' )
                offset += totwid * dz / nbars
            
        ax.legend( fontsize=12 )
        ax.tick_params( "both", labelsize=12 )
        ax.set_xlabel( r'z_CMB', fontsize=16 )
        ax.set_ylabel( r'n Roman-discovered objects', fontsize=16 )

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
    
# @app.route( "/byfom", strict_slashes=False )
# def summary_by_fom():
    
