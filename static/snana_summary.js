import { rkWebUtil } from "./rkwebutil.js";
import { SVGPlot } from "./svgplot.js";

// Namespace

var snanasum = {};

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.Context = class
{
    constructor()
    {
        this.collections = null;
        this.collectiondivs = {};
    };


    static filter_order = { 'R': 0,
                            'Z': 1,
                            'Y': 2,
                            'J': 3,
                            'H': 4,
                            'F': 5,
                            'K': 6 };


    static filter_sort = function( a, b ) {
        if ( !snanasum.Context.filter_order.hasOwnProperty( a ) ) {
            if ( !snanasum.Context.filter_order.hasOwnProperty( b ) ) {
                if ( a < b ) return -1;
                else if ( a > b ) return 1;
                else return 0;
            }
            return 1;
        }
        else if ( !snanasum.Context.filter_order.hasOwnProperty( b ) ) return 1;
        else {
            if ( snanasum.Context.filter_order[a] < snanasum.Context.filter_order[b] ) return -1
            else if ( snanasum.Context.filter_order[a] > snanasum.Context.filter_order[b] ) return 1;
            else return 0;
        }
    }


    renderpage()
    {
        var self = this;

        if ( this.collections == null ) {
            let connector = new rkWebUtil.Connector( "/collections" );
            connector.sendHttpRequest( "", {}, function( r ) { self.parse_collections_and_render( r ); } );
        }
        else {
            this.actually_renderpage();
        }
    }


    parse_collections_and_render( data )
    {
        this.maindiv = document.getElementById( "pagebody" );
        rkWebUtil.wipeDiv( this.maindiv );

        if ( data.hasOwnProperty( 'error' ) ) {
            rkWebUtil.elemaker( "h2", this.maindiv, { "text": "Error from server" } );
            rkWebUtil.elemaker( "p", this.maindiv, { 'text': data['error'] } );
            return;
        }

        this.collections = data['collections'];
        this.actually_renderpage();
    }


    actually_renderpage( data )
    {
        var self = this
        var h3;

        rkWebUtil.elemaker( "h4", this.maindiv,
                            { "text": "WARNING: results are very preliminary and subject to massive change" } );

        h3 = rkWebUtil.elemaker( "h3", this.maindiv, { "text": "Show simulation collection: " } );
        this.collectionwidget = rkWebUtil.elemaker( "select", h3 );
        let col = null;
        for ( let collection of this.collections ) {
            let option = rkWebUtil.elemaker( "option", this.collectionwidget,
                                             { "text": collection,
                                               "attributes": { "value": collection } } );
            if ( col == null ) {
                option.setAttribute( "selected", "selected" );
                col = collection;
            }
        }

        rkWebUtil.elemaker( "hr", this.maindiv );
        this.collectiondiv = rkWebUtil.elemaker( "div", this.maindiv );

        this.collectionwidget.addEventListener( "change", function() {
            let col = self.collectionwidget.value;
            if ( ! self.collectiondivs.hasOwnProperty( col ) ) {
                self.collectiondivs[col] = new snanasum.Collection( col, self.collectiondiv );
            }
            self.collectiondivs[col].renderpage();
        } );

        this.collectiondivs[col] = new snanasum.Collection( col, this.collectiondiv );
        this.collectiondivs[col].renderpage();
    }
}

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.Collection = class {
    constructor( collection, maindiv )
    {
        this.maindiv = maindiv;
        this.collection = collection;
        this.surveylist = null;
        this.tierlist = null;
        this.sortkeys = null;
        this.shown_sim = null;
        this.simtable_hidecolumns = [];
    }


    renderpage()
    {
        var self = this;
        if ( this.surveylist == null ) {
            let connector = new rkWebUtil.Connector( "/summarydata" );
            connector.sendHttpRequest( "/"+this.collection, {},
                                       function( resp ) { self.parse_summary_info_and_render( resp ); } );
        }
        else {
            this.actually_renderpage();
        }
    }


    parse_summary_info_and_render( data )
    {
        this.surveyinfo = data.surveyinfo;
        this.instrinfo = data.instrinfo;
        this.analysisinfo = data.analysisinfo;
        this.tiers = data.tiers;
        this.surveys = data.surveys;

        this.surveylist = Object.keys( this.surveys );
        this.tierlist = [];
        for ( let survey of this.surveylist ) {
            for ( let tier of Object.keys( this.surveys[survey].tiers ) ) {
                if ( !this.tierlist.includes( tier ) ) {
                    this.tierlist.push( tier );
                }
            }
        }

        this.actually_renderpage();
    }


    get_filter_str( sim, tier )
    {
        let filters = [];
        for ( let filt of Object.keys( this.surveys[sim]['tiers'][tier]['bands'] ) ) {
            if ( this.surveys[sim]['tiers'][tier]['bands'][filt] > 0 ) {
                filters.push( filt );
            }
        }
        filters.sort( snanasum.Context.filter_sort );
        return filters.join();
    };


    actually_renderpage( data )
    {
        var div, p, option;

        var self = this;

        rkWebUtil.wipeDiv( this.maindiv );
        this.contentdiv = rkWebUtil.elemaker( "div", this.maindiv );

        div = rkWebUtil.elemaker( "div", this.contentdiv, { "classes": [ "main_hbox" ] } );
        this.tabdiv = rkWebUtil.elemaker( "div", div, { "classes": [ "tabdiv" ] } );

        this.metainfodiv = rkWebUtil.elemaker( "div", div, { "classes": [ "metainfodiv" ] } );
        this.tabber = new rkWebUtil.Tabbed( this.metainfodiv );

        this.histdiv = rkWebUtil.elemaker( "div", null );
        this.tabber.addTab( "hists", "Photometry Summary", this.histdiv, true );
        this.specinfodiv = rkWebUtil.elemaker( "div", null );
        this.tabber.addTab( "specinfo", "Spectroscopy Summary", this.specinfodiv, false );
        this.ltcvdiv = rkWebUtil.elemaker( "div", null );
        this.tabber.addTab( "ltcvs", "Lightcurves", this.ltcvdiv, false );
        this.specdiv = rkWebUtil.elemaker( "div", null );
        this.tabber.addTab( "spectra", "Spectra", this.specdiv, false );

        this.photsummary = new snanasum.PhotSummary( self, this.histdiv );
        this.specsummary = new snanasum.SpecSummary( self, this.specinfodiv );
        this.ltcvplot = new snanasum.LtcvPlot( self, this.ltcvdiv );
        this.specplot = new snanasum.SpecPlot( self, this.specdiv )


        if ( this.sortkeys == null ) {
            this.sortkeys = [ "FoM_stat" ];
            this.sortorders = [ -1 ];
            let firstsurvey = Object.keys( this.surveys )[0]
            this.sorttier = Object.keys( this.surveys[firstsurvey].tiers )[0]
        }

        let sortables = [ 'FoM_stat', 'filters', 'area', 'nvisit', 'ntile', 'dt_visit', 'zSNRMATCH' ]

        p = rkWebUtil.elemaker( "p", this.tabdiv, { "text": "Sort rows based on values for: " } );
        this.which_tier_sort = rkWebUtil.elemaker( "select", p );
        let first = false;
        for ( let tier of this.tierlist ) {
            let option = rkWebUtil.elemaker( "option", this.which_tier_sort,
                                             { "text": tier,
                                               "attributes": { "value": tier } } );
            if ( first ) {
                option.setAttribute( "selected", "selected" );
                first = false;
            }
        }
        this.which_tier_sort.addEventListener( "change", function() { self.changeSortTier() } );

        p = rkWebUtil.elemaker( "p", this.tabdiv );
        this.show_hide_column_button = rkWebUtil.elemaker( "a", p,
                                                           { "text": "Hide",
                                                             "classes": [ "link" ],
                                                             "click": function() {
                                                                 let text, vispull, visadd;
                                                                 if ( self.show_hide_column_button.textContent
                                                                      == "Hide" ) {
                                                                     text = "Show";
                                                                     vispull = "showcolumn";
                                                                     visadd = "hidecolumn";
                                                                 } else {
                                                                     text = "Hide";
                                                                     vispull = "hidecolumn";
                                                                     visadd = "showcolumn";
                                                                 }
                                                                 self.show_hide_column_button.textContent = text;
                                                                 for ( let i of self.simtable_hidecolumns ) {
                                                                     i.classList.remove( vispull );
                                                                     i.classList.add( visadd );
                                                                 }
                                                             } } );
        p.appendChild( document.createTextNode( " detail columns" ) );

        this.sim_table = rkWebUtil.elemaker( "table", this.tabdiv );

        this.render_sim_table( );
    }


    render_sim_table()
    {
        var self = this;

        // WARNING : hardcoding fitopt=0, mu=0
        var fitopt = 0;
        var mu = 0;

        rkWebUtil.wipeDiv( this.sim_table );

        this.surveylist.sort( function( a, b ) {
            for ( let i in self.sortkeys ) {
                let key = self.sortkeys[i];
                let order = self.sortorders[i];


                if ( key == 'FoM_stat' ) {
                    if ( self.surveys[a].muopt[0].FoM_stat > self.surveys[b].muopt[0].FoM_stat ) return 1 * order;
                    else if ( self.surveys[a].muopt[0].FoM_stat < self.surveys[b].muopt[0].FoM_stat ) return -1 * order;
                }
                else if ( key == "filters" ) {
                    let filta = self.get_filter_str( a, self.sorttier );
                    let filtb = self.get_filter_str( b, self.sorttier );
                    if ( filta > filtb ) return 1 * order;
                    else if ( filta < filtb ) return -1 * order;
                }
                else {
                    if ( self.surveys[a].tiers[self.sorttier][key] >
                         self.surveys[b].tiers[self.sorttier][key] ) return 1 * order;
                    else if ( self.surveys[a].tiers[self.sorttier][key] <
                              self.surveys[b].tiers[self.sorttier][key] ) return -1 * order;
                }
            }
            return 0;
        } );

        var table, tr, th, td, p;

        this.simtable_hidecolumns = [];

        tr = rkWebUtil.elemaker( "tr", this.sim_table );
        th = rkWebUtil.elemaker( "th", tr, { "text": "Sim" } );

        th = rkWebUtil.elemaker( "th", tr, { "text": "FoM" } );
        rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "FoM_stat", 1 ) } } );
        rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "FoM_stat", -1 ) } } );
        rkWebUtil.elemaker( "br", th );
        rkWebUtil.elemaker( "text", th, { "text": "(stat)" } );

        th = rkWebUtil.elemaker( "th", tr, { "text": "Tier  " } );

        // this.show_hide_img = rkWebUtil.elemaker( "img", th,
        //                                          { "attributes":
        //                                            { "src": "static/eyeline.svg",
        //                                              "alt": "s/h",
        //                                              "style": "width: 1em; height: 1em" } } );

        th = rkWebUtil.elemaker( "th", tr, { "text": "z" } );
        rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "zSNRMATCH", 1 ) } } );
        rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "zSNRMATCH", -1 ) } } );
        rkWebUtil.elemaker( "br", th );
        rkWebUtil.elemaker( "text", th, { "text": "targ" } );
        this.simtable_hidecolumns.push( th );

        th = rkWebUtil.elemaker( "th", tr, { "text": "Bands" } );
        rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "filters", 1 ) } } );
        rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "filters", -1 ) } } );
        this.simtable_hidecolumns.push( th );

        th = rkWebUtil.elemaker( "th", tr, { "text": "Area" } );
        rkWebUtil.elemaker( "br", th );
        rkWebUtil.elemaker( "text", th, { "text": "□° " } );
        rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "area", 1 ) } } );
        rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "area", -1 ) } } );
        this.simtable_hidecolumns.push( th );

        th = rkWebUtil.elemaker( "th", tr, { "text": "ntile" } );
        rkWebUtil.elemaker( "br", th );
        rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "ntile", 1 ) } } );
        rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "ntile", -1 ) } } );
        this.simtable_hidecolumns.push( th );

        th = rkWebUtil.elemaker( "th", tr, { "text": "nvisit" } );
        rkWebUtil.elemaker( "br", th );
        rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "nvisit", 1 ) } } );
        rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "nvisit", -1 ) } } );
        this.simtable_hidecolumns.push( th );

        th = rkWebUtil.elemaker( "th", tr, { "text": "dt" } );
        rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "dt_visit", 1 ) } } );
        rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                          "click": function() { self.addSortKey( "dt_visit", -1 ) } } );
        rkWebUtil.elemaker( "br", th );
        rkWebUtil.elemaker( "text", th, { "text": "(days)" } );
        this.simtable_hidecolumns.push( th );

        this.simtable_simname_tds = {};

        let whichcolor = 0;
        for ( let sim of this.surveylist ) {
            let survey = this.surveys[sim];
            let firstofsim = true;
            for ( let tier of this.tierlist ) {
                if ( ! survey.tiers.hasOwnProperty( tier ) ) continue;
                tr = rkWebUtil.elemaker( "tr", this.sim_table );
                if ( firstofsim ) {
                    td = rkWebUtil.elemaker( "td", tr, { "attributes": { "rowspan": Object.keys(survey.tiers).length }
                                                       } );
                    this.simtable_simname_tds[sim] = td;
                    let simtxt = sim.split( " " ).slice(-1)[0]
                    let textnode = rkWebUtil.elemaker( "span", td, { "text": simtxt,
                                                                     "classes": [ "link" ],
                                                                     "click": function(e) { self.show_sim(sim); } } );
                    // WARNING: hardcoding muopt 0
                    td = rkWebUtil.elemaker( "td", tr, { "text": survey.muopt[0].FoM_stat,
                                                         "attributes": { "rowspan": Object.keys(survey.tiers).length }
                                                       } );
                    whichcolor = 1 - whichcolor;
                    firstofsim = false;
                }
                let cls = (whichcolor == 1) ? "lotsfaded" : "mostfaded";
                tr.classList.add( cls );
                td = rkWebUtil.elemaker( "td", tr, { "text": tier } );
                td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].zSNRMATCH } );
                this.simtable_hidecolumns.push( td );

                td = rkWebUtil.elemaker( "td", tr, { "text": this.get_filter_str( sim, tier ) } );
                this.simtable_hidecolumns.push( td );
                td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].area } );
                this.simtable_hidecolumns.push( td );
                td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].ntile } );
                this.simtable_hidecolumns.push( td );
                td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].nvisit } );
                this.simtable_hidecolumns.push( td );
                td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].dt_visit } );
                this.simtable_hidecolumns.push( td );

            }
        }

        for ( let i of this.simtable_hidecolumns ) i.classList.add( "showcolumn" );

        this.show_sim( this.surveylist[0] );
    }


    changeSortTier()
    {
        let newtier = this.which_tier_sort.value;
        if ( newtier != this.sorttier ) {
            this.sorttier = newtier;
            this.render_sim_table( this.sortkeys, this.sortorders );
        }
    }


    addSortKey( sortkey, order )
    {
        let i = this.sortkeys.indexOf( sortkey );
        if (  i >= 0 ) {
            this.sortkeys.splice( i, 1 );
            this.sortorders.splice( i, 1 );
        }
        this.sortkeys.unshift( sortkey );
        this.sortorders.unshift( order );
        this.render_sim_table( this.sortkeys, this.sortorders );
    }


    show_sim( sim )
    {
        for ( let tdsim in this.simtable_simname_tds ) {
            let td = this.simtable_simname_tds[ tdsim ];
            if ( tdsim == sim ) {
                td.classList.add( "selectedsim" );
            } else {
                td.classList.remove( "selectedsim" );
            }
        }
        this.photsummary.show_sim( sim );
        this.specsummary.show_sim( sim );
        this.ltcvplot.show_sim( sim );
        this.specplot.show_sim( sim );
    }

}

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.InfoWindow = class
{
    constructor( collection, topdiv, gentypeinclall=true, gentypeinclallbutIa=true )
    {
        this.collection = collection;
        this.topdiv = topdiv;
        this.gentype_dropdown = null;
        this.gentypeinclall = gentypeinclall;
        this.gentypeinclallbutIa = gentypeinclallbutIa;
    }

    update_gentype_dropdown = function( sim=null, curval=null )
    {
        if ( this.gentype_dropdown == null ) return;
        let option;

        if ( sim == null ) sim = this.collection.surveylist[0];
        if ( curval == null ) curval = this.gentype_dropdown.value;
        rkWebUtil.wipeDiv( this.gentype_dropdown );
        if ( this.gentypeinclall ) {
            option = rkWebUtil.elemaker( "option", this.gentype_dropdown, { "text": "All Types",
                                                                            "attributes": {
                                                                                "value": "__ALL__" } } );
            if ( curval == "__ALL__" ) option.setAttribute( "selected", "selected" );
        }
        if ( this.gentypeinclallbutIa ) {
            option = rkWebUtil.elemaker( "option", this.gentype_dropdown, { "text": "All But Ia",
                                                                            "attributes": {
                                                                                "value": "__ALLBUTIA__" } } );
            if ( curval == "__ALLBUTIA__" ) option.setAttribute( "selected", "selected" );
        }

        for ( let gentype of Object.keys( this.collection.surveys[sim].gentypemap ) ) {
            option = rkWebUtil.elemaker( "option", this.gentype_dropdown,
                                         { "text": this.collection.surveys[sim].gentypemap[gentype],
                                           "attributes": { "value": gentype } } );
            if ( curval == gentype ) option.setAttribute( "selected", "selected" );
        }
    }
}

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.PhotSummary = class extends snanasum.InfoWindow
{
    constructor( collection, topdiv )
    {
        super( collection, topdiv, true, true );

        let self = this;

        this.shown_sim = null;

        let p = rkWebUtil.elemaker( "p", this.topdiv, { "text": "Histogram for " } );

        this.infodiv = rkWebUtil.elemaker( "div", this.topdiv, { "classes": [ "infodiv" ] } );

        let tmpsurvey = this.collection.surveys[ this.collection.surveylist[0] ];
        this.hist_tier_dropdown = rkWebUtil.elemaker( "select", p,
                                                      { "change": ( function() {
                                                          self.show_sim( self.shown_sim );
                                                      } ) } );
        rkWebUtil.elemaker( "option", this.hist_tier_dropdown, { "text": "All Tiers",
                                                                 "attributes": { "value": "__ALL__",
                                                                                 "selected": "selected" } } );
        for ( let tier of Object.keys( tmpsurvey['tiers'] ) ) {
            rkWebUtil.elemaker( "option", this.hist_tier_dropdown, { "text": tier,
                                                                     "attributes": { "value": tier } } )
        }
        this.gentype_dropdown = rkWebUtil.elemaker( "select", p,
                                                    { "change": ( function() {
                                                        self.show_sim( self.shown_sim );
                                                    } ) } );
        this.update_gentype_dropdown( null, 10 );

        this.sncut_dropdown = rkWebUtil.elemaker( "select", p,
                                                  { "change": ( function() {
                                                      self.show_sim( self.shown_sim );
                                                  } ) } );
        rkWebUtil.elemaker( "option", this.sncut_dropdown, { "text": "All detections",
                                                             "attributes": { "value": "zhist",
                                                                             "selected": "selected" } } );
        rkWebUtil.elemaker( "option", this.sncut_dropdown, { "text": "Highest S/N band S/N>5",
                                                             "attributes": { "value": "snrmaxzhist" } } );
        rkWebUtil.elemaker( "option", this.sncut_dropdown, { "text": "2nd highest S/N color S/N>5",
                                                             "attributes": { "value": "snrmax2zhist" } } );
        rkWebUtil.elemaker( "option", this.sncut_dropdown, { "text": "3rd highest S/N color S/N>5",
                                                             "attributes": { "value": "snrmax3zhist" } } );
    }

    show_sim( sim )
    {
        let self = this;
        if ( sim == this.shown_sim ) return;

        let p, div, hbox, table, tr, th, td;

        rkWebUtil.wipeDiv( this.infodiv );

        this.shown_sim = sim;
        if ( this.shown_sim == null ) return;

        this.update_gentype_dropdown( sim, null );

        p = rkWebUtil.elemaker( "p", this.infodiv,
                                { "text": "Core-collapse SNe, AGN, and SLSN numbers _should_ now be scaled right.",
                                  "classes": [ "italic" ] } );

        div = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "zhist-img-container" ] } );

        let whichtier = this.hist_tier_dropdown.value;
        let gentype = this.gentype_dropdown.value;
        let sncut = this.sncut_dropdown.value;

        let imgurl = "/snzhist/" + this.collection.collection + "/" + sim
            + "/whichhist=" + sncut
            + "/gentype=" + gentype
            + "/tier=" + whichtier;
        console.log( "Asking for image " + imgurl );
        let img = rkWebUtil.elemaker( "img", div,
                                      { "classes": [ "zhist" ],
                                        "attributes": { "src": imgurl,
                                                        "width": 600,
                                                        "height": 500,
                                                        "alt": "[z Histogram]" } } );

        hbox = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "hbox2emgap" ] } )

        table = rkWebUtil.elemaker( "table", hbox );
        tr = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", tr, { "text": "Season" } );
        rkWebUtil.elemaker( "th", tr, { "text": "mjd_0" } );
        rkWebUtil.elemaker( "th", tr, { "text": "mjd_1" } );
        rkWebUtil.elemaker( "th", tr, { "text": "Δmjd" } );
        for ( let row in this.collection.surveyinfo['MJD_SEASON'] ) {
            let season = this.collection.surveyinfo['MJD_SEASON'][row];
            tr = rkWebUtil.elemaker( "tr", table );
            rkWebUtil.elemaker( "td", tr, { "text": row } );
            rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd0 } );
            rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd1 } );
            rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd1 - season.season_mjd0 } );

        }

        table = rkWebUtil.elemaker( "table", hbox );
        tr = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", tr, { "text": "Σt_obs" } );
        rkWebUtil.elemaker( "td", tr, { "text": this.collection.surveyinfo['TIME_SUM_OBS'] } );
        tr = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", tr, { "text": "f_reject" } );
        rkWebUtil.elemaker( "td", tr, { "text": this.collection.surveyinfo['RANDOM_REJECT_OBS'] } );

        hbox = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "hbox2emgap" ] } );

        div = rkWebUtil.elemaker( "div", hbox );
        table = rkWebUtil.elemaker( "table", div );
        let trtiers = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", trtiers, { "text": "Tier" } );
        let trntile = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", trntile, { "text": "ntile" } );
        let trnvisit = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", trnvisit, { "text": "nvisit" } );
        let trdtvisit = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", trdtvisit, { "text": "dt_visit (d)" } );
        let trarea = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", trarea, { "text": "Area" } );
        let trzsn = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", trzsn, { "text": "z_S/N" } );
        let tropenfrac = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", tropenfrac, { "text": "Openfrac" } );
        let trfilters = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "th", trfilters, { "text": "t_exp (s)" } );
        for ( let tier of Object.keys( this.collection.surveys[sim].tiers ) ) {
            let tierinfo = this.collection.surveys[sim].tiers[tier];
            td = rkWebUtil.elemaker( "th", trtiers, { "text": tier } );
            td = rkWebUtil.elemaker( "td", trntile, { "text": tierinfo.ntile } );
            td = rkWebUtil.elemaker( "td", trnvisit, { "text": tierinfo.nvisit } );
            td = rkWebUtil.elemaker( "td", trdtvisit, { "text": tierinfo.dt_visit } );
            td = rkWebUtil.elemaker( "td", trarea, { "text": tierinfo.area } );
            td = rkWebUtil.elemaker( "td", trzsn, { "text": tierinfo.zSNRMATCH } );
            td = rkWebUtil.elemaker( "td", tropenfrac, { "text": tierinfo.OpenFrac } );
            td = rkWebUtil.elemaker( "td", trfilters );

            let filters = [];
            for ( let filt of Object.keys( tierinfo.bands ) ) {
                if ( tierinfo.bands[filt] > 0 ) {
                    filters.push( filt );
                }
            }
            filters.sort( snanasum.Context.filter_sort );

            let firstfilt = true;
            for ( let filt of filters ) {
                if ( firstfilt ) firstfilt=false;
                else rkWebUtil.elemaker( "br", td );
                td.appendChild( document.createTextNode( filt + ": " + tierinfo.bands[filt] ) );
            }
        }

        p = rkWebUtil.elemaker( "p", this.infodiv,
                                { "text": "FoM includes the low-z survey.  Numbers below " +
                                  "are only from Roman.",
                                  "classes": [ "bold" ] } );

        if ( sncut == "zhist" )
            var hist = this.collection.surveys[sim].zhist;
        else if ( sncut == "snrmaxzhist" )
            var hist = this.collection.surveys[sim].snrmaxzhist;
        else if ( sncut == "snrmax2zhist" )
            var hist = this.collection.surveys[sim].snrmax2zhist;
        else if ( sncut == "snrmax3zhist" )
            var hist = this.collection.surveys[sim].snrmax3zhist;
        else {
            window.alert( "Unknown sncut" + sncut );
            return;
        }

        // Assume that all tiers / gentypes have the same list of zs.  I
        // built it that way in parse_snana.py, so hopefully....

        var tier_gentype_zs_ns = {};
        var gt0 = hist.gentype[0];
        for ( let i in hist.zCMB ) {
            let tier = hist.tier[i];
            let gentype = hist.gentype[i];
            if ( ! tier_gentype_zs_ns.hasOwnProperty( tier ) ) {
                tier_gentype_zs_ns[tier] = {};
                for ( let gentype in this.collection.surveys[sim].gentypemap ) {
                    tier_gentype_zs_ns[tier][gentype] = { z: [], n: [] };
                }
            }
            tier_gentype_zs_ns[ tier ][ gentype ].z.push( hist.zCMB[i] );
            tier_gentype_zs_ns[ tier ][ gentype ].n.push( hist.n[i] );
        }

        for ( let tier of Object.keys( this.collection.surveys[sim].tiers ) ) {
            rkWebUtil.elemaker( "h4", this.infodiv, { "text": "Tier " + tier } );

            table = rkWebUtil.elemaker( "table", this.infodiv );
            tr = rkWebUtil.elemaker( "tr", table );
            th = rkWebUtil.elemaker( "th", tr, { "text": "z_CMB" } );
            for ( let gentype in this.collection.surveys[sim].gentypemap )
                th = rkWebUtil.elemaker( "th", tr, { "text": this.collection.surveys[sim].gentypemap[gentype] } );

            for ( let i in tier_gentype_zs_ns[tier][gt0].z ) {
                let z = tier_gentype_zs_ns[tier][gt0].z[i];
                tr = rkWebUtil.elemaker( "tr", table );
                th = rkWebUtil.elemaker( "th", tr, { "text": Math.round( z * 10 ) / 10 } );
                for ( let gentype in this.collection.surveys[sim].gentypemap ) {
                    if ( z != tier_gentype_zs_ns[tier][gentype].z[i] ) {
                        console.log( "ERROR: tier " + tier + " gentype z list mismatch: " +
                                     "i=" + i + ", z_" + gt0 + "=" +z + ", z_" + gentype + "=" +
                                     tier_gentype_zs_ns[tier][gentype].z[i] );
                    }
                    let n = tier_gentype_zs_ns[tier][gentype].n[i];
                    let nstr;
                    if ( n % 1 != 0 ) nstr = n.toFixed(1); else nstr = n;
                    td = rkWebUtil.elemaker( "td", tr, { "text": nstr } );
                }
            }
        }
    }

}


// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.LtcvPlot = class extends snanasum.InfoWindow
{
    constructor( collection, topdiv )
    {
        super( collection, topdiv, false, false );

        var self = this;

        this.shown_sim = null;

        let p, button;

        p = rkWebUtil.elemaker( "p", this.topdiv );
        button = rkWebUtil.button( p, "Plot", () => { window.alert( "Individual objects not yet implemented" ) } );
        rkWebUtil.elemaker( "span", p, { "text": " lightcurve for object # " } );
        this.ltcv_objnum_wid = rkWebUtil.elemaker( "input", p, { "attributes": { "size": 10 } } );

        p = rkWebUtil.elemaker( "p", this.topdiv );
        button = rkWebUtil.button( p, "Find and plot", () => { self.plot_random_ltcv() } );
        rkWebUtil.elemaker( "span", p, { "text": " a lightcurve of type " } );
        this.gentype_dropdown = rkWebUtil.elemaker( "select", p );
        this.update_gentype_dropdown( null, 10 );
        rkWebUtil.elemaker( "span", p, { "text": " at z= " } );
        this.ltcv_z_wid = rkWebUtil.elemaker( "input", p,
                                              { "attributes":
                                                { "value": 0.5,
                                                  "size": 5 } } );
        rkWebUtil.elemaker( "span", p, { "text": "±0.1" } );

        this.ltcv_plot_div = rkWebUtil.elemaker( "div", this.topdiv );
    }


    show_sim( sim )
    {
        if ( !sim != this.shown_sim ) {
            rkWebUtil.wipeDiv( this.ltcv_plot_div );
            this.shown_sim = sim;
            this.update_gentype_dropdown( sim, null );
        }
    }


    plot_random_ltcv()
    {
        let self = this;

        rkWebUtil.wipeDiv( this.ltcv_plot_div );

        // TODO : reafactor all this code so that it all makes more snese
        let sim = this.shown_sim;
        let connector = new rkWebUtil.Connector( "/randomltcv" )
        let gentype = this.gentype_dropdown.value;
        let z = this.ltcv_z_wid.value;
        connector.sendHttpRequest( "/" + this.collection.collection + "/" + sim + "/" + gentype + "/" + z + "/0.1",
                                   {}, (data) => { self.actually_plot_random_ltcv( data ) } );
    }


    actually_plot_random_ltcv( data )
    {
        let self = this;

        var h3, p;

        let known_filters = ['R', 'Z', 'Y', 'J', 'H', 'F', 'K'];
        let filt_colors = { 'R' : '#cc00cc',
                            'Z' : '#0000cc',
                            'Y' : '#00cccc',
                            'J' : '#00cc00',
                            'H' : '#cccc00',
                            'F' : '#666600',
                            'K' : '#000000'
                          };
        let filt_markers = { 'R' : 'dot',
                             'Z' : 'circle',
                             'Y' : 'square',
                             'J' : 'filledsquare',
                             'H' : 'diamond',
                             'F' : 'filleddiamond',
                             'K' : 'uptriangle'
                           };

        h3 = rkWebUtil.elemaker( "h3", this.ltcv_plot_div,
                                 { "text": "Obj " + data['snid'] + " at z_cmb=" + data['zcmb'].toFixed(2) } )

        let have_filts = [];
        for ( let filt of known_filters )
            if ( data['ltcv'].hasOwnProperty( filt ) )
                have_filts.push( filt );

        this.ltcv_filt_checkboxes = {}
        this.ltcv_filt_datasets = {}
        p = rkWebUtil.elemaker( "p", this.ltcv_plot_div );
        this.show_ltcv_lines_cb = rkWebUtil.elemaker( "input", p,
                                                      { "attributes":
                                                        { "type": "checkbox",
                                                          "checked": "checked",
                                                          "id": "show_ltcv_lines_cb"
                                                        },
                                                        "change": () => {
                                                            if ( self.show_ltcv_lines_cb.checked ) {
                                                                for ( let i in self.ltcv_filt_datasets ) {
                                                                    self.ltcv_filt_datasets[i].linewid = 2;
                                                                }
                                                                self.ltcv_svgplot.redraw();
                                                            }
                                                            else {
                                                                for ( let i in self.ltcv_filt_datasets ) {
                                                                    self.ltcv_filt_datasets[i].linewid = 0;
                                                                }
                                                                self.ltcv_svgplot.redraw();
                                                            }
                                                        }
                                                      } );
        rkWebUtil.elemaker( "label", p, { "attributes": { "for": "show_ltcv_lines_cb" },
                                          "text": "show lines" } );
        p = rkWebUtil.elemaker( "p", this.ltcv_plot_div );
        for ( let filt of have_filts ) {
            let span = rkWebUtil.elemaker( "span", p,
                                           { "attributes":
                                             { "style": "color: " + filt_colors[filt] } } )
            let cb = rkWebUtil.elemaker( "input", span,
                                         { "attributes":
                                           { "type": "checkbox",
                                             "checked": "checked",
                                             "id": "ltcv_checkbox_band" + filt
                                           },
                                           "change": () => {
                                               if (cb.checked) {
                                                   self.ltcv_svgplot.addDataset( self.ltcv_filt_datasets[filt] );
                                                   self.ltcv_svgplot.redraw();
                                               }
                                               else
                                                   self.ltcv_svgplot.removeDataset( self.ltcv_filt_datasets[filt] );
                                           }
                                         }
                                       );
            let lab = rkWebUtil.elemaker( "label", span, { "attributes": { "for": "ltcv_checkbox_band" + filt },
                                                           "text": filt + "-band (" + filt_markers[filt] + ")" } );
            rkWebUtil.elemaker( "br", p );

            let mjds = [];
            let mags = [];
            let dmags = [];
            for ( let i in data['ltcv'][filt]['mjd'] ) {
                if ( data['ltcv'][filt]['flux'][i] > 0 ) {
                    mjds.push( data['ltcv'][filt]['mjd'][i] );
                    mags.push( ( -2.5 * Math.log10( data['ltcv'][filt]['flux'][i] ) + data['zp'] ) );
                    dmags.push( 1.0857 * data['ltcv'][filt]['dflux'][i] / data['ltcv'][filt]['flux'][i] );
                }
            }

            let ds = new SVGPlot.Dataset( { 'x': mjds, 'y': mags, 'dy': dmags,
                                            'color': filt_colors[filt], 'highlight_color': '#333333',
                                            'linewid': 2, 'marker': filt_markers[filt]
                                          } );

            this.ltcv_filt_datasets[ filt ] = ds;
        }
        this.ltcv_have_filts = have_filts;

        this.ltcv_svgplot = new SVGPlot.Plot( { "flipy": true,
                                                "xtitle": "MJD",
                                                "ytitle": "Magnitude"
                                              } );
        this.ltcv_plot_div.appendChild( this.ltcv_svgplot.topdiv );
        for ( let ds in this.ltcv_filt_datasets ) {
            this.ltcv_svgplot.addDataset( this.ltcv_filt_datasets[ds] );
        }
    }

}

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.SpecSummary = class extends snanasum.InfoWindow
{
    constructor( collection, topdiv )
    {
        super( collection, topdiv, true, true );

        this.started = false;

        let self = this;
        this.shown_sim = null;

        let p;

        p = rkWebUtil.elemaker( "p", this.topdiv, { "text": "Warning: non-Ia numbers aren't scaled right",
                                                    "classes": [ "bold", "italic" ] } );

        p = rkWebUtil.elemaker( "p", this.topdiv, { "text": "Spectrum strategy: " } );
        this.strat_dropdown = rkWebUtil.elemaker( "select", p );

        p = rkWebUtil.elemaker( "p", this.topdiv );
        rkWebUtil.button( p, "Show", () => { self.update_hist(); } );
        this.which_hist_wid = rkWebUtil.elemaker( "select", p,
                                                  { "change": () => { self.update_hist() } } );
        rkWebUtil.elemaker( "option", this.which_hist_wid, { "text": "Redshift",
                                                             "attributes": { "value": "z",
                                                                             "selected": "selected" } } );
        rkWebUtil.elemaker( "option", this.which_hist_wid, { "text": "Magnitude",
                                                             "attributes": { "value": "mag" } } );
        rkWebUtil.elemaker( "option", this.which_hist_wid, { "text": "S/N",
                                                             "attributes": { "value": "snr" } } );

        p.appendChild( document.createTextNode( " histogram of " ) );
        this.gentype_dropdown = rkWebUtil.elemaker( "select", p,
                                                    { "change": () => { self.update_hist() } } );
        this.update_gentype_dropdown( null, 10 );

        p.appendChild( document.createTextNode( " " ) );
        this.band_dropdown = rkWebUtil.elemaker( "select", p,
                                                 { "change": () => { self.update_hist(); } } );

        p.appendChild( document.createTextNode( " for z=" ) );
        this.z_dropdown = rkWebUtil.elemaker( "select", p,
                                              { "change": () => { self.update_hist() } } );

        p.appendChild( document.createTextNode( " t=" ) );
        this.t_dropdown = rkWebUtil.elemaker( "select", p,
                                              { "change": () => { self.update_hist() } } );


        p.appendChild( document.createTextNode( " m=" ) );
        this.m_dropdown = rkWebUtil.elemaker( "select", p,
                                              { "change": () => { self.update_hist() } } );

        p.appendChild( document.createTextNode( " s/n≥" ) );
        this.snr_dropdown = rkWebUtil.elemaker( "select", p,
                                                { "change": () => { self.update_hist() } } );

        this.update_strat_dropdown( null );
        this.update_dropdowns( null );
        this.strat_dropdown.addEventListener( "change", () => { self.update_dropdowns();
                                                                self.update_hist(); } );

        this.infodiv = rkWebUtil.elemaker( "div", this.topdiv );

        this.started = true;
    }

    update_one_dropdown( dropdown, spechists, mindex, maxdex, deltadex, defbin=0, fixed=0, showhi=true )
    {
        console.log( "update_one_dropdown, deltadex=" + deltadex );
        let self = this;

        let curbin = dropdown.value;
        let n = parseInt( ( spechists[maxdex] - spechists[mindex] ) / spechists[deltadex] + 0.5 );
        if ( ( curbin == null ) || ( curbin == undefined ) || ( curbin == "" ) || ( curbin >= n ) ) curbin = defbin;
        rkWebUtil.wipeDiv( dropdown );
        for ( let i = 0 ; i < n ; ++i ) {
            let lo = spechists[mindex] + i * spechists[deltadex];
            let hi = ( lo + spechists[deltadex] ).toFixed(fixed);
            lo = lo.toFixed(fixed)
            let text = "" + lo;
            if ( showhi )
                text += "–" + hi;
            let option = rkWebUtil.elemaker( "option", dropdown,
                                             { "text": text,
                                               "change": () => { self.update_hist() },
                                               "attributes": { "value": i } } );
            if ( i == curbin ) option.setAttribute( "selected", "selected" );
        }
    }

    update_strat_dropdown( sim )
    {
        console.log( "update_strat_dropdown for sim" + sim );
        if ( sim == null ) sim = this.collection.surveylist[0];

        let spechists = this.collection.surveys[sim]['spechists'];

        let curstrat = this.strat_dropdown.value;
        if ( ( curstrat == null ) || ( curstrat == undefined ) || ( curstrat == "" ) ) curstrat = 0;
        if ( curstrat > spechists['spectrumhists'].length ) curstrat = 0;
        rkWebUtil.wipeDiv( this.start_dropdown );
        for ( let i in spechists['spectrumhists'] ) {
            let text = "";
            for ( let tier in spechists['spectrumhists'][i] ) {
                let texp = spechists['spectrumhists'][i][tier]['texpose'];
                text += "t_exp(" + tier + ")=" + texp + " " ;
            }
            let option = rkWebUtil.elemaker( "option", this.strat_dropdown,
                                             { "text": text,
                                               "attributes": { "value": i } } );
            if ( i == curstrat ) option.setAttribute( "selected", "selected" );
        }
    }

    update_dropdowns( sim )
    {
        console.log( "update_dropdowns for sim " + sim );
        // WARNING -- assumption that the bands and histogram limits are the same
        //   for all tiers.  The latter is true by construction in lib/parse_snana.py,
        //   but the former is set by the sims.  Currently, the sims are all done for
        //   one prism, but that may change.

        let curstrat = this.strat_dropdown.value;

        if ( sim == null ) sim = this.collection.surveylist[0];
        let spechists = this.collection.surveys[sim]['spechists'];

        let tier = Object.keys(spechists['spectrumhists'][curstrat])[0];

        let curband = this.band_dropdown.value;
        if ( ( curband == null ) || ( curband == undefined ) || ( curband == "" ) ) curband = 'H';
        rkWebUtil.wipeDiv( this.band_dropdown );
        for ( let band in spechists['spectrumhists'][curstrat][tier] ) {
            if ( band == 'texpose' ) continue;
            let option = rkWebUtil.elemaker( "option", this.band_dropdown,
                                             { "text": band + "-band",
                                               "attributes": { "value": band } } );
            if ( band == curband ) option.setAttribute( "selected", "selected" );
        }

        // let spectrumhist = spechists['spectrumhists'][curstrat][tier][curband];

        this.update_one_dropdown( this.z_dropdown, spechists,
                                  "zmin", "zmax", "deltaz", 5, 2, true );
        this.update_one_dropdown( this.t_dropdown, spechists,
                                  "tobsmin", "tobsmax", "deltat", 3, 0, true );
        this.update_one_dropdown( this.m_dropdown, spechists,
                                  "mmin", "mmax", "deltam", 4, 1, true );
        this.update_one_dropdown( this.snr_dropdown, spechists,
                                  "snrmin", "snrmax", "deltasnr", 10, 0, false );
    }

    show_sim( sim )
    {
        this.shown_sim = sim;
    }

    update_hist()
    {
        if ( ! this.started ) return;

        rkWebUtil.wipeDiv( this.infodiv );

        let which = this.which_hist_wid.value;
        let curstrat = this.strat_dropdown.value;
        let curband = this.band_dropdown.value;
        let zbin = this.z_dropdown.value;
        let tbin = this.t_dropdown.value;
        let mbin = this.m_dropdown.value;
        let snrbin = this.snr_dropdown.value;
        let gentype = this.gentype_dropdown.value;

        let imgurl = ( "/spechist/" + which + "/" + this.collection.collection + "/"
                       + this.shown_sim + "/" + curstrat
                       + "/tier=__ALL__/zbin=" + zbin + "/tbin=" + tbin
                       + "/magbin=" + mbin + "/snrbin=" + snrbin + "/band=" + curband
                       + "/gentype=" + gentype );

        let img = rkWebUtil.elemaker( "img", this.infodiv,
                                      { "classes": [ "zhist" ],
                                        "attributes": { "src": imgurl,
                                                        "width": 600,
                                                        "height": 500,
                                                        "alt": "[Histogram]" } } );
    }

}

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.SpecPlot = class extends snanasum.InfoWindow
{
    constructor( collection, topdiv )
    {
        super( collection, topdiv, false, false );
        this.shown_sim = null;

        rkWebUtil.elemaker( "p", this.topdiv, { "text": "Spectrum plotting not implemented." } );
    }

    show_sim( sim )
    {
    }
}

// // **********************************************************************
// // **********************************************************************
// // **********************************************************************
//
// snanasum.specSurveyPlotsAndData = function( collection, parentdiv, simname, sim )
// {
//     let metahbox, hbox, vbox, div;
//
//     let self = this;
//
//     this.parentdiv = parentdiv;
//     this.collection = collection;
//     this.simname = simname;
//     this.sim = sim;
//     if ( sim == null ) {
//         window.alert( "Error, sim is null, this shouldn't happen." );
//     }
//
//     this.maindiv = rkWebUtil.elemaker( "div", parentdiv );
//
//     if ( ( ! this.sim.hasOwnProperty( 'spechists' ) ) ||
//          ( ! this.sim.spechists.hasOwnProperty( 'tiers' ) ) ) {
//         let p = rkWebUtil.elemaker( "p", this.maindiv, { "text": "(No spectrum survey info available.)" } );
//         return;
//     }
//
//     metahbox = rkWebUtil.elemaker( "div", this.maindiv, { "classes": [ "hbox" ],
//                                                         "text": "Histogram for: " } );
//     vbox = rkWebUtil.elemaker( "div", metahbox, { "classes": [ "vbox" ] } );
//
//     hbox = rkWebUtil.elemaker( "div", vbox, { "classes": [ "hbox" ] } );
//
//     this.which_hist_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
//     rkWebUtil.elemaker( "option", this.which_hist_dropdown, { "text": "Magnitudes",
//                                                               "attributes": { "value": "mag" } } );
//     rkWebUtil.elemaker( "option", this.which_hist_dropdown, { "text": "S/N",
//                                                               "attributes": { "value": "snr" } } );
//     rkWebUtil.elemaker( "option", this.which_hist_dropdown, { "text": "zHEL",
//                                                               "attributes": { "value": "z",
//                                                                               "selected": "selected" } } );
//     // TODO : t obs?
//
//     this.hist_tier_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
//     rkWebUtil.elemaker( "option", this.hist_tier_dropdown, { "text": "All Tiers",
//                                                              "attributes": { "value": "__ALL__",
//                                                                              "selected": "selected" } } );
//     for ( let tier of Object.keys( this.sim.spechists.tiers ) ) {
//         rkWebUtil.elemaker( "option", this.hist_tier_dropdown, { "text": tier,
//                                                                  "attributes": { "value": tier } } )
//     }
//
//     this.prism_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
//     this.update_prism_dropdown( "__init__" );
//
//     this.band_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
//     rkWebUtil.elemaker( "option", this.band_dropdown, { "text": "Z", "attributes": { "value": "Z" } } );
//     rkWebUtil.elemaker( "option", this.band_dropdown, { "text": "Y", "attributes": { "value": "Y" } } );
//     rkWebUtil.elemaker( "option", this.band_dropdown, { "text": "J", "attributes": { "value": "J",
//                                                                                      "selected": "selected" } } );
//     rkWebUtil.elemaker( "option", this.band_dropdown, { "text": "H", "attributes": { "value": "H" } } );
//
//     this.hist_gentype_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
//     this.update_hist_gentype_dropdown( 10 );
//
//     hbox = rkWebUtil.elemaker( "div", vbox, { "classes": [ "hbox" ] } );
//
//     this.tobswidbox = rkWebUtil.elemaker( "div", hbox );
//     div = rkWebUtil.elemaker( "div", this.tobswidbox, { "classes": [ "hbox" ], "text": "t_obs:" } );
//     this.tobswid = rkWebUtil.elemaker( "select", div, { "change": function() { self.render(); } } );
//     this.update_tobswid( "__init__" );
//
//     this.snrwidbox = rkWebUtil.elemaker( "div", hbox );
//     div = rkWebUtil.elemaker( "div", this.snrwidbox, { "classes": [ "hbox" ], "text": " S/N≥" } );
//     this.snrwid = rkWebUtil.elemaker( "select", div, { "change": function() { self.render(); } } );
//     this.update_snrwid( "__init__" );
//
//     this.zwidbox = rkWebUtil.elemaker( "div", hbox, { "classes": [ "dispnone" ] } );
//     div = rkWebUtil.elemaker( "div", this.zwidbox,{ "classes": [ "hbox" ], "text": " z:" } );
//     this.zwid = rkWebUtil.elemaker( "select", div, { "change": function() { self.render(); } } );
//     this.update_zwid( "__init__" );
//
//     // TODO : mag wid?
//
//     this.infodiv = rkWebUtil.elemaker( "div", this.maindiv );
//
//     this.render();
// };
//
// snanasum.specSurveyPlotsAndData.prototype.update_which_hist_dropdown_side_effects = function()
// {
//     let which = this.which_hist_dropdown.value;
//
//     if ( which == 'mag' ) {
//         this.zwidbox.classList.remove( 'dispnone' );
//         this.snrwidbox.classList.add( 'dispnone' );
//     }
//     else if ( which == 'snr' ) {
//         this.zwidbox.classList.remove( 'dispnone' );
//         this.snrwidbox.classList.add( 'dispnone' );
//     }
//     else if ( which == 'z' ) {
//         this.snrwidbox.classList.remove( 'dispnone' );
//         this.zwidbox.classList.add( 'dispnone' );
//     }
// }
//
// snanasum.specSurveyPlotsAndData.prototype.update_prism_dropdown = function( prism )
// {
//     let tier = this.hist_tier_dropdown.value;
//     if ( tier == "__ALL__" ) tier = Object.keys( this.sim.spechists.tiers )[0];
//
//     let sel;
//     if ( prism == "__init__" ) {
//         sel = Object.keys( this.sim.spechists.tiers[tier] )[0];
//     } else {
//         sel = ( prism == null ) ? this.prism_dropdown.value : prism;
//     }
//
//     let firstoption = null;
//     let foundsel = false;
//
//     rkWebUtil.wipeDiv( this.prism_dropdown );
//     for ( let prismoption of Object.keys( this.sim.spechists.tiers[tier] ) ) {
//         let option = rkWebUtil.elemaker( "option", this.prism_dropdown, { "text": prismoption,
//                                                                           "attributes": { "value": prismoption } } );
//         firstoption = ( firstoption == null ) ? option : firstoption;
//         if ( sel == prismoption ) {
//             option.setAttribute( "selected", "selected" );
//             foundsel = true;
//         }
//     }
//     if ( ! foundsel ) firstoption.setAttribute( "selected", "selected" );
// }
//
// snanasum.specSurveyPlotsAndData.prototype.update_hist_gentype_dropdown = function( gentype ) {
//     let option;
//     let gt10 = null;
//
//     let tier = this.hist_tier_dropdown.value;
//     if ( tier == "__ALL__" ) tier = Object.keys( this.sim.spechists.tiers )[0];
//
//     let prism = this.prism_dropdown.value;
//     let band = this.band_dropdown.value
//
//     let foundsel = false;
//     let sel = ( gentype == null ) ? this.hist_gentype_dropdown.value : gentype;
//
//     rkWebUtil.wipeDiv( this.hist_gentype_dropdown );
//     option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown, { "text": "All Types",
//                                                                          "attributes": { "value": "__ALL__" } } );
//     if ( sel == "__ALL__" ) {
//         option.setAttribute( "selected", "selected" );
//         foundsel = true;
//     }
//     option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown, { "text": "All But Ia",
//                                                                          "attributes": { "value": "__ALLBUTIA__" } } );
//     if ( sel == "__ALLBUTIA__" ) {
//         option.setAttribute( "selected", "selected" );
//         foundsel = true;
//     }
//
//     let gentypes = Array.from( new Set( this.sim.spechists.tiers[tier][prism][band]['GENTYPE'] ) );
//     gentypes.sort();
//
//     for ( let gentype of gentypes ) {
//         option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown,
//                                      { "text": this.sim.gentypemap[gentype],
//                                        "attributes": { "value": gentype } } );
//         if ( gentype == 10 ) gt10 = option;
//         if ( gentype == sel ) {
//             option.setAttribute( "selected", "selected" );
//             foundsel = true;
//         }
//     }
//     if ( ! foundsel ) {
//         if ( gt10 == null ) {
//             window.alert( "Didn't find SNIa! This is...surprising." );
//         } else {
//             gt10.setAttribute( "selected", "selected" );
//         }
//     }
// };
//
// snanasum.specSurveyPlotsAndData.prototype.update_tobswid = function( tobs )
// {
//     let tbin, option;
//
//     let tmin = this.sim.spechists.tobsmin;
//     let tmax = this.sim.spechists.tobsmax;
//     let deltat = this.sim.spechists.deltat;
//     let zerobin = Math.floor( - tmin / deltat );
//
//     if ( tobs == "__init__" ) {
//         tbin = zerobin;
//     } else {
//         if ( tobs != null ) {
//             tbin = Math.floor( ( tobs - tmin ) / deltat + 0.5 );
//         }
//         else {
//             tbin = this.tobswid.value;
//         }
//     }
//
//     rkWebUtil.wipeDiv( this.tobswid )
//     let curtbin = 0;
//     for ( let t = tmin ; t <= tmax ; t += deltat, curtbin += 1 ) {
//         option = rkWebUtil.elemaker( "option", this.tobswid,
//                                      { "text": t.toString() + ".." + (t+deltat).toString() + " d",
//                                        "attributes": { "value": curtbin } } );
//         if ( tbin == curtbin ) {
//             option.setAttribute( "selected", "selected" );
//         }
//     }
// };
//
// snanasum.specSurveyPlotsAndData.prototype.update_snrwid = function( snr )
// {
//     let option, snrbin;
//
//     let snrmin = this.sim.spechists.snrmin;
//     let snrmax = this.sim.spechists.snrmax;
//     let deltasnr = this.sim.spechists.deltasnr;
//
//     if ( snr == "__init__" ) snr = 0;
//     if ( snr == null ) snrbin = this.snrwid.value;
//     else snrbin = Math.floor( ( snr - snrmin ) / deltasnr + 0.5 );
//
//     rkWebUtil.wipeDiv( this.snrwid );
//     let cursnrbin = 0;
//     for ( let s = snrmin ; s <= snrmax ; s += deltasnr, cursnrbin += 1 ) {
//         option = rkWebUtil.elemaker( "option", this.snrwid,
//                                      { "text": s,
//                                        "attributes": { "value": cursnrbin } } );
//         if ( snrbin == cursnrbin ) {
//             option.setAttribute( "selected", "selected" );
//         }
//     }
// }
//
// snanasum.specSurveyPlotsAndData.prototype.update_zwid = function( z )
// {
//     let option, zbin;
//
//     let zmin = this.sim.spechists.zmin;
//     let zmax = this.sim.spechists.zmax;
//     let deltaz = this.sim.spechists.deltaz;
//
//     if ( z == "__init__" ) zbin = 5;
//     if ( z == null ) zbin = this.zwid.value;
//     else zbin = Math.floor( ( z - zmin ) / deltaz + 0.5 );
//
//     rkWebUtil.wipeDiv( this.zwid );
//     let curzbin = 0;
//     for ( let curz = zmin; curz <= zmax ; curz += deltaz, curzbin += 1 ) {
//         option = rkWebUtil.elemaker( "option", this.zwid,
//                                      { "text": curz.toFixed(2) + "-" + (curz+deltaz).toFixed(2),
//                                        "attributes": { "value": curzbin } } );
//         if ( zbin == curzbin ) {
//             option.setAttribute( "selected", "selected" );
//         }
//     }
// };
//
// snanasum.specSurveyPlotsAndData.prototype.render = function()
// {
//     rkWebUtil.wipeDiv( this.infodiv );
//
//     let p = rkWebUtil.elemaker( "p", this.invodiv,
//                                 { "text": "Warning: core-collapse SNe numbers are not scaled right. " +
//                                   "Also, the 'debug' collection just has a subset of object counts for everything.",
//                                   "classes": [ "italic" ] } );
//     let div = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "zhist-img-container" ] } );
//
//     this.update_which_hist_dropdown_side_effects();
//     this.update_prism_dropdown( null );
//     this.update_hist_gentype_dropdown( null );
//     this.update_tobswid( null );
//     this.update_snrwid( null );
//     this.update_zwid( null );
//
//     let whichplot = this.which_hist_dropdown.value;
//     let tier = this.hist_tier_dropdown.value;
//     let prism = this.prism_dropdown.value;
//     let band = this.band_dropdown.value;
//     let gentype = this.hist_gentype_dropdown.value;
//     let tobsbin = this.tobswid.value;
//     let snrbin = this.snrwid.value;
//     let zbin = this.zwid.value;
//
//     let imgurl = "/spechist/" + whichplot + "/" + this.collection.collection + "/" + this.simname
//         + "/tbin=" + tobsbin + "/snrbin=" + snrbin + "/zbin=" + zbin + "/gentype=" + gentype
//         + "/tier=" + tier + "/prism=" + prism + "/band=" + band;
//     // console.log( "Asking for image " + imgurl );
//     let img = rkWebUtil.elemaker( "img", div,
//                                   { "classes": [ "zhist" ],
//                                     "attributes": { "src": imgurl,
//                                                     "width": 600,
//                                                     "height": 500,
//                                                     "alt": "[spectrum histogram]" } } );
//
//
// };


export {snanasum}
