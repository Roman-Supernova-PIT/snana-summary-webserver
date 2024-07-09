import sys
import os
import io
import pathlib
import re
import gzip
import yaml
import json
import subprocess
import logging
import pickle
import argparse
import traceback
import numpy
import pandas

_logger = logging.getLogger("main")
_logout = logging.StreamHandler( sys.stderr )
_logger.addHandler( _logout )
_formatter = logging.Formatter( f'[%(asctime)s - %(levelname)s] - %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S' )
_logout.setFormatter( _formatter )
_logger.setLevel( logging.INFO )
# _logger.setLevel( logging.DEBUG )

class NumpyEncoder(json.JSONEncoder ):
    def default( self, obj ):
        if isinstance( obj, numpy.int64 ):
            return int( obj )
        if isinstance( obj, numpy.float64 ):
            return float( obj )
        return super().default( obj )

class RomanSurveySummary:
    known_filters = ['R', 'Z', 'Y', 'J', 'H', 'F', 'K']
    surveynameparse = re.compile( '^(.*)\.SIMLIB(\.gz)?' )

    def __init__( self, outdir, searchdir=None, snana_simdir=None, snrmaxcut=5. ):
        self.outdir = pathlib.Path( outdir )
        self.collections = {}
        self.snana_scratchdir = {}
        self.snrmaxcut = snrmaxcut
        self.snana_simdir = None if snana_simdir is None else pathlib.Path( snana_simdir )
        self.searchdir = None if searchdir is None else pathlib.Path( searchdir )

    def _read_inp_files( self, snana_outdir ):
        """Internal : read a INP* and ANALYSIS_INSTRUCTIONS.README file for a single SNANA outdir.

        One such directory might be:

           /global/cfs/cdirs/m4385/survey_strategy_optimization/pipeline_output/2024-05-16_x536/output_1TIER_PRISM10

        The directory is expected to have a single file named INP* as a yaml file.

        Returns surveyinfo, instrinfo, analysisinfo, tiers, filemap

        surveyinfo is a dict with the CONFIG_SURVEY dictionary from the INP* file
           * FORCE_SNRMAX is converted from an array of strings (each
             row has "SNR [λ0, λ1]") to an array of dictionaries
             {'snr': <float>, 'lam0': <float>, 'lam1': <float> }

           * MJD_SEASONS is converted from an array of strings to an array of dicts
               { 'season_mjd0': <float>, 'season_mjd1': <float> }

        instrinfo is a dict with the yaml read from the file whose path
           is given by the CONFIG_INSTRUMENT_FILE field of the INP* file

        analysisinfo is a dict with the CONFIG_ANALYSIS_PREP dictionary from the INP* file
           * field 'muopt' is a list dicts containing mu options; it always starts with
                  { 'name': 'standard', 'idsurvey_select': -99 }
                  (This is not explicitly in the INP file, but is implied.)
             additional lines are parsed from the analysisinfo['BBC']['MUOPT'], if that key exists

           * prescales is a dictionary of { type:str : prescale:float }
             - It is parsed from analysisinfo['SIM']['PRESCALE_TRANSIENT_LSIT']
             - HACK ALERT : analysinsof['prescales']'IIP+IIL' is added to have the same value as ...['IIL']

        tiers is a list of dicts, parsed out of surveyinfo['TIERS']; each element of the list has:
              { 'name': <str>, 'ra': <float>, 'dec': <float>, 'bands': <list of str>,
                'relarea': <list of int>, 'dt_visit': <list of float>, 'z_snrmatch': <list of float> }
          the length of the lists can be different; the three lists define a 3d matrix of sims to run.

        filemap is a pandas dataframe parsed from the csv file
           ANALSYS_INSTRUCTIONS.README in the same directory.  Each row
           in that file has the version name, the simlib file, and the
           three indices into area, t_exp, and z_snrmax.  filemap is a
           pandas dataframe with keys i_AREA, i_TEXPOSE, and i_zSNRMAX.

        """

        files = [ f for f in snana_outdir.glob( "INP*" ) ]
        if len(files) != 1:
            raise RuntimeError( f"There are {len(files)} INP* files in {snana_outdir.name}, expected 1" )
        inputfile = files[0]

        analysis_instr = snana_outdir / "ANALYSIS_INSTRUCTIONS.README"
        if not analysis_instr.is_file():
            raise FileNotFoundError( f"Could not find ANALYSIS_INSTRUCTIONS.README in {snana_outdir.name}" )

        # files = [ f for f in snana_outdir.glob( "OUTPUT1*" ) ]
        # if len(files) != 1:
        #     raise RuntimeError( f"There are {len(files)} OUTPUT1* files in {snana_outdir.name}, expected 1" )
        # snana_output1 = files[0]
        # if not snana_output1.is_dir():
        #     raise FileNotFoundError( f"{snana_output1} is not a directory" )

        # mergelog = snana_output1 / 'MERGE.LOG'
        # if not mergelog.is_file():
        #     raise FileNotFoundError( f"Failed to find {snana_outputdir.name}/{snana_output1.name}/MERGE.LOG" )

        # Read the ANALYSIS_INSTRUCTIONS.README file to get a list of
        #  simlibs files and version names as a function of indexes into area, texpose, snrmatch

        # filemap = pandas.read_csv( analysis_instr, delim_whitespace=True, comment='#', skip_blank_lines=True )
        filemap = pandas.read_csv( analysis_instr, sep='\s+', comment='#', skip_blank_lines=True )
        filemap.set_index( [ 'i_AREA', 'i_TEXPOSE', 'i_zSNRMAX' ], inplace=True )

        # Read the INP file

        with open( inputfile ) as ifp:
            blob = yaml.safe_load( ifp.read() )

        surveyinfo = blob['CONFIG_SURVEY']
        analysisinfo = blob['CONFIG_ANALYSIS_PREP']

        instrinfofile = blob['CONFIG_INSTRUMENT_FILE'].replace( '$SNANA_ROMAN_ROOT', os.getenv('SNANA_ROMAN_ROOT') )
        with open( instrinfofile ) as ifp:
            instrinfo = yaml.safe_load( ifp.read() )

        # Turn some of the arrays into subdicts
        parse_snrmax = re.compile( r'^\s*(?P<snr>\d*\.?\d+)\s+\[(?P<lam0>\d*\.?\d+),'
                                   r'\s+(?P<lam1>\d*\.?\d+)\]' )
        fm = []
        for line in surveyinfo['FORCE_SNRMAX']:
            match = parse_snrmax.search( line )
            if match is None:
                raise ValueError( f"Failed to parse FORCE_SNRMAX line \"{line}\"" )
            fm.append( { 'snr': float(match.group('snr')),
                         'lam0': float(match.group('lam0')),
                         'lam1': float(match.group('lam1')) } )
        surveyinfo['FORCE_SNRMAX'] = fm

        parse_mjd_season = re.compile( r'^\s*(?P<mjd0>\d*\.?\d+)\s+(?P<mjd1>\d*\.?\d+)' )
        seasons = []
        for line in surveyinfo['MJD_SEASON']:
            match = parse_mjd_season.search( line )
            if match is None:
                raise ValueError( f"Failed to parse MJD_SEASON line {line}" )
            seasons.append( { 'season_mjd0': float( match.group('mjd0') ),
                              'season_mjd1': float( match.group('mjd1') ) } )
        surveyinfo['MJD_SEASON'] = seasons

        # I have a problem.
        # I know, I'll solve it with regular expressions!
        # Now I have two problems.
        parse_tier = re.compile( r'^\s*(?P<tier>[^/\s]+)(/\d+)?\s+(?P<ra>\d*\.?\d+)\s+(?P<dec>[\+\-]?\d*\.?\d+)\s+'
                                 r'(?P<bands>\S+)\s+\[\s*(?P<relarea>[^\]]+)\s*\]\s*'
                                 r'\[\s*(?P<dt_visit>[^\]]+)\s*\]\s+\[\s*(?P<z_snrmatch>[^\]])+\s*\]' )
        tiers = []

        texpose_prism = {}
        if 'TEXPOSE_PRISM' in surveyinfo.keys():
            for line in surveyinfo['TEXPOSE_PRISM']:
                match = re.search( '^\s*(?P<tier>[^\s]+)\s*\[(?P<texplist>[^\]]+)\]', line )
                if match is None:
                    s = f"Failed to parse TEXPOSE_PRISIM line {line}"
                    _logger.error( s )
                    raise ValueError( s )
                texpose_prism[ match.group('tier') ] =  [ int(i) for i in
                                                          re.split( '\s*,\s*', match.group('texplist') ) ]

        for line in surveyinfo['TIERS']:
            match = parse_tier.search( line )
            if match is None:
                raise ValueError( f"Failed to parse TIERS line \"{line}\"" )
            tiername = match.group('tier')
            tiers.append( { 'name': tiername,
                            'ra': float( match.group('ra') ),
                            'dec': float( match.group('dec') ),
                            'bands': [ i for i in match.group('bands') ],
                            'relarea': [ int(i) for i in re.split( r'\s*,\s*', match.group('relarea') ) ],
                            'dt_visit': [ float(i) for i in re.split( r'\s*,\s*', match.group('dt_visit') ) ],
                            'z_snrmatch': [ float(i) for i in re.split( r'\s*,\s*', match.group('z_snrmatch') ) ],
                            'texpose_prism': [] } )
            if tiername in texpose_prism.keys():
                tiers[-1]['texpose_prism'] = texpose_prism[tiername]

        analysisinfo[ 'muopt' ] = [  { 'name': 'standard', 'idsurvey_select': -99 } ]
        muparse = re.compile( r'^\s*(?P<muname>.*)\s+idsurvey_select=(?P<surveyid>\d+)' )
        hackremovethismuparse = re.compile( '^\s*idsurvey_select=(?P<surveyid>\d+)' )
        if 'MUOPT' in analysisinfo['BBC'].keys():
            for i, line in enumerate( analysisinfo['BBC']['MUOPT'] ):
                match = muparse.search( line )
                if match is None:
                    match = hackremovethismuparse.search( line )
                    muname = '(unnamed)'
                    if match is None:
                        raise ValueError( f"Failed to parse BBC.MUOPT line {line}" )
                else:
                    muname = match.group('muname')
                analysisinfo['muopt'].append( { 'name': muname,
                                                'idsurvey_select': int( match.group('surveyid') ) } )


        # Parse the prescale transient list

        analysisinfo[ 'prescales' ] = {}
        for scaleinfo in analysisinfo['SIM']['PRESCALE_TRANSIENT_LIST']:
            match = re.search('^ *([^/]+)/(.*)$', scaleinfo )
            if match is None:
                raise ValueError( f"Failed to parse prescale string {scaleinfo}" )
            analysisinfo[ 'prescales' ][ match.group(1) ] = float( match.group(2) )

        # WARNING HACK ALERT to deal with an inconsistency in snana output
        analysisinfo[ 'prescales' ][ 'IIP+IIL' ] = analysisinfo[ 'prescales' ][ 'IIL' ]

        return surveyinfo, instrinfo, analysisinfo, tiers, filemap


    def _read_simlib_doc( self, simlib_file, tiers ):
        surveyinfo = { 'tiers': {} }

        simlib_file = pathlib.Path( simlib_file )
        if not simlib_file.is_file():
            simlibgz = simlib_file.parent / f'{simlib_file.name}.gz'
            if not simlibgz.is_file():
                raise FileNotFoundError( f"Couldn't find {simlib_file}" )
            simlib_file = simlibgz

        lines = []
        if ( simlib_file.name[:-3] == '.gz' ):
            ifp = gzip.open( simlib_file, 'rt' )
        else:
            ifp = open( simlib_file, 'rt' )
        for line in ifp:
            if line[0:18] == "DOCUMENTATION_END:": break
            lines.append( line )
        ifp.close()
        simlib_doc_yaml = yaml.safe_load( '\n'.join( lines ) )['DOCUMENTATION']

        # Going to assume that things like FORCE_SNRMAX just match
        # Parse out the tier info

        for tieri, tierstr in enumerate( simlib_doc_yaml['TIER_INFO'] ):
            ( name, bands, ntile, nvisit, area,
              dt_visit, NLIBID, zSNRMATCH, OpenFrac ) = tierstr.split()
            name = re.sub( "/.*$", "", name )
            surveyinfo['tiers'][name] = {
                'bands': { i:{} for i in bands },
                'ntile': int( ntile ),
                'nvisit': int( nvisit ),
                'area': float( area ),
                'dt_visit': float( dt_visit ),
                'NLIBID': int( NLIBID ),
                'zSNRMATCH': float( zSNRMATCH ),
                'OpenFrac': float(OpenFrac) }
            exptimes = simlib_doc_yaml['TIER_EXPOSURE_TIMES'][tieri].split()
            exptimes[0] = re.sub( "/.*$", "", exptimes[0] )
            if exptimes[0] != name:
                raise ValueError( f"Tier mismatch in {simlib} at exposure times; found {exptimes[0]} "
                                  f"where expected {name}" )
            if exptimes[1] != bands:
                raise ValueError( f"Tier exposure time mismatch for {simlib}, tier {name}: "
                                  f"found {exptimes[1]} where expected {bands}" )
            for band in bands:
                if band not in RomanSurveySummary.known_filters:
                    raise ValueError( f"Unknown band {band} in {simlib}, tier {name}" )

            for band in RomanSurveySummary.known_filters:
                if band in bands:
                    bandi = bands.index( band )
                    surveyinfo['tiers'][name]['bands'][band] = float( exptimes[bandi+2] )
                else:
                    surveyinfo['tiers'][name]['bands'][band] = 0.

        return surveyinfo

    def _gen_zhists( self, dumpfilepath, gentypemap, prescales ):

        # TODO : scaling CC by 10 (or whatever)

        dumpfilepath = pathlib.Path( dumpfilepath )
        if dumpfilepath.is_file():
            # dumpdf = pandas.read_csv( dumpfilepath, delim_whitespace=True, comment='#', skip_blank_lines=True )
            dumpdf = pandas.read_csv( dumpfilepath, sep='\s+', comment='#', skip_blank_lines=True )
        else:
            dumpgzfilepath = dumpfilepath.parent / f"{dumpfilepath.name}.gz"
            if dumpgzfilepath.is_file():
                # dumpdf = pandas.read_csv( dumpgzfilepath, delim_whitespace=True, compression='gzip',
                #                           comment='#', skip_blank_lines=True )
                dumpdf = pandas.read_csv( dumpgzfilepath, sep='\s+', compression='gzip',
                                          comment='#', skip_blank_lines=True )
            else:
                raise FileNotFoundError( f"Can't find {dumpfilepath} or {dumpgzfilepath}" )


        fields = dumpdf['FIELD'].unique()
        types = dumpdf['GENTYPE'].unique()

        hist = { 'tier': [], 'gentype': [], 'zCMB': [], 'n': [] }
        snrmaxhist = { 'tier': [], 'gentype': [], 'zCMB': [], 'n': [] }
        snrmax2hist = { 'tier': [], 'gentype': [], 'zCMB': [], 'n': [] }
        snrmax3hist = { 'tier': [], 'gentype': [], 'zCMB': [], 'n': [] }
        for field in fields:
            fielddf = dumpdf[ dumpdf['FIELD'] == field ]
            for zlow in numpy.arange( 0., 3.1, 0.1 ):
                sne_at_z = fielddf[ ( fielddf['ZCMB'] >= zlow ) & ( fielddf['ZCMB'] < zlow + 0.1 ) ]
                for gentype, gentypestr in gentypemap.items():
                    prescale = 1.
                    if gentypestr in prescales.keys():
                        prescale = float( prescales[gentypestr] )
                    gentypesne = sne_at_z[ sne_at_z['GENTYPE'] == gentype ]
                    hist['tier'].append( field )
                    snrmaxhist['tier'].append( field )
                    snrmax2hist['tier'].append( field )
                    snrmax3hist['tier'].append( field )
                    hist['gentype'].append( gentype )
                    snrmaxhist['gentype'].append( gentype )
                    snrmax2hist['gentype'].append( gentype )
                    snrmax3hist['gentype'].append( gentype )
                    hist['zCMB'].append( zlow )
                    snrmaxhist['zCMB'].append( zlow )
                    snrmax2hist['zCMB'].append( zlow )
                    snrmax3hist['zCMB'].append( zlow )
                    hist['n'].append( prescale * len(gentypesne) )
                    snrmaxhist['n'].append( prescale * len( gentypesne[ gentypesne['SNRMAX'] > self.snrmaxcut ] ) )
                    snrmax2hist['n'].append( prescale * len( gentypesne[ gentypesne['SNRMAX2'] > self.snrmaxcut ] ) )
                    snrmax3hist['n'].append( prescale * len( gentypesne[ gentypesne['SNRMAX3'] > self.snrmaxcut ] ) )

        return hist, snrmaxhist, snrmax2hist, snrmax3hist

    def _get_snana_scratchdir( self, collection ):
        # Find the SNANA output scratch directory
        #  (We know the parent will be the same for all sims in a collection)

        if collection not in self.snana_scratchdir.keys():
            if self.snana_simdir is not None:
                self.snana_scratchdir[ collection ] = self.snana_simdir
            else:
                _logger.debug( f"Running snana.exe GETINFO {survey_version} to find "
                               f"SNANA data dir" )
                retries = 5
                while retries > 0:
                    try:
                        res = subprocess.run( [ 'snana.exe', 'GETINFO', survey_version ],
                                              capture_output=True, timeout=30 )
                        if len( res.stderr ) > 0:
                            raise RuntimeError( f"Failed to run snana.exe: {res.stderr}" )
                        retries = 0
                    except subprocess.TimeoutExpired as ex:
                        if retries > 0:
                            _logger.warning( f"snana.exe run timed out, trying again" )
                        else:
                            _logger.error( f"snana.exe run timed out repeatedly, dying" )
                            raise RuntimeError( f"snana.exe run timed out repeatedly, dying" )
                        retries -= 1
                for line in res.stdout.decode( "utf-8" ).split("\n"):
                    if line[0:12] == 'SNDATA_PATH:':
                        self.snana_scratchdir[collection] = pathlib.Path( line.split()[1] ).parent
                        break
                _logger.debug( f"...done running snana.exe" )

        if collection not in self.snana_scratchdir.keys():
            raise RuntimeError( f"Failed to find snana_scratchdir for {collection}" )

    def _read_dump( self, collection, survey_version, prescales ):

        self._get_snana_scratchdir( collection )
        sndatadir = self.snana_scratchdir[collection] / survey_version

        # Read the .README file to get the gentype to string type match

        lines = []
        with open( sndatadir / f'{survey_version}.README' ) as ifp:
            for line in ifp:
                if line[0:18] == 'DOCUMENTATION_END:' : break
                lines.append( line )
        readme_yaml = yaml.safe_load( '\n'.join( lines ) )

        gentypemap = {}
        for gentype, namestr in readme_yaml['DOCUMENTATION']['GENTYPE_TO_NAME'].items():
            cols = namestr.split()
            if cols[0] == 'Ia':
                gentypemap[ gentype ] = 'Ia'
            else:
                gentypemap[ gentype ] = cols[1]

        # Build the histograms

        dumpfilepath = sndatadir / f'{survey_version}.DUMP'
        ( zhist, snrmaxzhist,
          snrmax2zhist, snrmax3zhist ) = self._gen_zhists( dumpfilepath, gentypemap, prescales )

        return gentypemap, zhist, snrmaxzhist, snrmax2zhist, snrmax3zhist


    def _read_spec( self, collection, survey_version, tiers ):
        """Read spectrum information.

        Returns two dictionaries: spechists, spectiercids

        spechists:
          { 'zmin': float,       # z of left edge of low bin
            'zmax': float,       # z of ? edge of high bin (gratuitous)
            'deltaz': float,     # z bin width
            'tobsmin': float,    # t rel. max in obs. frame of left edge of low bin
            'tobsmax': float,
            'deltat': float,
            'mmin': float,       # magnitude of left edge of low bin
            'mmax': float,
            'deltam': float,
            'snrmin': float,     # S/N of left edge of low bin
            'snrmax': float,
            'deltasnr': float,
            'nspecstrategies': int,    # number of different spectrum strategies
            'spectrumhists':
                [ { tier: { 'texpose':   exposure time for this tier
                            <band_1>: { 'GENTYPE': int,
                                      'zbin': int,
                                      'tbin': int,
                                      'magbin': int,
                                      'snrbin': int,
                                      'n': int,         # of SNe in the relevant bins
                                    },
                            <band_1>_restframe { 'GENTYPE': int,
                                               'zbin': int,
                                               'tbin': int,
                                               'magbin': int,
                                               'snrbin': int,
                                               'n': int },
                            <band_2>: { ... },
                            <band_2>_restframe: { ... },
                            ... }
                   } ]
        }

        spectiercids:
          { tier: [ [ cid1, cid2, cid3 ] ] }

              If there are tiers 'SHALLOW' and 'DEEP', and three spectrum strategies, then
              spectiercids['DEEP'][1] is a list of all cids that were taken as part of the
              second spectrum strategy of objects in the 'DEEP' subset.


        """

        # This one tries to make later summing of histogram seasier.
        # It doesn't fully finish it.
        #
        # Within a tier/texpose, it bins by gentype, z, mag, snr, and t, and sums counts within those bins.

        self._get_snana_scratchdir( collection )
        sndatadir = self.snana_scratchdir[collection] / survey_version

        specfile = sndatadir / f'{survey_version}.SPEC'
        if not specfile.is_file():
            specfile = sndatadir / f'{survey_version}.SPEC.gz'
            if not specfile.is_file():
                _logger.error( f"Can't find {specfile} (w/ or w/o .gz), returning empty dict for spectrum info" )
                return {}

        _logger.debug( f"Parsing {specfile}" )
        # specdf = pandas.read_csv( specfile, delim_whitespace=True, comment='#', skip_blank_lines=True, compression='infer' )
        specdf = pandas.read_csv( specfile, sep='\s+', comment='#', skip_blank_lines=True, compression='infer' )

        zmin = 0.
        zmax = 3.
        deltaz = 0.2
        mmin = 20.
        mmax = 28.
        deltam = 1.
        snrmin = 0.
        snrmax = 20.
        deltasnr = 1.
        tobsmin = -33.
        tobsmax = 243.
        deltat = 10.

        hist = { 'zmin': zmin,
                 'zmax': zmax,
                 'deltaz': deltaz,
                 'tobsmin': tobsmin,
                 'tobsmax': tobsmax,
                 'deltat': deltat,
                 'mmin': mmin,
                 'mmax': mmax,
                 'deltam': deltam,
                 'snrmin': snrmin,
                 'snrmax': snrmax,
                 'deltasnr': deltasnr
                }

        spectiers = specdf['FIELD'].unique()
        if set( spectiers ) != set( [ t['name'] for t in tiers ] ):
            _logger.error( f"Spectroscopic tiers {spectiers} don't match photometric {tiers.keys()}" )
        ntexpose = -99
        for info in tiers:
            tier = info['name']
            if not isinstance( info['texpose_prism'], list ):
                _logger.error( f"texpose_prism not a list for tier {tier}!  Not returning spectrum info." )
                raise RuntimeError( f"texpose_prism not a list for tier {tier}!" )
                # return {}
            if ntexpose < 0:
                ntexpose = len( info['texpose_prism'] )
            elif len( info['texpose_prism'] ) != ntexpose:
                raise RuntimeError( f"Inconsistent numbers texpose_prism for {collection} {survey_version}" )

        hist[ 'nspecstrategies' ] = ntexpose

        specstrat = []
        for strati in range(ntexpose):
            stratdict = {}

            for tier in specdf['FIELD'].unique():
                _logger.debug( f"Spectrum strategy {strati}, tier {tier}" )
                tiersentry = None
                for ent in tiers:
                    if ent['name'] == tier:
                        tiersentry = ent
                        break
                else:
                    raise RuntimeError( f"Tier {tier} in specdf is not in tiers." )

                stratdict[tier] = {}
                stratdict[tier]['texpose'] = tiersentry['texpose_prism'][strati]

                tierdf = specdf[ ( specdf['FIELD'] == tier )
                                 & ( specdf['TEXPOSE'] == tiersentry['texpose_prism'][strati] )
                                ].copy()

                tierdf['zbin'] = ( ( tierdf['zHEL'] - zmin ) / deltaz ).apply( int )
                tierdf['tbin'] = ( ( tierdf['TOBS'] - tobsmin ) / deltat ).apply( int )
                tierdf['trestbin'] = ( ( tierdf['TOBS'] / ( 1 + tierdf['zHEL'] ) - tobsmin ) / deltat ).apply( int )

                for band in [ 'Z', 'Y', 'J', 'H' ]:
                    magstr = f'{band}_mag_syn'
                    errstr = f'{band}_magerr_syn'

                    banddf = tierdf[ [ 'GENTYPE', 'zbin', 'tbin', 'trestbin', magstr, errstr ] ].copy()
                    banddf['magbin'] = ( ( banddf[magstr] - mmin ) / deltam ).apply(int)
                    banddf['snr'] = 2.5 / ( banddf[errstr] * 2.30258509299405 )
                    banddf.loc[ banddf[errstr] <= 0., 'snr' ] = 0.
                    banddf.loc[ banddf['snr'] > 20., 'snr' ] = 20.
                    banddf['snrbin'] = ( ( banddf['snr'] - snrmin ) / deltasnr ).apply(int)

                    obsdf = banddf.sort_values( [ 'GENTYPE', 'zbin', 'tbin', 'magbin', 'snrbin' ] )
                    obsdf = obsdf.groupby( [ 'GENTYPE', 'zbin', 'tbin', 'magbin', 'snrbin' ] ).count()['snr']
                    obsdf = obsdf.to_frame().reset_index()
                    obsdf.rename( { 'snr': 'n' }, axis='columns', inplace=True )

                    restdf = banddf.sort_values( [ 'GENTYPE', 'zbin', 'trestbin', 'magbin', 'snrbin' ] )
                    restdf = restdf.groupby( [ 'GENTYPE', 'zbin', 'trestbin', 'magbin', 'snrbin' ] ).count()['snr']
                    restdf = restdf.to_frame().reset_index()
                    restdf.rename( { 'snr': 'n' }, axis='columns', inplace=True )

                    stratdict[tier][band] = obsdf.to_dict( 'list' )
                    stratdict[tier][f'{band}_restframe'] = restdf.to_dict( 'list' )

            specstrat.append( stratdict )

        hist[ 'spectrumhists' ] = specstrat

        spectiercids = {}
        for tier in specdf['FIELD'].unique():
            tiersentry = None
            for ent in tiers:
                if ent['name'] == tier:
                    tiersentry = ent
                    break
            else:
                # This should never happen; exception would have been raised before.
                raise RuntimeError( f"Tier {tier} in specdf is not in tiers." )

            spectiercids[ tier ] = []
            for i, specstrat in enumerate( range(ntexpose) ):
                # I'm going to be doing a float comparison for texpose, which is scary.
                #   However, I expect these floating point numbers to all be integers,
                #   and 32-bit floats can perfectly represent integers up to 2^23-1,
                #   or 8388607, and no exposure time will ever be that long.
                texpose = tiersentry['texpose_prism'][i]
                # Explicitly convert to int just in case it's a string,
                #   which I've seen for ids in SNANA sometimes
                try:
                    spectiercids[ tier ].append( [ int(j) for j in
                                                   list( specdf[ ( specdf['FIELD'] == tier ) &
                                                                 ( specdf['TEXPOSE'] == texpose ) ]['CID']
                                                         .unique() ) ] )
                except Exception as ex:
                    import pdb; pdb.set_trace()
                    pass


        return hist, spectiercids


    def read_files( self, collection, snana_outdir, regen=False, savecache=True, clobber=False ):
        """Load information from a single survey collection.

        Parameters
        ==========
        collection : str
            The name that will identify this collection in the objects
            collections dict.

        snana_outdir : str or Path
            The output directory for SNANA.  The following files must exist here:
              * a single INP_ file
              * a single OUTPUT1* directory
              * MERGE.LOG in the OUTPUT1* directory
              * ANALYSIS_INSTRUCTIONS.README
              * A *.SIMLIB file for each row in the ANALYSIS_INSTRUCTIONS.README

        regen : bool, default False
            If False, will try to read the necessary JSON files from the
            outdir passed to the object at construction, rather than
            trying to rebuild them from the SNANA outputs.  If True,
            will ignore existing JSON files.

        savecache : bool, default True
            If the information is rebuilt from the SNANA outputs, save
            JSON files named {collection}_{structure}.json with either
            dicts or pandas DataFrames.

        clobber : bool, default False
           This has nothing to do with files; set regen=True to force
           overwriting existing JSON files.  This has to do with
           internal memeory; if we try to read a collection we've
           already read, raise an error unless this is True.

        Will add to self.collections with key collection and value:
           { 'surveyinfo': dict with keys OUTDIR, FORCE_TEXPOSE_LIST, FORCE_SIMGEN_INPUT_FILE,
                                          FORCE_NGEN, NLIBID_TOT, TIME_SUM_OBS, TEXPOSE_MIN,
                                          RANDOM_REJECT_OBS,
                                'MJD_SEASON': [ { 'season_mjd0': mjd0, 'season_mjd1': mjd1 }, ... ],
                                'FORCE_SNRMAX': [ { 'snr': snr, 'lam0': lam0, 'lam1': lam1 }, ... ]
                                'FoM': [ { 'muopt_dex': int, 'muopt': str, 'FoM_stat': float }, ... ]
             'tiers': [ { 'name': tier name,
                             'ra': ra,
                             'dec': dec,
                             'bands': list of letters,
                             'relarea': list of of ints,
                             'dt_visit': list of floats,
                             'z_snrmatch': list of floats,
                             'texpose_prism': list of ints
                          } ]
             'instrinfo': dict of stuff,
             'analysisinfo': dict with a bunch of keys including
                           'muopt': [ { 'name': str, 'idsurvey_select': int } ]
             'surveys': { name : { 'tiers': { tier: { (several other keys),
                                                      'bands': { letter: exptime, ... },
                                                      'ntile': int,
                                                      'nvisit': int,
                                                      'area': float,
                                                      'dt_visit': float,
                                                      'NLIBID': int,
                                                      'zSNRMATCH': float,
                                                      'OpenFrac': float,
                                                    }
                                            }
                                   'zhist': { 'tier': [...], 'gentype': [...], 'zCMB': [...], 'n': [...] },
                                   'snrmaxzhist': { <same structure as zhist> },
                                   'snrmaxz2hist': { <same structure as zhist> },
                                   'snrmaxz3hist': { <same structure as zhist> },
                                   'spechists': { <see _read_spec> },
                                   'gentypemap' : { gentype: name, ... },
                                   'long_survey_version' : <str>,
                                   'muopt': [ { 'name': str,
                                                'idsurvey_select': int,
                                                 (bunch of cosmology keys, including 'FoM_stat') }
                                            ]

                         } },
             'spectiercids': { survey_name: { see _read_spec} },
           }

        The zhist thingies are set up to be easy to convert to a Pandas dataframe.

        """
        if ( not clobber ) and ( collection in self.collections.keys() ):
            raise RuntimeError( f"Not clobbering collection {collection}" )

        # TODO read cache

        snana_outdir = pathlib.Path( snana_outdir ).resolve()

        # Read the INP, ANALYSIS_INSTRUCTIONS.README, and OUTPUT1 files

        surveyinfo, instrinfo, analysisinfo, tiers, filemap = self._read_inp_files( snana_outdir )

        # Make sure an assumption I'm going to make is true, that the
        # number of areas, dt_visits, and zSNRMATCHes are the same for all tiers.

        surveyparamlens = {
            'relarea': None,
            'dt_visit': None,
            'z_snrmatch': None }
        for tier in tiers:
            for var in surveyparamlens.keys():
                if surveyparamlens[var] is None:
                    surveyparamlens[var] = len( tier[var] )
                elif surveyparamlens[var] != len( tier[var] ):
                    raise ValueError( f"The number of {var} is not the same for all tiers." )

        # Start building the individual surveys

        surveys = {}
        spectiercids = {}
        for ai, relarea in enumerate( tiers[0]['relarea'] ):
            for ti, dt_visit in enumerate( tiers[0]['dt_visit'] ):
                for zi, z_snrmatch in enumerate( tiers[0]['z_snrmatch'] ):
                    subdf = filemap.xs( ( ai, ti, zi ), level=( 'i_AREA', 'i_TEXPOSE', 'i_zSNRMAX' ) )
                    if len(subdf) != 1:
                        _logger.error( "Bad things have happened." )
                        import pdb; pdb.set_trace()
                        pass
                    survey_version = subdf.iloc[0].VERSION

                    # WARNING filename assumptions
                    if survey_version[0:len(collection)+12] == f'ROMAN_{collection}_DATA-':
                        short_survey_version = f'{collection} {survey_version[len(collection)+12:]}'
                    else:
                        short_survey_version = survey_version
                    simlib_file = snana_outdir / subdf.iloc[0].SIMLIB_FILE

                    _logger.debug( f"Processing {survey_version} ({simlib_file})" )

                    try:
                        surveys[short_survey_version] = self._read_simlib_doc( simlib_file, tiers )
                        ( gentypemap, zhist, snrmaxzhist,
                          snrmax2zhist, snrmax3zhist ) = self._read_dump( collection, survey_version,
                                                                          analysisinfo['prescales'] )
                        surveys[short_survey_version]['gentypemap'] = gentypemap
                        surveys[short_survey_version]['zhist'] = zhist
                        surveys[short_survey_version]['snrmaxzhist'] = snrmaxzhist
                        surveys[short_survey_version]['snrmax2zhist'] = snrmax2zhist
                        surveys[short_survey_version]['snrmax3zhist'] = snrmax3zhist
                        surveys[short_survey_version]['long_survey_version'] = survey_version
                        spechists, this_spectiercids = self._read_spec( collection, survey_version, tiers )
                        surveys[short_survey_version]['spechists'] = spechists
                        spectiercids[short_survey_version] = this_spectiercids
                    except Exception as ex:
                        strio = io.StringIO()
                        strio.write( f"Failed to get survey info for {short_survey_version}; Exception: " )
                        traceback.print_exc( file=strio )
                        _logger.error( strio.getvalue() )
                        if short_survey_version in surveys.keys():
                            del surveys[ short_survey_version ]

        # Get the cosmology and figure of merit from the BBC files

        _logger.debug( "Reading BBC_SUMMARY_wfit0.FITRES" )
        files = [ f for f in snana_outdir.glob( "OUTPUT3*" ) ]
        if len(files) != 1:
            raise RuntimeError( f"There are {len(files)} OUTPUT3* files in {snana_outdir.name}, expected 1" )
        output3file = files[0] / 'BBC_SUMMARY_wfit0.FITRES'
        # bbcsummary = pandas.read_csv( output3file, delim_whitespace=True, comment='#' )
        bbcsummary = pandas.read_csv( output3file, sep='\s+', comment='#' )
        if len( bbcsummary['FITOPT'].unique() ) > 1:
            raise ValueError( f"Assumption failure: there is more than one FITOPT!" )
        if bbcsummary['FITOPT'].unique()[0] != 0:
            raise ValueError( f"Assumption failure: FITOPT is not 0" )

        muopts = list( bbcsummary['MUOPT'].unique() )
        muopts.sort()
        if ( muopts != [ i for i in range(len(analysisinfo['muopt'])) ] ):
            raise ValueError( f"muopts in bbcsummary for {sndatabasename} not what was expected!" )

        for skey, sval in surveys.items():
            survey = sval['long_survey_version']
            sval['muopt'] = []
            for muopt in muopts:
                thisbbc = bbcsummary[ ( bbcsummary['MUOPT'] == muopt ) & ( bbcsummary['VERSION'] == survey ) ]
                if len( thisbbc ) != 1:
                    raise ValueError( f"Found {len(thisbbc)} lines in BBC file for {survey}, muopt={muopt}" )
                bbcdict = thisbbc.iloc[0].to_dict()
                bbcdict['FoM_stat'] = bbcdict['FoM']
                del bbcdict['FoM']
                sval['muopt'].append( bbcdict )

        # Done

        self.collections[ collection ] = {
            'surveyinfo': surveyinfo,
            'tiers': tiers,
            'instrinfo': instrinfo,
            'analysisinfo': analysisinfo,
            'surveys': surveys,
            'spectiercids': spectiercids
        }

        # Save to cache dir

        if savecache:
            for attr in ( 'surveyinfo', 'tiers', 'instrinfo', 'analysisinfo', 'surveys', 'spectiercids' ):
                with open( self.outdir / f'{collection}_{attr}.json', 'w' ) as ofp:
                    json.dump( self.collections[collection][attr], ofp, cls=NumpyEncoder )

    def process_searchdir( self ):
        if self.searchdir is None:
            raise ValueError( "Can't process_searchdir : no searchdir was given to RomanSurveySummary constructor." )

        outputparse = re.compile( "^output_?(.*)$" )

        _logger.info( f"Looking for collections in {self.searchdir}" )
        for direc in self.searchdir.glob( "output*" ):
            match = outputparse.search( direc.name )
            if match is None:
                raise RuntimeError( f"Failed to parse {direc.name} for output_?(.*)" )
            surveyname = match.group(1)

            _logger.info( f"Working on collection {surveyname}" )
            self.read_files( surveyname, direc )

        _logger.info( f"All done with collecitons in {self.searchdir}" )


# ======================================================================

def main():
    parser = argparse.ArgumentParser( 'parse_snana',
                                      description="do things",
                                      formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    parser.add_argument( "-v", "--verbose", action='store_true', default=False, help="Show debug info" )
    parser.add_argument( "-o", "--outdir", default=".", help="Output directory for pkl files" )
    parser.add_argument( "-p", "--campaign-pipeline-dir",
                         help=( "The SNANA campaign directory; under this directory, each subdirectory "
                                "named output_* is a single collection within the campaign, has an "
                                "ANALYSIS_INSTRUCTIONS.README file, and OUTPUT[123]* files" ) )
    parser.add_argument( "-s", "--snana-simdir",
                         help=( "The SNANA sim directory; this holds all of the SNANA SIMS for the "
                                "campaign in --campaign-pipeline-dir.  In this directory are "
                                "subdirectories corresponding to all of the versions found in all of the"
                                ".../OUTPUT2*/MERGE.LOG files under campaign-pipeline-dir." ) )
    args = parser.parse_args()

    if args.verbose:
        _logger.setLevel( logging.DEBUG )

    ss = RomanSurveySummary( args.outdir, searchdir=args.campaign_pipeline_dir, snana_simdir=args.snana_simdir )
    ss.process_searchdir()

    # for snanadir in args.snana_outdirs:
    #     inpfile = pathlib.Path( snanadir )
    #     if inpfile.name[0:7] == 'output_':
    #         survey_name = inpfile.name[7:]
    #     else:
    #         survey_name = inpfile
    #     _logger.info( f"Reading survey {survey_name} from {inpfile}..." )
    #     ss.read_files( survey_name, inpfile  )

    # _logger.info( f"Done." )


if __name__ == "__main__":
    main()
