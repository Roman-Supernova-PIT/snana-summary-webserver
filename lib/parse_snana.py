import sys
import pathlib
import re
import yaml
import numpy
import pandas

class RomanSurveySummary:
    known_filters = ['R', 'Z', 'Y', 'J', 'H', 'F', 'K']

    def __init__( self, subdir, noread=False ):
        self.subdir = pathlib.Path( subdir )
        if not noread:
            self.read_files()


    def get_survey_info( self, input_file, printing=True ):
        input_file = pathlib.Path( input_file )
        
        #Survey name
        surveyname = input_file.name.replace( ".SIMLIB", "" )

        #Read the documentation from the SIMLIB file
        lines = []
        with open( input_file ) as ifp:
            for line in ifp:
                if line[0:18] == "DOCUMENTATION_END:": break
                lines.append( line )
        config_yaml = yaml.safe_load( '\n'.join( lines ) )

        # Build the return value in obs_dict

        doc = config_yaml['DOCUMENTATION']

        objs_dict = { 'TIME_SUM_OBS': float( doc['TIME_SUM_OBS'] ),
                      'TIME_SUM_SEASON': float( doc['TIME_SUM_SEASON'] ),
                      'RANDOM_REJECT_OBS': float( doc['RANDOM_REJECT_OBS'] ),
                      'TIME_SLEW': float( doc['TIME_SLEW'] ) }

        forcesnrre = re.compile( '^\s*(\d+)\s*\[\s*(\d+),\s*(\d+)\s*\]$' )
        objs_dict['TIERS'] = {}
        for tierinfo, force_snrmax, tierexp in zip( doc['TIER_INFO'],
                                                    doc['FORCE_SNRMAX'],
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

            match = forcesnrre.search( force_snrmax )
            if match is None:
                raise ValueError( f"Failed to parse \"{force_snrmax}\" as a FORCE_SNRMAX entry" )
            objs_dict['TIERS'][name]['FORCE_SNRMAX'] = float( match.group(1) )
            objs_dict['TIERS'][name]['FORCE_SNRMAX_LAM0'] = float( match.group(2) )
            objs_dict['TIERS'][name]['FORCE_SNRMAX_LAM1'] = float( match.group(3) )

            exptimeinfo = tierexp.split()
            if exptimeinfo[0] != name:
                raise RuntimeError( f"Exposure time name {exptimeinfo[0]} doesn't match tier name {name}" )
            bands = exptimeinfo[1]
            exptimes = exptimeinfo[2:]
            if len(bands) != len(exptimes):
                raise RuntimeError( f"Number of bands {len(bands)} != len(exptimes)={len(exptimes)}" )
            objs_dict['TIERS'][name]['EXPTIME'] = { k: float(v) for k, v in zip( bands, exptimes ) }
            for filt in SurveySummary.known_filters:
                if filt not in objs_dict['TIERS'][name]['EXPTIME']:
                    objs_dict['TIERS'][name]['EXPTIME'][filt] = 0.
            for filt in objs_dict['TIERS'][name]['EXPTIME'].keys():
                if filt not in SurveySummary.known_filters:
                    raise RuntimeError( f"Unknown filter {filt}" )
            
        return objs_dict, surveyname
    

    def read_files( self, cached=True ):
        if cached:
            mustredo = False
            for attr in ( 'infodf', 'tierdf', 'obsdf', 'zhistdf', 'cosmodf' ):
                if not ( self.subdir / f'{attr}.pkl' ).is_file():
                    sys.stderr.write( f"Didn't find {self.subdir/attr}.pkl, regenerating\n" )
                    mustredo = True
                    break
            if not mustredo:
                for attr in ( 'infodf', 'tierdf', 'obsdf', 'zhistdf', 'cosmodf' ):
                    setattr( self, attr, pandas.read_pickle( self.subdir / f"{attr}.pkl" ) )
                return

        infodf = None
        tierdf = None
        obsdf = None
        zhistdf = None

        simlibs = self.subdir.glob( "*.SIMLIB" )
        
        for simlib in simlibs:
            outdict, name = self.get_survey_info( simlib )

            tmpdf = pandas.DataFrame( { k:[outdict[k]] for k in outdict.keys() if k != 'TIERS' } )
            tmpdf['NAME'] = name
            tmpdf.set_index( 'NAME', inplace=True )
            if infodf is None:
                infodf = tmpdf
            else:
                infodf = pandas.concat( [ infodf, tmpdf ], axis=0 )

            for tier, tierinfo in outdict['TIERS'].items():
                # I do not understand why above I had to do k:[outdict[k]], but here I do k:tierinfo[k]
                # Pandas is very mysterious
                tmpdf = pandas.DataFrame( [ { k:tierinfo[k] for k in tierinfo.keys() if k != 'EXPTIME' } ] )
                tmpdf[ 'NAME' ] = name
                tmpdf[ 'TIER' ] = tier
                tmpdf.set_index( [ 'NAME', 'TIER'], inplace=True )
                if tierdf is None:
                    tierdf = tmpdf
                else:
                    tierdf = pandas.concat( [ tierdf, tmpdf ], axis=0)

                tmpdf = pandas.DataFrame( [ { 'FILTER': filt, 'EXPTIME': tierinfo['EXPTIME'][filt] }
                                            for filt in tierinfo['EXPTIME'].keys() ] )
                tmpdf[ 'NAME' ] = name
                tmpdf[ 'TIER' ] = tier
                tmpdf['FILTER'] = pandas.Categorical( tmpdf['FILTER'], SurveySummary.known_filters )
                tmpdf.sort_values( ['NAME', 'TIER', 'FILTER'], inplace=True )
                tmpdf.set_index( ['NAME', 'TIER', 'FILTER' ], inplace=True )
                
                if obsdf is None:
                    obsdf = tmpdf
                else:
                    obsdf = pandas.concat( [ obsdf, tmpdf ], axis=0 )

            for mu in [ 0, 1 ]:
                fname = [ i for i in ( self.subdir / "DATA_FILES" ).glob( f"*{name}/FITOPT000_MUOPT{mu:03d}.FITRES" ) ]
                if len(fname) > 1:
                    raise RuntimeError( "Too many matches!" )
                fname = fname[0]
                tmpdf = pandas.read_csv( fname, comment='#', sep='\s+' )
                
                knownfields = tmpdf['FIELD'].unique()
                # sys.stderr.write( f"knownfields: {knownfields}\n" )
                for field in knownfields:
                    found = False
                    for t in tierdf.xs( name, level='NAME' ).index.unique( 'TIER' ).values:
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
                        tmpsurveyzdict['z'].append( bins[i] )
                        tmpsurveyzdict['n'].append( hist[i] )
                tmpzdf = pandas.DataFrame( tmpsurveyzdict )
                if zhistdf is None:
                    zhistdf = tmpzdf
                else:
                    zhistdf = pandas.concat( [ zhistdf, tmpzdf ], axis=0 )

                # zhistdf.sort_values( ['NAME', 'FIELD', 'MU', 'z'], inplace=True )

        zhistdf.sort_values( ['NAME', 'FIELD', 'MU', 'z'], inplace=True )
        zhistdf.set_index( ['NAME', 'FIELD', 'MU', 'z'], inplace=True )

        nameversionre = re.compile( '^.*_DATA_(ROMAN.*)$' )

        def nameversionstrip( ver ):
            match = nameversionre.search( ver )
            if match is None:
                raise RuntimeError( f"Failed to match {ver}" )
            return match.group(1)

        cosmodf = pandas.read_csv( self.subdir / 'DATA_FILES/BBC_SUMMARY_wfit.FITRES', sep='\s+', comment='#' )
        cosmodf['NAME'] = cosmodf['VERSION'].apply( nameversionstrip )
        cosmodf.drop( [ 'VARNAMES:', 'ROW', 'VERSION' ], axis=1, inplace=True )
        cosmodf.sort_values( ['NAME','FITOPT','MUOPT'], inplace=True )
        cosmodf.set_index( ['NAME', 'FITOPT', 'MUOPT'], inplace=True )

        self.infodf = infodf
        self.tierdf = tierdf
        self.obsdf = obsdf
        self.zhistdf = zhistdf
        self.cosmodf = cosmodf

        if cached:
            for attr in 'infodf', 'tierdf', 'obsdf', 'zhistdf', 'cosmodf':
                getattr( self, attr ).to_pickle( self.subdir / f'{attr}.pkl' )
