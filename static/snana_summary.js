import { rkWebUtil } from "./rkwebutil.js";

// Namespace

var snanasum = {};

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.Context = function()
{
    this.collections = null;
    this.collectiondivs = {};
};

snanasum.Context.filter_order = { 'R': 0,
                                  'Z': 1,
                                  'Y': 2,
                                  'J': 3,
                                  'H': 4,
                                  'F': 5,
                                  'K': 6 }

snanasum.Context.filter_sort = function( a, b ) {
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

snanasum.Context.prototype.renderpage = function()
{
    var self = this;

    if ( this.collections == null ) {
        let connector = new rkWebUtil.Connector( "/collections" );
        connector.sendHttpRequest( "", {}, function( r ) { self.parse_collections_and_render( r ); } );
    }
    else {
        this.actually_renderpage();
    }
};

snanasum.Context.prototype.parse_collections_and_render = function( data )
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
};

snanasum.Context.prototype.actually_renderpage = function( data )
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
};

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.Collection = function( collection, maindiv )
{
    this.maindiv = maindiv;
    this.collection = collection;
    this.surveylist = null;
    this.tierlist = null;
    this.sortkeys = null;
    this.shown_hist_sim = null;
    this.photinfodivs = {};
    this.specinfodivs = {};
};

snanasum.Collection.prototype.renderpage = function()
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
};

snanasum.Collection.prototype.parse_summary_info_and_render = function( data )
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
};

snanasum.Collection.prototype.get_filter_str = function( sim, tier ) {
    let filters = [];
    for ( let filt of Object.keys( this.surveys[sim]['tiers'][tier]['bands'] ) ) {
        if ( this.surveys[sim]['tiers'][tier]['bands'][filt] > 0 ) {
            filters.push( filt );
        }
    }
    filters.sort( snanasum.Context.filter_sort );
    return filters.join();
};

snanasum.Collection.prototype.actually_renderpage = function( data )
{
    var div, p, option, button;

    var self = this;

    rkWebUtil.wipeDiv( this.maindiv );
    this.contentdiv = rkWebUtil.elemaker( "div", this.maindiv );

    div = rkWebUtil.elemaker( "div", this.contentdiv, { "classes": [ "main_hbox" ] } );

    // tabdiv on the left holds the sortable list of sims
    this.tabdiv = rkWebUtil.elemaker( "div", div, { "classes": [ "tabdiv" ] } );

    // metainfodiv on the right holds divs for individual sims
    this.metainfodiv = rkWebUtil.elemaker( "div", div, { "classes": [ "metainfodiv" ] } );

    div = rkWebUtil.elemaker( "div", this.metainfodiv, { "classes": [ "infodivtabs" ] } );
    this.photbutton = rkWebUtil.elemaker( "button", div, { "text": "Phot Survey Info",
                                                           "click": function() {
                                                               self.infodiv.removeChild( self.infodiv.firstChild );
                                                               self.infodiv.appendChild( self.photdiv );
                                                               self.specbutton.classList.remove( "seltab" );
                                                               self.specbutton.classList.add( "unseltab" );
                                                               self.photbutton.classList.remove( "unseltab" );
                                                               self.photbutton.classList.add( "seltab" );
                                                           },

                                                           "classes": [ "seltab" ] } );
    this.specbutton = rkWebUtil.elemaker( "button", div, { "text": "Spec Survey Info",
                                                           "click": function() {
                                                               self.infodiv.removeChild( self.infodiv.firstChild );
                                                               self.infodiv.appendChild( self.specdiv );
                                                               self.photbutton.classList.remove( "seltab" );
                                                               self.photbutton.classList.add( "unseltab" );
                                                               self.specbutton.classList.remove( "unseltab" );
                                                               self.specbutton.classList.add( "seltab" );
                                                           },
                                                           "classes": [ "unseltab" ] } );
    this.infodiv = rkWebUtil.elemaker( "div", this.metainfodiv );

    this.photdiv = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "infodiv" ] } );
    this.specdiv = rkWebUtil.elemaker( "div", null, { "classes": [ "infodiv" ] } );
    
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

    this.sim_table = rkWebUtil.elemaker( "table", this.tabdiv );

    this.render_sim_table( );
}

snanasum.Collection.prototype.render_sim_table = function() {
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

    tr = rkWebUtil.elemaker( "tr", this.sim_table );
    th = rkWebUtil.elemaker( "th", tr, { "text": "Sim" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "Tier" } );

    th = rkWebUtil.elemaker( "th", tr, { "text": "z" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "zSNRMATCH", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "zSNRMATCH", -1 ) } } );
    rkWebUtil.elemaker( "br", th );
    rkWebUtil.elemaker( "text", th, { "text": "targ" } );

    th = rkWebUtil.elemaker( "th", tr, { "text": "Bands" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "filters", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "filters", -1 ) } } );

    th = rkWebUtil.elemaker( "th", tr, { "text": "Area" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "area", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "area", -1 ) } } );
    rkWebUtil.elemaker( "br", th );
    rkWebUtil.elemaker( "text", th, { "text": "□°" } );

    th = rkWebUtil.elemaker( "th", tr, { "text": "ntile" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "ntile", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "ntile", -1 ) } } );

    th = rkWebUtil.elemaker( "th", tr, { "text": "nvisit" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "nvisit", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "nvisit", -1 ) } } );

    th = rkWebUtil.elemaker( "th", tr, { "text": "dt" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "dt_visit", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "dt_visit", -1 ) } } );
    rkWebUtil.elemaker( "br", th );
    rkWebUtil.elemaker( "text", th, { "text": "(days)" } );

    th = rkWebUtil.elemaker( "th", tr, { "text": "FoM" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "FoM_stat", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "FoM_stat", -1 ) } } );
    rkWebUtil.elemaker( "br", th );
    rkWebUtil.elemaker( "text", th, { "text": "(stat)" } );

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
                let textnode = rkWebUtil.elemaker( "span", td, { "text": sim,
                                                                 "classes": [ "link" ],
                                                                 "click": function(e) { self.showSim(sim); } } );
                whichcolor = 1 - whichcolor;
            }
            let cls = (whichcolor == 1) ? "lotsfaded" : "mostfaded";
            tr.classList.add( cls );
            td = rkWebUtil.elemaker( "td", tr, { "text": tier } );
            td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].zSNRMATCH } );

            td = rkWebUtil.elemaker( "td", tr, { "text": this.get_filter_str( sim, tier ) } );
            td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].area } );
            td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].ntile } );
            td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].nvisit } );
            td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].dt_visit } );

            // WARNING : hardcoding muopt[0]
            if ( firstofsim ) {
                firstofsim = false;
                td = rkWebUtil.elemaker( "td", tr, { "text": survey.muopt[0].FoM_stat,
                                                     "attributes": { "rowspan": Object.keys(survey.tiers).length }
                                                   } );
            }
        }
    }
};

snanasum.Collection.prototype.changeSortTier = function() {
    let newtier = this.which_tier_sort.value;
    if ( newtier != this.sorttier ) {
        this.sorttier = newtier;
        this.render_sim_table( this.sortkeys, this.sortorders );
    }
}

snanasum.Collection.prototype.addSortKey = function( sortkey, order ) {
    let i = this.sortkeys.indexOf( sortkey );
    if (  i >= 0 ) {
        this.sortkeys.splice( i, 1 );
        this.sortorders.splice( i, 1 );
    }
    this.sortkeys.unshift( sortkey );
    this.sortorders.unshift( order );
    this.render_sim_table( this.sortkeys, this.sortorders );
};

snanasum.Collection.prototype.showSim = function( sim ) {
    while ( this.photdiv.firstChild )
        this.photdiv.removeChild( this.photdiv.firstChild );
    if ( this.photinfodivs.hasOwnProperty( sim ) ) {
        this.photdiv.appendChild( this.photinfodivs[ sim ].maindiv );
    }
    else {
        this.photinfodivs[ sim ] = new snanasum.photSurveyPlotsAndData( this, this.photdiv,
                                                                        sim, this.surveys[sim] );
    }

    while ( this.specdiv.firstChild )
        this.specdiv.removeChild( this.specdiv.firstChild );
    if ( this.specinfodivs.hasOwnProperty( sim ) ) {
        this.specdiv.appendChild( this.specinfodivs[ sim ].maindiv );
    }
    else {
        this.specinfodivs[ sim ] = new snanasum.specSurveyPlotsAndData( this, this.specdiv,
                                                                        sim, this.surveys[sim] );
    }
    
}

snanasum.Collection.prototype.renderCollectionInfo = function( parent, collection, sim )
{
    let table, tr, td, div, hbox, p;
    
    hbox = rkWebUtil.elemaker( "div", parent, { "classes": [ "hbox2emgap" ] } )

    table = rkWebUtil.elemaker( "table", hbox );
    tr = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", tr, { "text": "Season" } );
    rkWebUtil.elemaker( "th", tr, { "text": "mjd_0" } );
    rkWebUtil.elemaker( "th", tr, { "text": "mjd_1" } );
    rkWebUtil.elemaker( "th", tr, { "text": "Δmjd" } );
    for ( let row in collection.surveyinfo['MJD_SEASON'] ) {
        let season = collection.surveyinfo['MJD_SEASON'][row];
        tr = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "td", tr, { "text": row } );
        rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd0 } );
        rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd1 } );
        rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd1 - season.season_mjd0 } );

    }

    table = rkWebUtil.elemaker( "table", hbox );
    tr = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", tr, { "text": "Σt_obs" } );
    rkWebUtil.elemaker( "td", tr, { "text": collection.surveyinfo['TIME_SUM_OBS'] } );
    tr = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", tr, { "text": "f_reject" } );
    rkWebUtil.elemaker( "td", tr, { "text": collection.surveyinfo['RANDOM_REJECT_OBS'] } );

    hbox = rkWebUtil.elemaker( "div", parent, { "classes": [ "hbox2emgap" ] } );

    div = rkWebUtil.elemaker( "div", hbox );
    table = rkWebUtil.elemaker( "table", div );
    let trtiers = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", trtiers, { "text": "Tier" } );
    let trntile = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", trntile, { "text": "ntile" } );
    let trnvisit = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", trnvisit, { "text": "nvisit" } );
    let trarea = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", trarea, { "text": "Area" } );
    let trzsn = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", trzsn, { "text": "z_S/N" } );
    let tropenfrac = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", tropenfrac, { "text": "Openfrac" } );
    let trfilters = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", trfilters, { "text": "t_exp (s)" } );
    for ( let tier of Object.keys( sim.tiers ) ) {
        let tierinfo = sim.tiers[tier];
        td = rkWebUtil.elemaker( "th", trtiers, { "text": tier } );
        td = rkWebUtil.elemaker( "td", trntile, { "text": tierinfo.ntile } );
        td = rkWebUtil.elemaker( "td", trnvisit, { "text": tierinfo.nvisit } );
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

    p = rkWebUtil.elemaker( "p", parent,
                            { "text": "The FoM above includes the low-z survey.  Numbers below " +
                                      "are only from Roman.",
                              "classes": [ "bold" ] } );
}

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.photSurveyPlotsAndData = function( collection, parentdiv, simname, sim )
{
    let self = this;
    
    this.parentdiv = parentdiv;
    this.collection = collection;
    this.simname = simname;
    this.sim = sim;
    if ( sim == null ) {
        window.alert( "Error, sim is null, this shouldn't happen." )
        return;
    }

    this.maindiv = rkWebUtil.elemaker( "div", parentdiv );
    
    let p = rkWebUtil.elemaker( "p", this.maindiv, { "text": "Histogram for " } );

    this.hist_tier_dropdown = rkWebUtil.elemaker( "select", p, { "change": ( function() { self.render(); } ) } );
    rkWebUtil.elemaker( "option", this.hist_tier_dropdown, { "text": "All Tiers",
                                                             "attributes": { "value": "__ALL__",
                                                                             "selected": "selected" } } );
    for ( let tier of Object.keys( this.sim['tiers'] ) ) {
        rkWebUtil.elemaker( "option", this.hist_tier_dropdown, { "text": tier,
                                                                 "attributes": { "value": tier } } )
    }
    this.hist_gentype_dropdown = rkWebUtil.elemaker( "select", p, { "change": ( function() { self.render(); } ) } );
    this.update_hist_gentype_dropdown( 10 );

    this.sncut_dropdown = rkWebUtil.elemaker( "select", p, { "change": ( function() { self.render(); } ) } );
    rkWebUtil.elemaker( "option", this.sncut_dropdown, { "text": "All detections",
                                                         "attributes": { "value": "zhist",
                                                                         "selected": "selected" } } );
    rkWebUtil.elemaker( "option", this.sncut_dropdown, { "text": "Highest S/N band S/N>5",
                                                         "attributes": { "value": "snrmaxzhist" } } );
    rkWebUtil.elemaker( "option", this.sncut_dropdown, { "text": "2nd highest S/N color S/N>5",
                                                         "attributes": { "value": "snrmax2zhist" } } );
    rkWebUtil.elemaker( "option", this.sncut_dropdown, { "text": "3rd highest S/N color S/N>5",
                                                         "attributes": { "value": "snrmax3zhist" } } );

    this.infodiv = rkWebUtil.elemaker( "div", this.maindiv );

    this.render();
}
    

snanasum.photSurveyPlotsAndData.prototype.render = function()
{
    let self = this;

    let table, tr, th, td, h3, h4, hbox, div, p;

    rkWebUtil.wipeDiv( this.infodiv );

    p = rkWebUtil.elemaker( "p", this.infodiv,
                            { "text": "Warning: core-collapse SNe numbers are not scaled right.",
                              "classes": [ "italic" ] } );

    div = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "zhist-img-container" ] } );

    let whichtier = this.hist_tier_dropdown.value;
    let gentype = this.hist_gentype_dropdown.value;
    let sncut = this.sncut_dropdown.value;

    let imgurl = "/snzhist/" + this.collection.collection + "/" + this.simname
        + "/whichhist=" + sncut
        + "/gentype=" + gentype
        + "/tier=" + whichtier;
    // console.log( "Asking for image " + imgurl );
    let img = rkWebUtil.elemaker( "img", div,
                                  { "classes": [ "zhist" ],
                                    "attributes": { "src": imgurl,
                                                    "width": 600,
                                                    "height": 500,
                                                    "alt": "[z Histogram]" } } );

    this.collection.renderCollectionInfo( this.infodiv, this.collection, this.sim );
    
    if ( sncut == "zhist" )
        var hist = this.sim.zhist;
    else if ( sncut == "snrmaxzhist" )
        var hist = this.sim.snrmaxzhist;
    else if ( sncut == "snrmax2zhist" )
        var hist = this.sim.snrmax2zhist;
    else if ( sncut == "snrmax3zhist" )
        var hist = this.sim.snrmax3zhist;
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
            for ( let gentype in this.sim.gentypemap ) {
                tier_gentype_zs_ns[tier][gentype] = { z: [], n: [] };
            }
        }
        tier_gentype_zs_ns[ tier ][ gentype ].z.push( hist.zCMB[i] );
        tier_gentype_zs_ns[ tier ][ gentype ].n.push( hist.n[i] );
    }

    for ( let tier of Object.keys( this.sim.tiers ) ) {
        rkWebUtil.elemaker( "h4", this.infodiv, { "text": "Tier " + tier } );

        table = rkWebUtil.elemaker( "table", this.infodiv );
        tr = rkWebUtil.elemaker( "tr", table );
        th = rkWebUtil.elemaker( "th", tr, { "text": "z_CMB" } );
        for ( let gentype in this.sim.gentypemap )
            th = rkWebUtil.elemaker( "th", tr, { "text": this.sim.gentypemap[gentype] } );

        for ( let i in tier_gentype_zs_ns[tier][gt0].z ) {
            let z = tier_gentype_zs_ns[tier][gt0].z[i];
            tr = rkWebUtil.elemaker( "tr", table );
            th = rkWebUtil.elemaker( "th", tr, { "text": Math.round( z * 10 ) / 10 } );
            for ( let gentype in this.sim.gentypemap ) {
                if ( z != tier_gentype_zs_ns[tier][gentype].z[i] ) {
                    console.log( "ERROR: tier " + tier + " gentype z list mismatch: " +
                                 "i=" + i + ", z_" + gt0 + "=" +z + ", z_" + gentype + "=" +
                                 tier_gentype_zs_ns[tier][gentype].z[i] );
                }
                td = rkWebUtil.elemaker( "td", tr,
                                         { "text": tier_gentype_zs_ns[tier][gentype].n[i] } );
            }
        }
    }
}

snanasum.photSurveyPlotsAndData.prototype.update_hist_gentype_dropdown = function( curval=null ) {
    let option;

    if ( curval == null ) curval = this.hist_gentype_dropdown.value;
    rkWebUtil.wipeDiv( this.hist_gentype_dropdown );
    option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown, { "text": "All Types",
                                                                         "attributes": { "value": "__ALL__" } } );
    if ( curval == "__ALL__" ) option.setAttribute( "selected", "selected" );
    option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown, { "text": "All But Ia",
                                                                         "attributes": { "value": "__ALLBUTIA__" } } );
    if ( curval == "__ALLBUTIA__" ) option.setAttribute( "selected", "selected" );

    for ( let gentype of Object.keys( this.sim.gentypemap ) ) {
        option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown,
                                     { "text": this.sim.gentypemap[gentype],
                                       "attributes": { "value": gentype } } );
        if ( curval == gentype ) option.setAttribute( "selected", "selected" );
    }
}

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.specSurveyPlotsAndData = function( collection, parentdiv, simname, sim )
{
    let metahbox, hbox, vbox, div;
    
    let self = this;

    this.parentdiv = parentdiv;
    this.collection = collection;
    this.simname = simname;
    this.sim = sim;
    if ( sim == null ) {
        window.alert( "Error, sim is null, this shouldn't happen." );
    }

    this.maindiv = rkWebUtil.elemaker( "div", parentdiv );

    if ( ( ! this.sim.hasOwnProperty( 'spechists' ) ) ||
         ( ! this.sim.spechists.hasOwnProperty( 'tiers' ) ) ) {
        let p = rkWebUtil.elemaker( "p", this.maindiv, { "text": "(No spectrum survey info available.)" } );
        return;
    }
    
    metahbox = rkWebUtil.elemaker( "div", this.maindiv, { "classes": [ "hbox" ],
                                                        "text": "Histogram for: " } );
    vbox = rkWebUtil.elemaker( "div", metahbox, { "classes": [ "vbox" ] } );

    hbox = rkWebUtil.elemaker( "div", vbox, { "classes": [ "hbox" ] } );
    
    this.which_hist_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
    rkWebUtil.elemaker( "option", this.which_hist_dropdown, { "text": "Magnitudes",
                                                              "attributes": { "value": "mag" } } );
    rkWebUtil.elemaker( "option", this.which_hist_dropdown, { "text": "S/N",
                                                              "attributes": { "value": "snr" } } );
    rkWebUtil.elemaker( "option", this.which_hist_dropdown, { "text": "zHEL",
                                                              "attributes": { "value": "z",
                                                                              "selected": "selected" } } );
    // TODO : t obs?
    
    this.hist_tier_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
    rkWebUtil.elemaker( "option", this.hist_tier_dropdown, { "text": "All Tiers",
                                                             "attributes": { "value": "__ALL__",
                                                                             "selected": "selected" } } );
    for ( let tier of Object.keys( this.sim.spechists.tiers ) ) {
        rkWebUtil.elemaker( "option", this.hist_tier_dropdown, { "text": tier,
                                                                 "attributes": { "value": tier } } )
    }

    this.prism_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
    this.update_prism_dropdown( "__init__" );

    this.band_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
    rkWebUtil.elemaker( "option", this.band_dropdown, { "text": "Z", "attributes": { "value": "Z" } } );
    rkWebUtil.elemaker( "option", this.band_dropdown, { "text": "Y", "attributes": { "value": "Y" } } );
    rkWebUtil.elemaker( "option", this.band_dropdown, { "text": "J", "attributes": { "value": "J",
                                                                                     "selected": "selected" } } );
    rkWebUtil.elemaker( "option", this.band_dropdown, { "text": "H", "attributes": { "value": "H" } } );
    
    this.hist_gentype_dropdown = rkWebUtil.elemaker( "select", hbox, { "change": function() { self.render(); } } );
    this.update_hist_gentype_dropdown( 10 );

    hbox = rkWebUtil.elemaker( "div", vbox, { "classes": [ "hbox" ] } );

    this.tobswidbox = rkWebUtil.elemaker( "div", hbox );
    div = rkWebUtil.elemaker( "div", this.tobswidbox, { "classes": [ "hbox" ], "text": "t_obs:" } );
    this.tobswid = rkWebUtil.elemaker( "select", div, { "change": function() { self.render(); } } );
    this.update_tobswid( "__init__" );

    this.snrwidbox = rkWebUtil.elemaker( "div", hbox );
    div = rkWebUtil.elemaker( "div", this.snrwidbox, { "classes": [ "hbox" ], "text": " S/N≥" } );
    this.snrwid = rkWebUtil.elemaker( "select", div, { "change": function() { self.render(); } } );
    this.update_snrwid( "__init__" );

    this.zwidbox = rkWebUtil.elemaker( "div", hbox, { "classes": [ "dispnone" ] } );
    div = rkWebUtil.elemaker( "div", this.zwidbox,{ "classes": [ "hbox" ], "text": " z:" } );
    this.zwid = rkWebUtil.elemaker( "select", div, { "change": function() { self.render(); } } );
    this.update_zwid( "__init__" );

    // TODO : mag wid?

    this.infodiv = rkWebUtil.elemaker( "div", this.maindiv );

    this.render();
};

snanasum.specSurveyPlotsAndData.prototype.update_which_hist_dropdown_side_effects = function()
{
    let which = this.which_hist_dropdown.value;

    if ( which == 'mag' ) {
        this.zwidbox.classList.remove( 'dispnone' );
        this.snrwidbox.classList.add( 'dispnone' );
    }
    else if ( which == 'snr' ) {
        this.zwidbox.classList.remove( 'dispnone' );
        this.snrwidbox.classList.add( 'dispnone' );
    }
    else if ( which == 'z' ) {
        this.snrwidbox.classList.remove( 'dispnone' );
        this.zwidbox.classList.add( 'dispnone' );
    }
}

snanasum.specSurveyPlotsAndData.prototype.update_prism_dropdown = function( prism )
{
    let tier = this.hist_tier_dropdown.value;
    if ( tier == "__ALL__" ) tier = Object.keys( this.sim.spechists.tiers )[0];

    let sel;
    if ( prism == "__init__" ) {
        sel = Object.keys( this.sim.spechists.tiers[tier] )[0];
    } else {
        sel = ( prism == null ) ? this.prism_dropdown.value : prism;
    }

    let firstoption = null;
    let foundsel = false;
    
    rkWebUtil.wipeDiv( this.prism_dropdown );
    for ( let prismoption of Object.keys( this.sim.spechists.tiers[tier] ) ) {
        let option = rkWebUtil.elemaker( "option", this.prism_dropdown, { "text": prismoption,
                                                                          "attributes": { "value": prismoption } } );
        firstoption = ( firstoption == null ) ? option : firstoption;
        if ( sel == prismoption ) {
            option.setAttribute( "selected", "selected" );
            foundsel = true;
        }
    }
    if ( ! foundsel ) firstoption.setAttribute( "selected", "selected" );
}

snanasum.specSurveyPlotsAndData.prototype.update_hist_gentype_dropdown = function( gentype ) {
    let option;
    let gt10 = null;
    
    let tier = this.hist_tier_dropdown.value;
    if ( tier == "__ALL__" ) tier = Object.keys( this.sim.spechists.tiers )[0];

    let prism = this.prism_dropdown.value;
    let band = this.band_dropdown.value
    
    let foundsel = false;
    let sel = ( gentype == null ) ? this.hist_gentype_dropdown.value : gentype;

    rkWebUtil.wipeDiv( this.hist_gentype_dropdown );
    option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown, { "text": "All Types",
                                                                         "attributes": { "value": "__ALL__" } } );
    if ( sel == "__ALL__" ) {
        option.setAttribute( "selected", "selected" );
        foundsel = true;
    }
    option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown, { "text": "All But Ia",
                                                                         "attributes": { "value": "__ALLBUTIA__" } } );
    if ( sel == "__ALLBUTIA__" ) {
        option.setAttribute( "selected", "selected" );
        foundsel = true;
    }

    let gentypes = Array.from( new Set( this.sim.spechists.tiers[tier][prism][band]['GENTYPE'] ) );
    gentypes.sort();

    for ( let gentype of gentypes ) {
        option = rkWebUtil.elemaker( "option", this.hist_gentype_dropdown,
                                     { "text": this.sim.gentypemap[gentype],
                                       "attributes": { "value": gentype } } );
        if ( gentype == 10 ) gt10 = option;
        if ( gentype == sel ) {
            option.setAttribute( "selected", "selected" );
            foundsel = true;
        }
    }
    if ( ! foundsel ) {
        if ( gt10 == null ) {
            window.alert( "Didn't find SNIa! This is...surprising." );
        } else {
            gt10.setAttribute( "selected", "selected" );
        }
    }
};

snanasum.specSurveyPlotsAndData.prototype.update_tobswid = function( tobs )
{
    let tbin, option;

    let tmin = this.sim.spechists.tobsmin;
    let tmax = this.sim.spechists.tobsmax;
    let deltat = this.sim.spechists.deltat;
    let zerobin = Math.floor( - tmin / deltat );
    
    if ( tobs == "__init__" ) {
        tbin = zerobin;
    } else {
        if ( tobs != null ) {
            tbin = Math.floor( ( tobs - tmin ) / deltat + 0.5 );
        }
        else {
            tbin = this.tobswid.value;
        }
    }

    rkWebUtil.wipeDiv( this.tobswid )
    let curtbin = 0;
    for ( let t = tmin ; t <= tmax ; t += deltat, curtbin += 1 ) {
        option = rkWebUtil.elemaker( "option", this.tobswid,
                                     { "text": t.toString() + ".." + (t+deltat).toString() + " d",
                                       "attributes": { "value": curtbin } } );
        if ( tbin == curtbin ) {
            option.setAttribute( "selected", "selected" );
        }
    }
};

snanasum.specSurveyPlotsAndData.prototype.update_snrwid = function( snr )
{
    let option, snrbin;
    
    let snrmin = this.sim.spechists.snrmin;
    let snrmax = this.sim.spechists.snrmax;
    let deltasnr = this.sim.spechists.deltasnr;

    if ( snr == "__init__" ) snr = 0;
    if ( snr == null ) snrbin = this.snrwid.value;
    else snrbin = Math.floor( ( snr - snrmin ) / deltasnr + 0.5 );

    rkWebUtil.wipeDiv( this.snrwid );
    let cursnrbin = 0;
    for ( let s = snrmin ; s <= snrmax ; s += deltasnr, cursnrbin += 1 ) {
        option = rkWebUtil.elemaker( "option", this.snrwid,
                                     { "text": s,
                                       "attributes": { "value": cursnrbin } } );
        if ( snrbin == cursnrbin ) {
            option.setAttribute( "selected", "selected" );
        }
    }
}

snanasum.specSurveyPlotsAndData.prototype.update_zwid = function( z )
{
    let option, zbin;

    let zmin = this.sim.spechists.zmin;
    let zmax = this.sim.spechists.zmax;
    let deltaz = this.sim.spechists.deltaz;

    if ( z == "__init__" ) zbin = 5;
    if ( z == null ) zbin = this.zwid.value;
    else zbin = Math.floor( ( z - zmin ) / deltaz + 0.5 );

    rkWebUtil.wipeDiv( this.zwid );
    let curzbin = 0;
    for ( let curz = zmin; curz <= zmax ; curz += deltaz, curzbin += 1 ) {
        option = rkWebUtil.elemaker( "option", this.zwid,
                                     { "text": curz.toFixed(2) + "-" + (curz+deltaz).toFixed(2),
                                       "attributes": { "value": curzbin } } );
        if ( zbin == curzbin ) {
            option.setAttribute( "selected", "selected" );
        }
    }
};

snanasum.specSurveyPlotsAndData.prototype.render = function()
{
    rkWebUtil.wipeDiv( this.infodiv );

    let p = rkWebUtil.elemaker( "p", this.invodiv,
                                { "text": "Warning: core-collapse SNe numbers are not scaled right. " +
                                  "Also, the 'debug' collection just has a subset of object counts for everything.",
                                  "classes": [ "italic" ] } );
    let div = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "zhist-img-container" ] } );

    this.update_which_hist_dropdown_side_effects();
    this.update_prism_dropdown( null );
    this.update_hist_gentype_dropdown( null );
    this.update_tobswid( null );
    this.update_snrwid( null );
    this.update_zwid( null );
    
    let whichplot = this.which_hist_dropdown.value;
    let tier = this.hist_tier_dropdown.value;
    let prism = this.prism_dropdown.value;
    let band = this.band_dropdown.value;
    let gentype = this.hist_gentype_dropdown.value;
    let tobsbin = this.tobswid.value;
    let snrbin = this.snrwid.value;
    let zbin = this.zwid.value;

    let imgurl = "/spechist/" + whichplot + "/" + this.collection.collection + "/" + this.simname
        + "/tbin=" + tobsbin + "/snrbin=" + snrbin + "/zbin=" + zbin + "/gentype=" + gentype
        + "/tier=" + tier + "/prism=" + prism + "/band=" + band;
    // console.log( "Asking for image " + imgurl );
    let img = rkWebUtil.elemaker( "img", div,
                                  { "classes": [ "zhist" ],
                                    "attributes": { "src": imgurl,
                                                    "width": 600,
                                                    "height": 500,
                                                    "alt": "[spectrum histogram]" } } );


};

// **********************************************************************
// **********************************************************************
// **********************************************************************

export {snanasum}
