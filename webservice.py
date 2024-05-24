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
import re
import math
import json
import yaml
import pathlib
import logging
import random
import numpy
import pandas

import flask
import flask.views

from astropy.io import fits

workdir = pathlib.Path( __name__ ).resolve().parent

# ======================================================================

class BaseView(flask.views.View):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    def argstr_to_args( self, argstr ):
        """Parse argstr as a bunch of /kw=val to a dictionary, update with requesty body if it's json."""

        kwargs = {}
        if argstr is not None:
            for arg in argstr.split("/"):
                match = re.search( '^(?P<k>[^=]+)=(?P<v>.*)$', arg )
                if match is None:
                    sys.stderr.write( f"error parsing url argument {arg}, must be key=value" )
                    return f'error parsing url argument {arg}, must be key=value', 500
                kwargs[ match.group('k') ] = match.group('v')
        if flask.request.is_json:
            kwargs.update( flask.request.json() )
        return kwargs

    def readjson( self, collection, which ):
        f = pathlib.Path( f"/data/{collection}_{which}.json" )
        if not f.is_file():
            raise Exception( f'No {which} file for {collection}' )
        with open( f ) as ifp:
            jsontext = ifp.read()
        return jsontext

    def returnjson( self, collection, which ):
        jsontext = self.readjson( collection, which )
        response = flask.make_response( jsontext )
        response.headers['Content-Type'] = 'application/json'
        return response

# ======================================================================

class MainPage(BaseView):
    def dispatch_request( self ):
        return flask.render_template( 'snana-summary-root.html' )

# ======================================================================

class Collections(BaseView):
    def dispatch_request( self ):
        d = pathlib.Path( "/data" )
        jsonlist = list( d.glob( '*surveys.json' ) )
        jsonlist = [ str(i.name).replace( '_surveys.json', '' ) for i in jsonlist ]
        jsonlist.sort()
        return { 'status': 'ok',
                 'collections': jsonlist }
# ======================================================================

class SurveyInfo(BaseView):
    def dispatch_request( self, collection ):
        return self.returnjson( collection, 'surveyinfo' )

class InstrInfo(BaseView):
    def dispatch_request( self, collection ):
        return self.returnjson( collection, 'instrinfo' )

class AnalysisInfo(BaseView):
    def dispatch_request( self, collection ):
        return self.returnjson( collection, 'analysisinfo' )

class Tiers(BaseView):
    def dispatch_request( self, collection ):
        return self.returnjson( colletion, 'tiers' )

class Surveys(BaseView):
    def dispatch_request( self, collection ):
        return self.returnjson( collection, 'surveys' )

# ======================================================================

class SummaryData(BaseView):
    def dispatch_request( self, collection ):
        try:
            si = self.readjson( collection, 'surveyinfo' )
            ii = self.readjson( collection, 'instrinfo' )
            ai = self.readjson( collection, 'analysisinfo' )
            t = self.readjson( collection, 'tiers' )
            s = self.readjson( collection, 'surveys' )
        except Exception as e:
            return str(e), 500

        response = flask.make_response( f'{{"status": "ok", "surveyinfo": {si}, "instrinfo": {ii}, '
                                        f'"analysisinfo": {ai}, "tiers": {t}, "surveys": {s} }}' )
        response.headers['Content-Type'] = 'application/json'
        return response

# ======================================================================

class SNZHist(BaseView):
    def dispatch_request( self, collection, sim, argstr=None ):
        try:
            data = { 'width': 600,
                     'height': 500,
                     'whichhist': 'zhist',
                     'gentype': 10,
                     'tier': "__ALL__"
                     }
            data.update( self.argstr_to_args( argstr ) )

            surveys = json.loads( self.readjson( collection, 'surveys' ) )
            if sim not in surveys.keys():
                app.logger.error( f"error, could not find survey {sim} in collection {collection}\n" )
                return f'error, could not find survey {sim} in collection {collection}', 500

            survey = surveys[sim]

            gentypes = []
            gentypemap = survey['gentypemap']
            if data['gentype'] == "__ALL__":
                gentypes = list( gentypemap.keys() )
            elif data['gentype'] == "__ALLBUTIA__":
                gentypes = [ t for t in list( gentypemap.keys() ) if t != '10' ]
            else:
                # gentypemap keys are strings, not integers, and I'm kind of boggled by that,
                #   but this is what happens when you work in a type-loosey-goosey language
                gentype = str( data['gentype'] )
                # nl = '\n'
                # sys.stderr.write( f'gentypemap.keys() = '
                #                   f'{nl.join( [f"{i} (type {type(i)})" for i in gentypemap.keys() ] )}\n' )
                if gentype not in gentypemap.keys():
                    app.logger.error( f"Asked for unknown gentype {gentype}\n" )
                    return f"Asked for unknown gentype {gentype}", 500
                gentypes = [ gentype ]

            histdata = None
            if data['whichhist'] == 'zhist':
                histdata = survey['zhist']
            elif data['whichhist'] == 'snrmaxzhist':
                histdata = survey['snrmaxzhist']
            elif data['whichhist'] == 'snrmax2zhist':
                histdata = survey['snrmax2zhist']
            elif data['whichhist'] == 'snrmax3zhist':
                histdata = survey['snrmax3zhist']
            else:
                app.logger.error( f'Unknown snrmax {whichhist}, must be one of '
                                  f'(zhist,snrmaxzhist,snrmax2zhist,snrmax3zhist)\n' )
                return f'Unknown snrmax {snrmax}', 500

            tiers = []
            if data['tier'] == '__ALL__':
                tiers = []
                for t in histdata['tier']:
                    if t not in tiers:
                        tiers.append( t )
            else:
                if data['tier'] not in histdata['tier']:
                    return f'Unknown tier {data["tier"]}', 500
                tiers = [ data['tier'] ]

            if ( len(tiers) < 1 ) or ( len(gentypes) < 1 ):
                return f'Ended up with {len(tiers)} tiers and {len(gentypes)}; must have at least 1 of both'

            nbars = len( tiers ) * len( gentypes )
            dpi = 72

            # TODO : types.  gentypemap, gentype, gentypes, blah.  int or str?

            fig = pyplot.figure( figsize=(data['width']/dpi, data['height']/dpi), dpi=dpi, tight_layout=True )
            ax = fig.add_subplot( 1, 1, 1 )
            # dz = histdata['zCMB'][1] - histdata['zCMB'][0] # this is wrong
            dz = 0.1 # TODO NOT HARDCODE
            totwid = 0.90
            onewid = totwid * dz / nbars
            offset = 0.
            # sys.stderr.write( f"histdata.keys() = {histdata.keys()}\n" )
            # sys.stderr.write( f"zcmb: {histdata['zCMB']}\n"
            #                   f"n: {histdata['n']}\n"
            #                   f"tier: {histdata['tier']}\n"
            #                   f"gentype: {histdata['gentype']}\n" )
            # sys.stderr.write( f"histdata['tier'][0]=='DEEP' = {histdata['tier'][0]=='DEEP'}\n" )
            # sys.stderr.write( f"histdata['gentype'][0]==10 = {histdata['gentype'][0]==10}\n" )
            histzcmb = numpy.array( histdata['zCMB'] )
            histn = numpy.array( histdata['n'] )
            histtier = numpy.array( histdata['tier'] )
            histtype = numpy.array( histdata['gentype' ] )
            for gentype in gentypes:
                gentype = int(gentype)
                for tier in tiers:
                    x = histzcmb[ ( histtier == tier ) & ( histtype == gentype ) ]
                    y = histn[ ( histtier == tier ) & ( histtype == gentype ) ]
                    ax.bar( x + offset, height=y, width=onewid, align='edge',
                            label=f'{tier} {gentypemap[str(gentype)]} ({y.sum()})' )
                    offset += totwid * dz / nbars

            ax.legend( fontsize=12 )
            ax.tick_params( "both", labelsize=12 )
            ax.set_xlabel( r'z_CMB', fontsize=16 )
            ax.set_ylabel( r'n Roman-discovered objects', fontsize=16 )
            ax.set_title( f'{sim} ; FoM_stat = {surveys[sim]["muopt"][0]["FoM_stat"]:.1f}', fontsize=16 )

            bio = io.BytesIO()
            fig.savefig( bio, format='svg' )
            pyplot.close( fig )

            response = flask.make_response( bio.getvalue() )
            # response.headers['Content-Type'] = 'image/png'
            response.headers['Content-Type'] = 'image/svg+xml'

            return response
        except Exception as e:
            app.logger.exception( e )
            return flask.abort( 500 )

# ======================================================================

class SpecHist(BaseView):
    def dispatch_request( self, which, collection, sim, strategy, argstr=None ):
        try:
            data = { 'width': 600,
                     'height': 500,
                     'gentype': 10,
                     'tier': "__ALL__",
                     'zbin': None,
                     'tbin': None,
                     'magbin': None,
                     'snrbin': None,
                     'band': 'J',
                     'tframe': 'obs'
                    }
            data.update( self.argstr_to_args( argstr ) )

            if which not in [ 'mag', 'snr', 'z', 'rest_phase_z' ]:
                return f'which must be one of mag, snr, z, or rest_phase_z', 500

            if data['tframe'] == 'rest':
                data['banddf'] = f"{data['band']}_restframe"
            elif data['tframe'] == 'obs':
                data['banddf'] = data['band']
            else:
                return f'tframe must be rest or obs', 500

            surveys = json.loads( self.readjson( collection, 'surveys' ) )
            if sim not in surveys.keys():
                sys.stderr.write( f"error, could not find survey {sim} in collection {collection}\n" )
                return f"error, could not find survey {sim} in collection {collection}", 500

            survey = surveys[sim]
            if ( 'spechists' not in surveys[sim] ) or ( len(surveys[sim]['spechists']) == 0 ):
                return f"Survey doesn't have prism info.", 500
            data['gentypemap'] = survey['gentypemap']

            spechists = survey['spechists']

            if ( strategy < 0 ) or ( strategy >= spechists['nspecstrategies'] ):
                return f"There are {spechists['nspecstrategies']} spectrum stragies; {strategy} is out of range", 500

            if data['tbin'] is None:
                data['tbin'] = int( -spechists['tobsmin'] / spechists['deltat'] + 0.5 )
            if data['snrbin'] is None:
                data['snrbin'] = int( ( 10. - spechists['snirmin'] ) / spechists['deltasnr'] + 0.5 )
            if data['zbin'] is None:
                data['zbin'] = 5
            if data['magbin'] is None:
                data['magbin'] = 5

            data['tbin'] = int( data['tbin'] )
            data['t'] = spechists['tobsmin'] + data['tbin'] * spechists['deltat']
            data['snrbin'] = int( data['snrbin'] )
            data['snr'] = spechists['snrmin'] + data['snrbin'] * spechists['deltasnr']
            if ( data['zbin'] == '__all__' ):
                data['z'] = '(all)';
            else:
                data['zbin'] = int( data['zbin'] )
                data['z'] = spechists['zmin'] + data['zbin'] * spechists['deltaz']
            if ( data['magbin'] == '__all__' ):
                data['mag'] = '(all)'
            else:
                data['magbin'] = int( data['magbin'] )
                data['mag'] = spechists['mmin'] + data['magbin'] * spechists['deltam']

            if data['tier'] == '__ALL__':
                data['tier'] = list( spechists['spectrumhists'][strategy].keys() )
            else:
                data['tier'] = [ data['tier'] ]

            # This will be used in spechist_*

            data['deltaz'] = spechists['deltaz']
            data['deltat'] = spechists['deltat']
            data['deltasnr'] = spechists['deltasnr']
            data['deltam'] = spechists['deltam']

            # Gentype counting
            gentypes = []
            for tier in data['tier']:
                df = pandas.DataFrame( spechists['spectrumhists'][strategy][tier][data['banddf']] )
                if ( data['gentype'] == '__ALL__' ) or ( data['gentype'] == '__ALLBUTIA__' ):
                    for gentype in df['GENTYPE'].unique():
                        if gentype not in gentypes:
                            if ( data['gentype'] == '__ALL__' ) or ( gentype != 10 ):
                                gentypes.append( gentype )

            if len(gentypes) == 0:
                gentype = data['gentype']
                if str(gentype) not in data['gentypemap'].keys():
                    return f"Asked for unknown gentype {gentype}", 500
                gentypes = [ gentype ]

            if which == 'mag':
                return self.spechist_mag( sim, survey, spechists['spectrumhists'][strategy], gentypes,
                                          spechists['mmin'], spechists['mmax'], spechists['deltam'],
                                          data, argstr )
            elif which == "snr":
                return self.spechist_snr( sim, survey, spechists['spectrumhists'][strategy], gentypes,
                                          spechists['snrmin'], spechists['snrmax'], spechists['deltasnr'],
                                          data, argstr )
            elif which == "z":
                return self.spechist_z( sim, survey, spechists['spectrumhists'][strategy], gentypes,
                                        spechists['zmin'], spechists['zmax'], spechists['deltaz'],
                                        data, argstr )
            elif which == "rest_phase_z":
                return self.heatmap_restphase_z( sim, survey, spechists['spectrumhists'][strategy], gentypes,
                                                 spechists['zmin'], spechists['zmax'], spechists['deltaz'],
                                                 spechists['tobsmin'], spechists['tobsmax'], spechists['deltat'],
                                                 data, argstr )
            else:
                return "Error 27B/6", 500

        except Exception as ex:
            sys.stderr.write( f"Exception: {ex}\n" )
            sys.stderr.write( f"{traceback.format_exc()}\n" )
            return flask.abort( 500 )


    def plothist( self, sim, dfs, minval, maxval, delta, binstr, gentypes, survey, data, extra_title="", x_title="" ):
        nbars = len( data['tier'] ) * len( gentypes )
        dpi = 72

        fig = pyplot.figure( figsize=(data['width']/dpi, data['height']/dpi), dpi=dpi, tight_layout=True )
        ax = fig.add_subplot( 1, 1, 1 )
        totwid = 0.90
        onewid = totwid * delta / nbars
        offset = 0.
        for gentype in gentypes:
            gentype = int( gentype )
            for tier in data['tier']:
                df = dfs[tier]
                df = df[ df['GENTYPE'] == gentype ]
                x = minval + df[binstr] * delta
                y = df['n']
                ax.bar( x + offset, height=y, width=onewid, align='edge',
                        label=f'{tier} {data["gentypemap"][str(gentype)]}' )
                offset += totwid * delta / nbars

        ax.legend( fontsize=12 )
        ax.tick_params( "both", labelsize=12 )
        ax.set_xlim( minval, maxval )
        ax.set_xlabel( x_title, fontsize=16 )
        ax.set_ylabel( r'N', fontsize=16 )
        ax.set_title( f'{sim} ; FoM_stat = {survey["muopt"][0]["FoM_stat"]:.1f}\nband {data["band"]}{extra_title}',
                      fontsize=16 )

        bio = io.BytesIO()
        fig.savefig( bio, format='svg' )
        pyplot.close( fig )

        response = flask.make_response( bio.getvalue() )
        response.headers['Content-Type'] = 'image/svg+xml'

        return response


    def spechist_z( self, sim, survey, spechists, gentypes, zmin, zmax, dz, data, argstr ):
        # Pandafication
        dfs = {}
        tbin = 'trestbin' if data['tframe'] == 'rest' else 'tbin'
        for tier in data['tier']:
            df = pandas.DataFrame( spechists[tier][data['banddf']] )
            df = df.loc[ ( df[tbin] == data['tbin'] ) & ( df['snrbin'] >= data['snrbin'] ),
                         [ 'GENTYPE', 'zbin', 'snrbin', 'n' ] ]
            df = df.groupby( [ 'GENTYPE', 'zbin' ] ).sum()[ 'n' ].reset_index()
            dfs[tier] = df

        extra_title = ""
        for tier in spechists.keys():
            extra_title += f", t_exp({tier})={spechists[tier]['texpose']}s"
        extra_title += f"\nt_{data['tframe']}=[{data['t']:.0f},{data['t']+data['deltat']:.0f}) d, "
        extra_title += f"S/N≥{data['snr']:.0f}"

        return self.plothist( sim, dfs, zmin, zmax, dz, 'zbin', gentypes, survey, data,
                              extra_title=extra_title, x_title="z (heliocentric)" )


    def spechist_mag( self, sim, survey, spechists, gentypes, mmin, mmax, dm, data, argstr ):
        dfs = {}
        tbin = 'trestbin' if data['tframe'] == 'rest' else 'tbin'
        for tier in data['tier']:
            df = pandas.DataFrame( spechists[tier][data['banddf']] )
            df = df.loc[ df[tbin] == data['tbin'], [ 'GENTYPE', 'magbin', 'zbin', 'n' ] ]
            if data['zbin'] != '__all__':
                df = df.loc[ df['zbin'] == data['zbin'], : ]
            df = df.groupby( [ 'GENTYPE', 'magbin' ] ).sum()[ 'n' ].reset_index()
            dfs[tier] = df

        extra_title = ""
        for tier in spechists.keys():
            extra_title += f", t_exp({tier})={spechists[tier]['texpose']}s"
        extra_title += f"\nt_{data['tframe']}=[{data['t']:.0f},{data['t']+data['deltat']:.0f}) d"
        if data['zbin'] != '__all__':
            extra_title += f", z_hel=[{data['z']:.0f},{data['z']+data['deltaz']:.0f})"
        else:
            extra_title += f", all z"

        return self.plothist( sim, dfs, mmin, mmax, dm, 'magbin', gentypes, survey, data,
                              extra_title=extra_title, x_title='observed magnitude' )


    def spechist_snr( self, sim, survey, spechists, gentypes, snrmin, snrmax, dsnr, data, argstr ):
        dfs = {}
        tbin = 'trestbin' if data['tframe'] == 'rest' else 'tbin'
        for tier in data['tier']:
            df = pandas.DataFrame( spechists[tier][data['banddf']] )
            df = df.loc[ df[tbin] == data['tbin'], [ 'GENTYPE', 'snrbin', 'zbin', 'n' ] ]
            if data['zbin'] != '__all__':
                df = df.loc[ df['zbin'] == data['zbin'], : ]
            df = df.groupby( [ 'GENTYPE', 'snrbin' ] ).sum()[ 'n' ].reset_index()
            dfs[tier] = df

        extra_title = ""
        for tier in spechists.keys():
            extra_title += f", t_exp({tier})={spechists[tier]['texpose']}s"
        extra_title += f"\nt_{data['tframe']}=[{data['t']:.0f},{data['t']+data['deltat']:.0f}) d"
        if data['zbin'] != '__all__':
            extra_title += f", z_hel=[{data['z']:.0f},{data['z']+data['deltaz']:.0f})"
        else:
            extra_title += f", all z"

        return self.plothist( sim, dfs, snrmin, snrmax, dsnr, 'snrbin', gentypes, survey, data,
                              extra_title=extra_title, x_title=f'S/N integrated over {data["band"]}-band' )


    def heatmap_restphase_z( self, sim, survey, spechists, gentypes, zmin, zmax, dz, tmin, tmax, dt, data, argstr ):
        masterdf = None
        tbin = 'trestbin'
        # In this case, we're not going to try to represent different tiers and gentypes, but
        #   just sum together all the included tiers and gentypes.
        for tier in data['tier']:
            df = pandas.DataFrame( spechists[tier][f"{data['band']}_restframe"] )
            df = df.loc[ df['snrbin'] >= data['snrbin'], [ 'GENTYPE', 'zbin', tbin, 'n' ] ]
            df = ( df.groupby( [ 'GENTYPE', 'zbin', tbin ] ).sum()[ 'n' ]
                   .reset_index().set_index( ['zbin', tbin ] ) )
            gtsumdf = None
            for gentype in gentypes:
                thisgtdf = df.loc[ df['GENTYPE'] == int(gentype), ['n'] ]
                if gtsumdf is None:
                    gtsumdf = thisgtdf
                else:
                    gtsumdf = gtsumdf.add( thisgtdf, fill_value=0 )
            if masterdf is None:
                masterdf = gtsumdf
            else:
                masterdf = masterdf.add( gtsumdf, fill_value=0 )

        # app.logger.debug( f'masterdf=\n{masterdf}\n{masterdf.unstack(level=tbin)}' )

        # Make sure that the index values are continuous, so that imshow will be meaningful
        zbinvals = masterdf.index.get_level_values( level='zbin' ).values
        zbinmin = zbinvals.min()
        zbinmax = zbinvals.max()
        tbinvals = masterdf.index.get_level_values( level=tbin ).values
        tbinmin = tbinvals.min()
        tbinmax = tbinvals.max()

        zbinvals = []
        for z in range( zbinmin, zbinmax+1 ):
            zbinvals.extend( [z] * (tbinmax-tbinmin+1) )
        tbinvals = list( range( tbinmin, tbinmax+1 ) ) * (zbinmax-zbinmin+1 )

        template = pandas.DataFrame( { 'zbin': zbinvals, tbin: tbinvals, 'n': [0]*len(tbinvals)  } )
        template.set_index( [ 'zbin', tbin ], inplace=True )
        # app.logger.debug( f'template=\n{template}\n{template.unstack(level=tbin)}' )
        masterdf = masterdf.reindex_like( template )
        masterdf[ masterdf.isna() ] = 0
        grid = masterdf.unstack( level=tbin, fill_value=0 )

        # app.logger.debug( f'grid=\n{grid}\n' )
        # app.logger.debug( f'zbinmin={zbinmin}, zbinmax={zbinmax}, tbinmin={tbinmin}, tbinmax={tbinmax}' )

        zlo = zmin + zbinmin * dz
        zhi = zmin + (zbinmax+1) * dz
        tlo = tmin + tbinmin * dt
        thi = tmin + (tbinmax+1) * dt

        # app.logger.debug( f'zlo={zlo}, zhi={zhi}, dz={dz}, tlo={tlo}, thi={thi}, dt={dt}' )

        # OK, plot

        dpi = 72
        fig = pyplot.figure( figsize=(data['width']/dpi, data['height']/dpi), dpi=dpi, tight_layout=True )
        ax = fig.add_subplot( 1, 1, 1 )
        img = ax.imshow( grid['n'].values,
                         aspect='auto',
                         origin='lower',
                         extent=( tlo, thi, zlo, zhi ) )
        ax.figure.colorbar( img, ax=ax )

        ax.tick_params( "both", labelsize=12 )
        ax.set_ylabel( 'z', fontsize=16 )
        ax.set_xlabel( 't_rest rel. max (d)', fontsize=16 )
        ax.set_title( f'{sim} ; FoM_stat = {survey["muopt"][0]["FoM_stat"]:.1f}\n'
                      f'band={data["band"]}; S/N≥{data["snr"]:.0f}', fontsize=16 )

        bio = io.BytesIO()
        fig.savefig( bio, format='svg' )
        pyplot.close( fig )

        response = flask.make_response( bio.getvalue() )
        response.headers['Content-Type'] = 'image/svg+xml'

        return response



# ======================================================================

class RandomLTCV(BaseView):
    def dispatch_request( self, collection, sim, gentype, z, dz ):
        try:
            gentype = int(gentype)
            z = float(z)
            dz = float(dz)

            # TODO : update this to when there is more than one collection sim dir

            # HACK ALERT : update this when collection names are more coherent

            app.logger.debug( f"gentype={gentype}, z={z}, dz={dz}" )

            simcomps = sim.strip().split()
            app.logger.debug( f"collection={collection}, sim={sim}" )
            app.logger.debug( f"collection={collection}, sim={sim}, simcomps[1]={simcomps[1]}" )
            subdir = pathlib.Path( "/snana_sim" ) / f'ROMAN_{collection}_DATA-{simcomps[1]}'
            g = [ i for i in subdir.glob( "*.README" ) ]
            if len(g) == 0:
                app.logger.error( f"Couldn't find a *.README file in {subdir}" )
                raise RuntimeError( "Error parsing snana output data" )
            if len(g) > 1:
                app.logger.error( f"Found more than one *.README file in {subdir}" )
                raise RuntimeError( "Error parsing snana output data" )

            with open( g[0] ) as ifp:
                blob = yaml.safe_load( ifp.read() )

            model = None
            for key in blob['DOCUMENTATION'].keys():
                if key[0:11] == "INPUT_KEYS_":
                    if blob['DOCUMENTATION'][key]['GENTYPE'] == gentype:
                        model = key[11:]
                        app.logger.debug( f"Found gentype {gentype} as model {model}" )

            if model is None:
                app.logger.error( f"Couldn't find model for gentype {gentype}" )
                raise RuntimeError( "Couldn't find snana files for type" )

            # TODO : assuming gzipped, fix that
            g = [ i for i in subdir.glob( f"ROMAN_{model}-*_HEAD.FITS.gz" ) ]
            random.shuffle( g )
            app.logger.info( f"Looking in files {g}" )

            found = False
            for headfile in g:
                with fits.open(headfile) as f:
                    tab = f[1].data
                    app.logger.debug( f"Read {headfile.name}, got {len(tab)} rows" )
                    rightz = tab[ ( tab['SIM_REDSHIFT_CMB'] >= z - dz ) & ( tab['SIM_REDSHIFT_CMB'] <= z + dz ) ]
                    app.logger.debug( f"Found {len(rightz)} at z={z}±{dz}" )
                    if len(rightz) == 0:
                        continue
                    dex = random.randint( 0, len(rightz)-1 )

                    if rightz[dex]['SIM_GENTYPE'] != gentype:
                        app.logger.error( f"gentype mismatch error" )
                        raise RuntimeError( "Gentype from HEAD file didn't match expected" )

                    snid = rightz[dex]['SNID']
                    ptrobs_min = rightz[dex]['PTROBS_MIN'] - 1
                    ptrobs_max = rightz[dex]['PTROBS_MAX']
                    snz = rightz[dex]['SIM_REDSHIFT_CMB']
                    mwebv = rightz[dex]['SIM_MWEBV']
                    av = rightz[dex]['SIM_AV']
                    rv = rightz[dex]['SIM_RV']
                    found = True

                    photfile = headfile.parent / headfile.name.replace( '_HEAD.FITS.gz', '_PHOT.FITS.gz' )
                    break

            if not found:
                app.logger.error( f"Failed to find an object of type {gentype} at z {z}±{dz}" )
                raise RuntimeError( f"Failed to find an object of type {gentype} at z {z}±{dz}" )

            retval = {
                'status': 'ok',
                'snid': int(snid),    # I hope python int can handle a 64-bit integer...
                'zcmb': float(snz),
                'mwebv': float(mwebv),
                'av': float(av),
                'rv': float(rv),
                'zp': 27.5,      # Standard snana zeropoint
                'ltcv': {}
                }

            app.logger.error( f"Opening photfile {photfile.name}" )
            with fits.open( photfile ) as f:
                photdata = f[1].data[ ptrobs_min : ptrobs_max ]

            app.logger.error( f"photdata columns: {photdata.columns}" )

            for band in numpy.unique( photdata['BAND'] ):
                banddata = photdata[ photdata['BAND'] == band ]
                retval['ltcv'][band] = { 'mjd': [ float(i) for i in banddata['MJD'] ],
                                         'flux': [ float(i) for i in banddata['FLUXCAL'] ],
                                         'dflux': [ float(i) for i in banddata['FLUXCALERR'] ] }

            return retval
        except Exception as ex:
            app.logger.exception( ex )
            return { 'status': 'error', 'error': str(ex) }

# ======================================================================

app = flask.Flask( __name__, instance_relative_config=True )
# app.logger.setLevel( logging.INFO )
app.logger.setLevel( logging.DEBUG )

app.add_url_rule( "/",
                  view_func=MainPage.as_view("mainpage"),
                  strict_slashes=False )

rules = {
    "/collections": Collections,
    "/surveyinfo/<string:collection>": SurveyInfo,
    "/instrinfo/<string:collection>": InstrInfo,
    "/analysisinfo/<string:collection>": AnalysisInfo,
    "/tiers/<string:collection>": Tiers,
    "/surveys/<string:collection>": Surveys,
    "/summarydata/<string:collection>": SummaryData,
    "/snzhist/<string:collection>/<string:sim>": SNZHist,
    "/snzhist/<string:collection>/<string:sim>/<path:argstr>": SNZHist,
    "/spechist/<string:which>/<string:collection>/<string:sim>/<int:strategy>": SpecHist,
    "/spechist/<string:which>/<string:collection>/<string:sim>/<int:strategy>/<path:argstr>": SpecHist,
    "/randomltcv/<string:collection>/<string:sim>/<int:gentype>/<float:z>/<float:dz>": RandomLTCV,
}

lastname = None
for url, cls in rules.items():
    match = re.search( "^/([^/]+)", url )
    if match is None:
        raise ValueError( f"Bad url {url}" )
    name = match.group(1)
    if name == lastname:
        # Kind of a hack so that flask doesn't get pissy about repeated names
        name += "x"
    lastname = name
    app.add_url_rule( url, view_func=cls.as_view(name), methods=["GET","POST"], strict_slashes=False )
