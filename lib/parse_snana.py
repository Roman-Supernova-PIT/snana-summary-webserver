import sys
import pathlib
import re
import gzip
import yaml
import numpy
import pandas

class RomanSurveySummary:
    known_filters = ['R', 'Z', 'Y', 'J', 'H', 'F', 'K']
    surveynameparse = re.compile( '^(.*)\.SIMLIB(\.gz)?' )
    
    def __init__( self, outdir, indirs=[] ):
        self.outdir = pathlib.Path( outdir )
        self.collections = {}
        for d in indirs:
            direc = pathlib.Path( d )
            self.read_files( d.name, indir=direc )

    def get_survey_info( self, input_file, printing=True ):
        input_file = pathlib.Path( input_file )
        
        #Survey name
        match = RomanSurveySummary.surveynameparse.search( input_file.name )
        if match is None:
            raise RuntimeError( f"Failed to parse {input_file.name} for .*\\.SIMLIB(\\.gz)" )
        surveyname = match.group(1)

        ifp = None
        
        #Read the documentation from the SIMLIB file
        lines = []
        if ( input_file.name[:-3] == '.gz' ):
            ifp = gzip.open( input_file, 'rt' )
        else:
            ifp = open( input_file, 'rt' )
        for line in ifp:
            if line[0:18] == "DOCUMENTATION_END:": break
            lines.append( line )
        ifp.close()
        config_yaml = yaml.safe_load( '\n'.join( lines ) )

        # Build the return value in obs_dict

        doc = config_yaml['DOCUMENTATION']

        objs_dict = { 'TIME_SUM_OBS': float( doc['TIME_SUM_OBS'] ),
                      'TIME_SUM_SEASON': float( doc['TIME_SUM_SEASON'] ),
                      'RANDOM_REJECT_OBS': float( doc['RANDOM_REJECT_OBS'] ),
                      'TIME_SLEW': float( doc['TIME_SLEW'] ) }

        objs_dict['FORCE_SNRMAX'] = []

        forcesnrre = re.compile( '^\s*(\d+)\s*\[\s*(\d+),\s*(\d+)\s*\]$' )
        for force_snrmax in doc['FORCE_SNRMAX']:
            match = forcesnrre.search( force_snrmax )
            if match is None:
                raise ValueError( f"Failed to parse \"{force_snrmax}\" as a FORCE_SNRMAX entry" );
            objs_dict['FORCE_SNRMAX'].append( { 'snr': match.group(1),
                                                'lam0': match.group(2),
                                                'lam1': match.group(3) } )

        objs_dict['TIERS'] = {}
        for tierinfo, tierexp in zip( doc['TIER_INFO'],
                                      doc['TIER_EXPOSURE_TIMES'] ):
            name = None
            for kw, val in zip ( ['name', 'bands', 'ntile', 'nvisit', 'Area', 'dt_visit',
                                  'NLIBID', 'zSNRMATCH', 'OpenFrac' ],
                                 tierinfo.split() ):
                if kw == 'name':
                    name = val
                    objs_dict['TIERS'][name] = {}
                elif kw == "bands":
                    pass
                elif name is None:
                    raise RuntimeError( "No name" )
                else:
                    objs_dict['TIERS'][name][kw] = float( val )
            if name is None:
                raise RuntimeError( "No name" )

            exptimeinfo = tierexp.split()
            if exptimeinfo[0] != name:
                raise RuntimeError( f"Exposure time name {exptimeinfo[0]} doesn't match tier name {name}" )
            bands = exptimeinfo[1]
            exptimes = exptimeinfo[2:]
            if len(bands) != len(exptimes):
                raise RuntimeError( f"Number of bands {len(bands)} != len(exptimes)={len(exptimes)}" )
            objs_dict['TIERS'][name]['EXPTIME'] = { k: float(v) for k, v in zip( bands, exptimes ) }
            for filt in RomanSurveySummary.known_filters:
                if filt not in objs_dict['TIERS'][name]['EXPTIME']:
                    objs_dict['TIERS'][name]['EXPTIME'][filt] = 0.
            for filt in objs_dict['TIERS'][name]['EXPTIME'].keys():
                if filt not in RomanSurveySummary.known_filters:
                    raise RuntimeError( f"Unknown filter {filt}" )
            
        return objs_dict, surveyname
    

    def read_files( self, collection, indir=None, regen=False, savecache=True ):
        if not regen:
            mustredo = False
            for attr in ( 'infodf', 'tierdf', 'obsdf', 'zhistdf', 'cosmodf' ):
                if not ( self.outdir / f'{collection}_{attr}.pkl' ).is_file():
                    sys.stderr.write( f"Didn't find {self.outdir}/{collection}_{attr}.pkl, regenerating all pkls.\n" )
                    mustredo = True
                    break
            if not mustredo:
                self.collections[collection] = {}
                for attr in ( 'infodf', 'snrmaxdf', 'tierdf', 'obsdf', 'zhistdf', 'cosmodf' ):
                    self.collections[attr] = pandas.read_pickle( self.outdir / f"{collection}_{attr}.pkl" ) )
                return

        infodf = None
        snrmaxdf = None
        tierdf = None
        obsdf = None
        zhistdf = None
        cosmodf = None

        if indir is None:
            indir = collection
        
        simlibs = list( indir.glob( "*.SIMLIB" ) )
        simlibsgz = list( indir.glob( "*.SIMLIB.gz" ) )
        for simlib in simlibsgz:
            nogz = simlib.parent / simlib.name[:-3]
            if nogz not in simlibs:
                simlibs.append( simlib )
        
        for simlib in simlibs:
            outdict, name = self.get_survey_info( simlib )

            # Make infodf based on all the fields that are the same one SIMLIB
            
            tmpdf = pandas.DataFrame( { k:[outdict[k]] for k in outdict.keys()
                                        if k not in [ 'TIERS', 'FORCE_SNRMAX' ] } )
            tmpdf['NAME'] = name
            if infodf is None:
                infodf = tmpdf
            else:
                infodf = pandas.concat( [ infodf, tmpdf ], axis=0 )

            # Make snrmaxdf to hold the FORCE_SNRMAX entries for the SIMLIB
                
            for i, snrinfo in enumerate( outdict['FORCE_SNRMAX'] ):
                tmpdf = pandas.DataFrame( [ snrinfo ] )
                tmpdf['NAME'] = name
                tmpdf['ORDINAL'] = i
                if snrmaxdf is None:
                    snrmaxdf = tmpdf
                else:
                    snrmaxdf = pandas.concat( [ snrmaxdf, tmpdf ], axis=0 )

            # Make tierdf to hold general information about tiers (everything but filter/exptime)
            # and obsdf to hold the filter/exptime pairs
                    
            curtierdf = None
            for tier, tierinfo in outdict['TIERS'].items():
                # I do not understand why above I had to do k:[outdict[k]], but here I do k:tierinfo[k]
                # Pandas is very mysterious
                tmpdf = pandas.DataFrame( [ { k:tierinfo[k] for k in tierinfo.keys() if k != 'EXPTIME' } ] )
                tmpdf[ 'NAME' ] = name
                tmpdf[ 'TIER' ] = tier
                if tierdf is None:
                    tierdf = tmpdf
                else:
                    tierdf = pandas.concat( [ tierdf, tmpdf ], axis=0)
                if curtierdf is None:
                    curtierdf = tmpdf
                else:
                    curtierdf = pandas.concat( [ curtierdf, tmpdf ], axis=0 )

                tmpdf = pandas.DataFrame( [ { 'FILTER': filt, 'EXPTIME': tierinfo['EXPTIME'][filt] }
                                            for filt in tierinfo['EXPTIME'].keys() ] )
                tmpdf[ 'NAME' ] = name
                tmpdf[ 'TIER' ] = tier
                tmpdf['FILTER'] = pandas.Categorical( tmpdf['FILTER'], RomanSurveySummary.known_filters )

                if obsdf is None:
                    obsdf = tmpdf
                else:
                    obsdf = pandas.concat( [ obsdf, tmpdf ], axis=0 )

            # (This is needed for the next df)
            curtierdf.set_index( [ 'NAME', 'TIER' ], inplace=True )

            # Make zhistdf holding a histogram of number of SNe Ia as a function of z
            
            for mu in [ 0, 1 ]:
                fname = [ i for i in ( indir / "DATA_FILES" ).glob( f"*{name}/FITOPT000_MUOPT{mu:03d}.FITRES" ) ]
                if len(fname) > 1:
                    raise RuntimeError( "Too many matches!" )
                if len( fname ) == 0:
                    fname = [ i for i in
                              ( indir / "DATA_FILES" ).glob( f"*{name}/FITOPT000_MUOPT{mu:03d}.FITRES.gz" ) ]
                if len( fname ) == 0:
                    raise FileNotFoundError( f"Couldn't find a FITRES for {name}" )
                fname = fname[0]
                tmpdf = pandas.read_csv( fname, comment='#', sep='\s+' )
                
                knownfields = tmpdf['FIELD'].unique()
                # sys.stderr.write( f"knownfields: {knownfields}\n" )
                for field in knownfields:
                    found = False
                    for t in curtierdf.xs( name, level='NAME' ).index.unique( 'TIER' ).values:
                        if t[0:len(field)] == field:
                            if found:
                                raise ValueError( f"Found {t} more than once" )
                            tmpdf.loc[ tmpdf['FIELD'] == field, 'FIELD'] = t
                            found = True
                    if not found:
                        sys.stderr.write( f"WARNING: didn't find {field} for {name}, mu={mu}; skipping\n" )
                        tmpdf = tmpdf[ tmpdf['FIELD'] != field ]

                tmpsurveyzdict = { 'NAME': [], 'FIELD': [], 'MU': [], 'z': [], 'n': [] }
                for field in tmpdf['FIELD'].unique():
                    hist, bins = numpy.histogram( tmpdf.loc[ tmpdf['FIELD'] == field, 'zHD' ],
                                                  bins=numpy.arange( 0, 3.2, 0.1 ) )
                    for i in range(len(hist)):
                        tmpsurveyzdict['NAME'].append( name )
                        tmpsurveyzdict['FIELD'].append( field )
                        tmpsurveyzdict['MU'].append( mu )
                        tmpsurveyzdict['zHD'].append( bins[i] )
                        tmpsurveyzdict['n'].append( hist[i] )
                tmpzdf = pandas.DataFrame( tmpsurveyzdict )
                if zhistdf is None:
                    zhistdf = tmpzdf
                else:
                    zhistdf = pandas.concat( [ zhistdf, tmpzdf ], axis=0 )

                # zhistdf.sort_values( ['NAME', 'FIELD', 'MU', 'z'], inplace=True )


        # read the BBC_SUMMARY into cosmodf
        
        nameversionre = re.compile( '^.*_DATA_(ROMAN.*)$' )

        def nameversionstrip( ver ):
            match = nameversionre.search( ver )
            if match is None:
                raise RuntimeError( f"Failed to match {ver}" )
            return match.group(1)

        fpath = indir / 'DATA_FILES/BBC_SUMMARY_wfit.FITRES'
        if not fpath.is_file():
            fpath = indir / 'DATA_FILES/BBC_SUMMARY_wfit.FITRES.gz'
        if not fpath.is_file():
            raise FileNotFoundError( f"Failed to find BBC_SUMMARY_wfit.FITRES(.gz)" )
        cosmodf = pandas.read_csv( fpath, sep='\s+', comment='#' )
        cosmodf['NAME'] = cosmodf['VERSION'].apply( nameversionstrip )
        cosmodf.drop( [ 'VARNAMES:', 'ROW', 'VERSION' ], axis=1, inplace=True )

        # Sort and index all the dataframes
        
        infodf.set_index( 'NAME', inplace=True )
        snrmaxdf.sort_values( [ 'NAME', 'ORDINAL' ], inplace=True )
        snrmaxdf.set_index( [ 'NAME', 'ORDINAL' ], inplace=True )
        tierdf.sort_values( [ 'NAME', 'TIER'], inplace=True )
        tierdf.set_index( [ 'NAME', 'TIER'], inplace=True )
        obsdf.sort_values( [ 'NAME', 'TIER', 'FILTER' ], inplace=True )
        obsdf.set_index( [ 'NAME', 'TIER', 'FILTER' ], inplace=True )
        zhistdf.sort_values( ['NAME', 'FIELD', 'MU', 'z'], inplace=True )
        zhistdf.set_index( ['NAME', 'FIELD', 'MU', 'z'], inplace=True )
        cosmodf.sort_values( ['NAME', 'FITOPT', 'MUOPT'], inplace=True )
        cosmodf.set_index( ['NAME', 'FITOPT', 'MUOPT'], inplace=True )

        # Safe to self
        
        self.collections[ collection ] = { 'infodf': infodf,
                                           'snrmaxdf': snrmaxdf,
                                           'tierdf': tierdf,
                                           'obsdf': obsdf,
                                           'zhistdf': zhistdf,
                                           'cosmodf': cosmodf
                                          }
        # Save to cache dir
        
        if savecache:
            for attr in 'infodf', 'snrmaxdf', 'tierdf', 'obsdf', 'zhistdf', 'cosmodf':
                self.collections[attr].to_pickle( self.outdir / f'{collection}_{attr}.pkl' )
