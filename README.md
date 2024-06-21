# A web service for pulling summary information from SNANA ROMAN PIT sims

## Overview of the SNANA sims performed

Many (hundreds of) SNANA sims are performed at once; all of these sims together are termed a **campaign**.  Right now, the webserver only serves up information from a single campaign.  With a campaign, there is a **collection**.  A collection is defined by some very broad parameters: how many tiers of photometric observations there are, what fraction of the time goes to the prism, and and what photometric bands are used.  A collection defines a 3d grid of valuers for three parameters: the relative sky area covered by each tier; the cadence in days of each tier, and the target redshift (where SNR tries to be 100) for each tier.

Within one sim, there are multiple **spectrum strategies**.  A single spectrum strategy defines a prism exposure time for each tier.

So, for example, the collection `2TIER_PRSIM25_5bands` may have the following:

* 25% of the time goes to the prism (the rest to imaging)
* Two tiers, "SHALLOW" and "DEEP"
* Photometric observations in bands RZYJH for the SHALLOW tier and bands ZYJHF for the DEEP tier.
* Three possibilities for SHALLOW/DEEP relative area: 4/1, 2/1, and 1/1.
* Three posibililties for cadence: [ 3, 5, 8 ] days for SHALLOW, and [ 5, 10, 15 ] days for DEEP.  (There are only three, not 9, possibilities; any sim with a 3-day cadence for the SHALLOW tier has a 5-day cadence for the DEEP tier.)
* Four possiblities for z(SNR=10) : [0.5, 0.7, 0.9, 1.1] for the SHALLOW tier and [1.2, 1.5, 1.8, 2.1] for the DEEP tier.  (Again, there are 4, not 16, possibilities: any sim with a SHALLOW target of z=0.5 has a DEEP target of z=1.2.)
* Three different spectrum strategies, with SHALLOW/DEEP exposure times of [ 1000s/3000s, 2000s/6000s, 3000s/10000s ].

Within this collection there are a total of 3×3×4=36 sims.  (The different spectrum strategies don't make different sims, because the photometric simulation is identical in each case; a sim defines set of parameters for the photometric strategy.)

## snana-summary-webserver interactive website

This lives at `https://roman-snpit-snana-strategy.lbl.gov/`

DOCUMENTATION TODO

---

## Underlying data

This webap (and API) show summary data collected from the output of SNANA runs.  The SNANA output can be found in two directories:

* [https://portal.nersc.gov/cfs/m4385/sims/RomanPIT-SNANA/](https://portal.nersc.gov/cfs/m4385/sims/RomanPIT-SNANA/) — SNANA output files with simulated photometric and spectroscopic data
* [https://portal.nersc.gov/cfs/m4385/sims/RomanPIT_SNANA_pipeline_output/](https://portal.nersc.gov/cfs/m4385/sims/RomanPIT_SNANA_pipeline_output/) — SNANA collected summary and cosmology files.

Each of those directories have multiple subdirectories.  One subdirectory holds a campaign; there are subdirectories for the collections within each campaign.  See the file `AAA_README.TXT` in the latter directory for a description of the campaigns.

---

## snana-summary-webserver API

The base URL for the API is the same as for the interactive webserver: `https://roman-snpit-snana-strategy.lbl.gov/`.  There are several API endpoints that return data in (usually) JSON format:

---

### `/collections`

This API endpoint just returns a JSON string with list of the collections that are available for the campaign that the web server is currently pointing at.  This will be a list of names like `2TIER_PRISM25_5bands`.  Don't try to algorithmically parse the names returned; just view them as opaque strings for getting further information.  (They may be shown to users though for humans to try to parse.)

---

### `/surveyinfo`

Hit this API with the url `<baseurl>/surveyinfo/<string:collection>`, where the argument at the end is the collection you want to get information for.  So, for example, you might hit the url `https://roman-snpit-snana-strategy.lbl.gov/surveyinfo/2TIER_PRISM25_5bands`

This API returns a JSON dictionary with the following keys.  Many of these are internal SNANA variables and are not useful outside of SNANA.

* `OUTDIR`: (internal)
* `FORCE_TEXPOSE_LIST`:
* `FORCE_SIMGEN_NIPUT_FILE`: (internal)
* `FORCE_NGEN`:
* `FORCE_SNRMAX`:
* `NLIBID_TOT`:
* `TIME_SUM_OBS`: Total _photometric_ observing time in days for one season, including slews.
* `TEXPOSE_MIN`: (internal)
* `RANDOM_REJECT_OBS`: This fraction of simulated observations are thrown out (to simulate dithers, things falling in chip gaps, etc.)
* `MJD_SEASON`: A list of dictionaries, each with keys `season_mjd0` and `season_mjd1`, defining the MJD range for each season simulated.
* `TIERS`: A list of strings defining the tiers, and the grid of parameters for each tier.  Needs further parsing if you want to interpret them.  (See below.)
* `TEXPOSE_PRISM`: Two strings defining the spectrum strategies.

#### `TIERS`

The `/tiers` API endpoint (below) is probably more convenient to use than parsing this.

The list strings defining the tiers look something like:

```
[
   'SHALLOW   10  -10   RZYJH    [4,2,1]    [3,  5, 8 ]   [0.5, 0.7, 0.9, 1.1]'
   'DEEP      20  +10   ZYJHF    [1,1,1]    [5, 10, 15]   [1.2, 1.5, 1.8, 2.1]'
]
```

The columns, left to right, are: tier name, ra, dec, bands used for that tier, list of relative areas, list of cadences in days, and list of SNR=10 target redshifts.

---

### `/instrinfo`

API url: `<baseurl>/instrinfo/<string:collection>` (see `/surveyinfo` above).

Returns a JSON-encoded dictionary with bunch of information about the simulated instrument that SNANA used.

---

### `/analysisinfo`

API url: `<baseurl>/analysisinfo/<string:collection>` (see `/surveyinfo` above).

A JSON-encoded dictionary with a bunch of parameters that defined what SNANA did.  Probably of most interest is the sub-dictionary found underneath the `prescales` key of this dictionary.  The keys of that sub-dictionary are object types that were in the simulation (e.g. `Ia`, `AGN`, `IIL`, etc.).  The values are the scaling that should be applied to numbers of objects produced by the sim.  So, for example, if `analysisinfo['prescales']['IIP']` is equal to 10.0, that means that the sim only produced lightcurves for 1/10 as many SNIIP supernovae as it simulated would exist.  As such, any counts of IIP supernovae produced by further endpoints below should be multiplied by 10.

---

### `/tiers`

API url: `<baseurl>/tiers/<string:collection>` (see `/surveyinfo` above).

A JSON-encoded list with information about the tiers from this collection.  The length of the list is the number of tiers; each element of the list is a dictionary with keys:

* `name`: the name of the tier (e.g. `SHALLOW`, `MEDIUM`, `DEEP`, etc.).  Don't try to algoritmically interpret this, just view it as a key.  However present it to the user, as the name is usually (at least) suggestive.
* `ra` : Not really meaningful, because this was not an image-level simulation, just a catalog-level simulation
* `dec`:
* `relarea`: A list; each element of the list has relative area (relative to the numbers for all the other tiers) of the imaging survey that went to this tier.
* `dt_visit`: A list; each element of this list has the cadence in days of the imaging survey for this tier.
* `z_snrmatch`: A list; each element has the target redshfit for SNR=10 for this tier.
* `texpose_prism`: A list; each element has the prism exposure time used for this tier for one of the spectrum stategies.

As described above under "Overview of the SNANA sims performed", The `relarea`, `dt_visit`, and `z_snrmatch` lists define a matrix of sims performed; all those sims together comprise this collection.  As such, the lengths of those lists *must* be the same for each tier within the collection, as each sim must have values for each tier.  (If the lists aren't the same, then something internally has gone wrong.)

A single sim within the collection (a) the index into the `relarea` asrea, (t) the index into the `dt_visit` array, and (z) the index into the `z_snrmatch` array.  So, for example, suppose the collection had the following definitions:

```
[
  { 'name': 'SHALLOW', 'relarea': [4,2,1], 'dt_visit': [3.,5.,8.],   'z_snrmatch': [0.8,1.0], texpose_prism: [1000,2000,3000] }
  { 'name': 'DEEP',    'relarea': [1,1,1], 'dt_visit': [5.,10.,15.], 'z_snrmatch': [1.4,1.6], texpose_prism: [3000,6000,10000] },
]
```

(Note that the full structure returned by the URL is not included in this example above; some keys have been omitted.)

In this case, there are 3×3×2 different sims.  A couple of examples:

* The sim `a0_t0_z0` has two tiers, SHALLOW and DEEP, with SHALLOW covering four times the area of DEEP.  The SHALLOW fields have a visit cadence of 3 days, and the DEEP fields have a visit cadence of 5 days.  Exposure times for the SHALLOW field were chosen in an attempt to make SNIa at z=0.8 to have a SNR of 10, and for the DEEP field were chosen in an attempt to make SNIa at z=1.4 to have a SNR of 10.
* The sim `a1_t2_z1` has two tiers, SHALLOW and DEEP, with SHAOOW covering two times the area of DEEP.  The SHALLOW fields have a visit cadence of 8 days, and the DEEP fields have a visit cadence of 15 days.  Exposure times were chosen to target SNR=10 for SNIa at z=1.0 for the SHALLOW fields, and at z=1.6 for the DEEP fields.

Each sim is further divided into three spectrum strategies, with given exposure times for the different tiers.

---

### `/surveys`

API url: `<baseurl>/surveys/<string:collection>` (see `/surveyinfo` above).

Returns a JSON-encoded dictionary with a lot of information about each collection.  The key is the name of the sim (where the API url comes from "survey"="sim"), and the value is another dictionary with a lot of information.  The name of the sim should probably not be algorithmically parsed, but it's always '{collection} a{ai}_t{ti}_z{zi}' where `ai`, `ti`, and `zi` are indexes into the arrays defined in `/tiers` above.

The sub-dictionary for a single sim has keys:

* `tiers`: Information about the tiers for this particular sim (see below)
* `gentypemap`: A mapping of SNANA gentypes (used elsewhere) to actual types (see below)
* `zhist`: Numbers of objects found as function of tier, redshift and gentype (see below)
* `snrmaxzhist`: (see below)
* `snrmax2zhist`: (see below)
* `snrmax3zhist`: (see below)
* `long_survey_version`: (used internally, may be ignored)
* `spechists`: A really complicated dictionary with information about numbers of spectra (see below)
* `muopt`: (can probably be ingored, until it can't)

#### `tiers`

The `tiers` sub-subdictionary has the following structure:

```
{ tier: {
    "bands": {
       band: exptime (float),
       band: exptime (float),
       ...
     }
     "ntile": number of tiles on the sky included in this tier (integer),
     "nvisit": number of times each tile was visited (integer),
     "area": area of this tier in square degrees (float),
     "dt_visit": cadence for this tier in days (float),
     "NLIBID":
     "zSNRMATCH": The redshift that was targeted for SNR=10 for this tier (float),
     "OpenFrac": (Check this) The fraction of time assigned to this tier that was actually exposing (float)
  },
  tier: { ... },
  ...
}
```

Ideally, these numbers will be consistent with what you get from the `/tiers` API endpoint.  (There is more infrormation here, though.  For example, whereas `/tiers` only specifies relative areas covered by the different tiers, this structure has the actual area covered by each tier.)

#### `gentypemap`:

A dictionary of int:string that goes from `gentype` (the internal SNANA type key, also used in the histogram data structures below) to a string suitable for use in plot captions.  This dictionary will probably always have exactly the following contents (but don't assume that, it could conceivably change):

```
{
  "10": "Ia",
  "32": "IIP",
  "33": "IIL",
  "21": "Ib",
  "26": "Ic",
  "11": "SNIa-91bg",
  "42": "TDE",
  "40": "SLSN-I",
  "60": "AGN"
}
```

(Notice that the keys are strings and not integers; this is a limitation of JSON, which requires that all keys be strings.  If you want to interpret the key values, you probably need to run it through `int()`.  This JSON limitation is annoying in other places too.)

#### 'zhist'

The easiest way to hand the data here is to parse it into a Pandas dataframe, e.g.:

```
  df = pandas.DataFrame( surveys['2TIER_PRSIM25_5bands a00-t00-z00']['zhist'] ).set_index( ['tier','gentype','zCMB'] )
```

That will give you a series of histograms for the different tiers and types of objects as a function of redshift.  For example, suppose you want the numbers of SNIa found in this sim as a function of redshift in the shallow tier.  You could extract that histogram with

```
  df.xs( ( 'SHALLOW', 10 ), level=( 'tier', 'gentype' ) )
```

Histogram bins (the `zCMB` index in the extracted dataframe) are left-side bins.

#### `snrmaxzhist`, `snrmax2zhist`, `snrmax3zhist`

These have exactly the same structure as `zhist`, only the counts have been filtered:

`snrmaxzhist` : only supernoave with at least one detection above S/N=5.  This is probably approximately redundant with `zhist`.

`snrmax2zhist` : only supernoave with at least one detection above S/N=5 in all bands other than the one that had the highest S/N point.  That is, if the highest S/N point in J-band was 7.0, but the highest S/N point in H-band was 4.0, that object would be included in the `snrmaxzhist` counts but _not_ in the `snrmax2hist` counts.

`snrmax3zhist`: only supernovae with at least one detection above S/N=5 in all bands other than the two bands with the higest S/N detections.

#### `spechists`

This one is giant.

---

### `/summarydata`

API url: `<baseurl>/surveys/<string:collection>` (see `/surveyinfo` above).

This is a way to get all of the information returned by API endpoints above in one go.  It returns a JSON-encoded dict with keys:

* `surveyinfo` : what you'd get from `/surveyinfo/{collection}`
* `instrinfo` : what you'd get from `/instrinfo/{collection}`
* `analysisinfo` : what you'd get from `/analysisinfo/{collection}`
* `tiers` : what you'd get from `/tiers/{collection}`
* `surveys` : what you'd get from `/surveys/{collection}`

---

### `/snzhist`

This one does not return a JSON array, but rather returns an SVG image with the requested histogram (plotted server-side using matplotlib).  All the data you need to plot these histograms yourself is already present in what you get back from `/surveys`.  This exists as a convenience (and so that I didn't have to bother plotting histograms in Javascript when writing the web ap).

Hit this URL at `<baseurl>/snzhist/<string:collection>/<string:sim>`, with optionally additional arguments at the end of the URL.  Additional arguments are appended with `/key=value`.  Supported arguments are:

* `width`: target width of the image in pixels, default 600.  (You get an svg back, so you can display it higher than this and it will still look good, but this is for purposes of font sizes, etc.)
* `heigh`: target height of the image in pixels, default 500.
* `whichhist`: one of `zhist`, `snrmaxzhist`, `snrmax2hist`, or `snrmax3zhist`, default `zhist`.
* `gentype`: the type of objects to plot the histograms for, default 10 (SNIa).
* `tier`: which tiers to plot the histogram for, default `__ALL__`

Two of these options require further explanation.

`gentype` can be any of the numeric gentypes from the keys of `gentypemap` you get back from the `/surveys` API endpoint.  It can also have one of two special values: `__ALL__` and `__ALLBUT1A__`.  Theses will plot a huge number of bars in each redshift bin for various different types.  (Play with the interactive webserver to see what this looks like.)

`tier` can be either one of the names of the tiers (something like `SHALLOW` or `DEEP`), or it can be `__ALL__`, in which case multiple bars (for each tier) are plotted in each redshift bin.  (Again, play with the interactive webserver to see what this looks like.)

---

### `/spechist`

TODO

---

### `/randomltcv`'

Ask the server to return a random lightcurve.

Hit this url at one of:

* `<baseurl>/randomltcv/<string:collection>/<string:sim>/<string:gentype>/<float:z>/<float:dz>`
* `<baseurl>/randomltcv/<string:collection>/<string:sim>/<string:gentype>/<float:z>/<float:dz>/<string:tier>`

It will return a randomly chosen object from the specified collection and sim, of the specified type, at the specified reshift within the specified redshift range.  If the `tier` argument is included, it will only choose from objects observed as part of that tier; otherwise, it will choose from all objects.

The returned value is a JSON-encoded dictionary:

```
{ 'status': 'ok',
  'zp': 27.5,
  'ltcv': {
     band: { 'mjd': [ ... ],
             'flux': [ ... ],
             'dflux': [ ... ]
           },
     band: { 'mjd': [ ... ],
             'flux': [ ... ],
             'dflux': [ ... ]
           },
    ...
  }
}
```

(If `status` is 'error' instead of 'ok', then the rest of the keys won't be there and instead there will be a key `error` with (hopefully) a meaningful error message.)

'zp' is the standard SNANA zeropoint, and is used to convert all fluxes to magnitudes.

The 'ltcv' sub-dictionary has the lightcurves for each band.  (band will be something like 'J', 'H', etc.)  Hopefully the format is self-explanatory.

---

### `/randomspectrum`

Ask the server to return a random spectrum.

The URL to hit is

```
<baseurl>/randomspectrum/<string:collection>/<string:sim>/<int:gentype>/<float:z>/<float:dz>/<float:t>/<float:dt>
```

with optional additional arguments appended at the end via a series of `/key=value`.

This will return a spectrum from the spedified collection/sim and object type at the specified redshift (within `dz`) and time relative to max (within `dt`).  Optional additional arguments are:

* `tframe`: one of 'rest' or 'obs', default 'rest'
* `tier`: one of the photometric tiers (e.g. "DEEP" or "SHALLOW"); if not specified, will randomly choose from all tiers.
* `specstrat`: an integer.  This is an index into one of the `texpose_prism` arrays returned by `/tiers`.  If not specified, will randomly find a spectrum from any spectrum strategy.

The return value is a JSON-encoded dictionary with structure:

```
{ 'status': 'ok',
  'tier': 'Any' or the name of the tier this spectrum was selected from,
  'snid': int,   # internal SNANA object ID.  May be useful later when the API has more endpoints
  'snz': float,  # The redshift of the SN returned
  'mwebv': float,
  'av': float',
  'rv': float,
  'spec_texp': float,   # Exposure time for this spectrum
  'spec_dtrest': float,  # Rest frame days of this spectrum relative ot object max
  'spec_nbin_lam': float,   # (todo)
  'spechost_contam': float,  # (todo)
  'spectrum': {
     'lammin': [ ... ],   # Left side of the wavelength bin
     'lammax': [ ... ],   # Right side of the wavelength bin
     'flam': [ ... ],     # Observed F_λ in... some units...
     'flamerr': [ ... ],  # Uncertainty on F_λ
     'sim_flam': [ ... ], # (CHECK THIS) the simulated F_λ before processed through simulated observations
  }
}
```

As with `/randomltcv`, if `status` is 'error' instead of 'ok', then the rest of the fields will not be there; instead, there will be an `error` field.
