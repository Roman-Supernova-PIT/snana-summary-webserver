import sys
import pathlib
import re
import gzip
import yaml
import json
import subprocess
import logging
import pickle
import argparse
import numpy
import pandas

_logger = logging.getLogger("main")
_logout = logging.StreamHandler( sys.stderr )
_logger.addHandler( _logout )
_formatter = logging.Formatter( f'[%(asctime)s - %(levelname)s] - %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S' )
_logout.setFormatter( _formatter )
_logger.setLevel( logging.INFO )

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

    def __init__( self, outdir, searchdir=None, snrmaxcut=5. ):
        self.outdir = pathlib.Path( outdir )
        self.collections = {}
        self.snana_scratchdir = {}
        self.snrmaxcut = snrmaxcut
        if searchdir is not None:
            self.read_all_outputs_in( searchdir )

    def _read_inp_files( self, snana_outdir ):
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

        filemap = pandas.read_csv( analysis_instr, delim_whitespace=True, comment='#', skip_blank_lines=True )
        filemap.set_index( [ 'i_AREA', 'i_TEXPOSE', 'i_zSNRMAX' ], inplace=True )

        # Read the INP file

        with open( inputfile ) as ifp:
            blob = yaml.safe_load( ifp.read() )

        surveyinfo = blob['CONFIG_SURVEY']
        instrinfo = blob['CONFIG_INSTRUMENT']
        analysisinfo = blob['CONFIG_ANALYSIS_PREP']

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
        for line in surveyinfo['TIERS']:
            match = parse_tier.search( line )
            if match is None:
                raise ValueError( f"Failed to parse TIERS line \"{line}\"" )
            tiers.append( { 'name': match.group('tier'),
                            'ra': float( match.group('ra') ),
                            'dec': float( match.group('dec') ),
                            'bands': [ i for i in match.group('bands') ],
                            'relarea': [ int(i) for i in re.split( r'\s*,\s*', match.group('relarea') ) ],
                            'dt_visit': [ float(i) for i in re.split( r'\s*,\s*', match.group('dt_visit') ) ],
                            'z_snrmatch': [ float(i) for i in re.split( r'\s*,\s*', match.group('z_snrmatch') ) ] } )

        analysisinfo[ 'muopt' ] = [  { 'name': 'standard', 'idsurvey_select': -99 } ]
        muparse = re.compile( r'^\s*(?P<muname>.*)\s+idsurvey_select=(?P<surveyid>\d+)' )
        hackremovethismuparse = re.compile( '^\s*idsurvey_select=(?P<surveyid>\d+)' )
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

    def _gen_zhists( self, dumpfilepath, gentypes ):

        # TODO : scaling CC by 10 (or whatever)

        dumpfilepath = pathlib.Path( dumpfilepath )
        if dumpfilepath.is_file():
            dumpdf = pandas.read_csv( dumpfilepath, delim_whitespace=True, comment='#', skip_blank_lines=True )
        else:
            dumpgzfilepath = dumpfilepath.parent / f"{dumpfilepath.name}.gz"
            if dumpgzfilepath.is_file():
                dumpdf = pandas.read_csv( dumpgzfilepath, delim_whitespace=True, compression='gzip',
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
                for gentype in gentypes:
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
                    hist['n'].append( len(gentypesne) )
                    snrmaxhist['n'].append( len( gentypesne[ gentypesne['SNRMAX'] > self.snrmaxcut ] ) )
                    snrmax2hist['n'].append( len( gentypesne[ gentypesne['SNRMAX2'] > self.snrmaxcut ] ) )
                    snrmax3hist['n'].append( len( gentypesne[ gentypesne['SNRMAX3'] > self.snrmaxcut ] ) )

        return hist, snrmaxhist, snrmax2hist, snrmax3hist


    def _read_dump( self, collection, survey_version ):

        # Find the SNANA output scratch directory
        #  (We know the parent will be the same for all sims)

        if collection not in self.snana_scratchdir.keys():
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
          snrmax2zhist, snrmax3zhist ) = self._gen_zhists( dumpfilepath, gentypemap.keys() )

        return gentypemap, zhist, snrmaxzhist, snrmax2zhist, snrmax3zhist


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
             'tiers': dict { 'name': tier name, 'ra': ra, 'dec': dec,
                             'bands': array of letters,
                             'relarea': array of ints,
                             'dt_visit': array of floats,
                             'z_snrmatc': array of floats,
                           }
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
                                   'zhist': { 'tier': [...], 'gentype': [...], 'zCMB': [...], 'n': [...] }
                                   'snrmaxzhist': <same structure>
                                   'snrmaxz2hist': <same structure>
                                   'snrmaxz3hist': <same structure> } },
                                   'gentypemap' : { gentype: name, ... }
                                   'muopt': [ { 'name': str,
                                                'idsurvey_select': int,
                                                 (bunch of cosmology keys, including 'FoM_stat') }
                                            ]

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
        for ai, relarea in enumerate( tiers[0]['relarea'] ):
            for ti, dt_visit in enumerate( tiers[0]['dt_visit'] ):
                for zi, z_snrmatch in enumerate( tiers[0]['z_snrmatch'] ):
                    subdf = filemap.xs( [ ai, ti, zi ], level=['i_AREA', 'i_TEXPOSE', 'i_zSNRMAX' ] )
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

                    surveys[short_survey_version] = self._read_simlib_doc( simlib_file, tiers )
                    ( gentypemap, zhist, snrmaxzhist,
                      snrmax2zhist, snrmax3zhist ) = self._read_dump( collection, survey_version )
                    surveys[short_survey_version]['gentypemap'] = gentypemap
                    surveys[short_survey_version]['zhist'] = zhist
                    surveys[short_survey_version]['snrmaxzhist'] = snrmaxzhist
                    surveys[short_survey_version]['snrmax2zhist'] = snrmax2zhist
                    surveys[short_survey_version]['snrmax3zhist'] = snrmax3zhist
                    surveys[short_survey_version]['long_survey_version'] = survey_version

        # Get the cosmology and figure of merit from the BBC files

        _logger.debug( "Reading BBC_SUMMARY_wfit.FITRES" )
        files = [ f for f in snana_outdir.glob( "OUTPUT3*" ) ]
        if len(files) != 1:
            raise RuntimeError( f"There are {len(files)} OUTPUT3* files in {snana_outdir.name}, expected 1" )
        output3file = files[0] / 'BBC_SUMMARY_wfit.FITRES'
        bbcsummary = pandas.read_csv( output3file, delim_whitespace=True, comment='#' )
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
            'surveys': surveys }

        # Save to cache dir

        if savecache:
            for attr in ( 'surveyinfo', 'tiers', 'instrinfo', 'analysisinfo', 'surveys' ):
                with open( self.outdir / f'{collection}_{attr}.json', 'w' ) as ofp:
                    json.dump( self.collections[collection][attr], ofp, cls=NumpyEncoder )

    def read_all_outputs_in( self, searchdir ):
        raise NotImplementedError( "read_all_outputs_in() not implemented" )

# ======================================================================

def main():
    parser = argparse.ArgumentParser( 'parse_snana',
                                      description="do things",
                                      formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    parser.add_argument( "-v", "--verbose", action='store_true', default=False, help="Show debug info" )
    parser.add_argument( "-o", "--outdir", default=".", help="Output directory for pkl files" )
    parser.add_argument( "-s", "--snana_outdirs", nargs='+', help="SNANA output directories to read" )
    args = parser.parse_args()

    if args.verbose:
        _logger.setLevel( logging.DEBUG )

    ss = RomanSurveySummary( args.outdir )
    for snanadir in args.snana_outdirs:
        inpfile = pathlib.Path( snanadir )
        if inpfile.name[0:7] == 'output_':
            survey_name = inpfile.name[7:]
        else:
            survey_name = inpfile
        _logger.info( f"Reading survey {survey_name} from {inpfile}..." )
        ss.read_files( survey_name, inpfile  )

    _logger.info( f"Done." )


if __name__ == "__main__":
    main()
