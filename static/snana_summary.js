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

    h3 = rkWebUtil.elemaker( "h3", this.maindiv, { "text": "Show simulation collection: " } );
    this.collectionwidget = rkWebUtil.elemaker( "select", h3 );
    let first = false;
    for ( let collection of this.collections ) {
        let option = rkWebUtil.elemaker( "option", this.collectionwidget,
                                         { "text": collection,
                                           "attributes": { "value": collection } } );
        if ( first ) {
            option.setAttribute( "selected", "selected" );
            first = false;
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
    var self = this;

    rkWebUtil.wipeDiv( this.maindiv );
    this.contentdiv = rkWebUtil.elemaker( "div", this.maindiv );

    let div = rkWebUtil.elemaker( "div", this.contentdiv, { "classes": [ "main_hbox" ] } );
    this.tabdiv = rkWebUtil.elemaker( "div", div, { "classes": [ "tabdiv" ] } );
    this.infodiv = rkWebUtil.elemaker( "div", div, { "classes": [ "infodiv" ] } );
    
    if ( this.sortkeys == null ) {
        this.sortkeys = [ "FoM_stat" ];
        this.sortorders = [ -1 ];
        let firstsurvey = Object.keys( this.surveys )[0]
        this.sorttier = Object.keys( this.surveys[firstsurvey].tiers )[0]
    }

    let sortables = [ 'FoM_stat', 'filters', 'nvisit', 'ntile', 'dt_visit', 'zSNRMATCH' ]
    
    let p = rkWebUtil.elemaker( "p", this.tabdiv, { "text": "Sort rows based on values for: " } );
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
    th = rkWebUtil.elemaker( "th", tr, { "text": "z target" } );

    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "zSNRMATCH", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "zSNRMATCH", -1 ) } } );
    // th = rkWebUtil.elemaker( "th", tr, { "text": "λ range" } );
    // th = rkWebUtil.elemaker( "th", tr, { "text": "S/N" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "Filters" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "filters", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "filters", -1 ) } } );
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
    th = rkWebUtil.elemaker( "th", tr, { "text": "dt (days)" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "dt_visit", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "dt_visit", -1 ) } } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "FoM_stat" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "FoM_stat", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "FoM_stat", -1 ) } } );
    
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
            td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].ntile } )
            td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].nvisit } )
            td = rkWebUtil.elemaker( "td", tr, { "text": survey.tiers[tier].dt_visit } )
            
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
    let self = this;
    
    let table, tr, th, td, h3, h4, hbox, div, p;
    
    rkWebUtil.wipeDiv( this.infodiv );
    let img = rkWebUtil.elemaker( "img", this.infodiv,
                                  { "attributes": { "src": "/snzhist/" + this.collection + "/" + sim,
                                                    "width": 600,
                                                    "height": 500,
                                                    "alt": "[z Histogram]" } } );

    let text = sim + " ; FoM = " + this.surveys[sim].muopt[0].FoM_stat
    h3 = rkWebUtil.elemaker( "h3", this.infodiv, { "text": text } );

    hbox = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "hbox2emgap" ] } )
    
    table = rkWebUtil.elemaker( "table", hbox );
    tr = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", tr, { "text": "Season" } );
    rkWebUtil.elemaker( "th", tr, { "text": "mjd_0" } );
    rkWebUtil.elemaker( "th", tr, { "text": "mjd_1" } );
    rkWebUtil.elemaker( "th", tr, { "text": "Δmjd" } );
    for ( let row in this.surveyinfo['MJD_SEASON'] ) {
        let season = this.surveyinfo['MJD_SEASON'][row];
        tr = rkWebUtil.elemaker( "tr", table );
        rkWebUtil.elemaker( "td", tr, { "text": row } );
        rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd0 } );
        rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd1 } );
        rkWebUtil.elemaker( "td", tr, { "text": season.season_mjd1 - season.season_mjd0 } );
        
    }

    table = rkWebUtil.elemaker( "table", hbox );
    tr = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", tr, { "text": "Σt_obs" } );
    rkWebUtil.elemaker( "td", tr, { "text": this.surveyinfo['TIME_SUM_OBS'] } );
    tr = rkWebUtil.elemaker( "tr", table );
    rkWebUtil.elemaker( "th", tr, { "text": "f_reject" } );
    rkWebUtil.elemaker( "td", tr, { "text": this.surveyinfo['RANDOM_REJECT_OBS'] } );
    
    hbox = rkWebUtil.elemaker( "div", this.infodiv, { "classes": [ "hbox2emgap" ] } );

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
    for ( let tier of Object.keys( this.surveys[sim].tiers ) ) {
        let tierinfo = this.surveys[sim].tiers[tier];
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

    // p = rkWebUtil.elemaker( "p", this.infodiv,
    //                         { "text": "Numbers above include the low-z survey.  Numbers below " +
    //                           "are only from Roman." } );
    
    // table = rkWebUtil.elemaker( "table", this.infodiv );
    // tr = rkWebUtil.elemaker( "tr", table );
    // th = rkWebUtil.elemaker( "th", tr, { "text": "z" } );
    // for ( let tier of Object.keys( this.tier[sim] ) ) {
    //     th = rkWebUtil.elemaker( "td", tr, { "text": tier } );
    // }
    // for ( let z of Object.keys( this.zhist[sim][Object.keys(this.tier[sim])[0]][0] ) ) {
    //     tr = rkWebUtil.elemaker( "tr", table );
    //     td = rkWebUtil.elemaker( "td", tr, { "text": Math.round( z * 10 ) / 10 } );
    //     for ( let tier of Object.keys( this.tier[sim] ) ) {
    //         td = rkWebUtil.elemaker( "td", tr, { "text": this.zhist[sim][tier][0][z].n } );
    //     }
    // }
}
    
export {snanasum}
