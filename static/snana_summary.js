import { rkWebUtil } from "./rkwebutil.js";

// Namespace

var snanasum = {};

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.Context = function()
{
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

snanasum.Context.prototype.get_filter_str = function( sim, tier ) {
    let filters = [];
    for ( let filt of Object.keys( this.obs[sim][tier] ) ) {
        if ( this.obs[sim][tier][filt].EXPTIME > 0 ) {
            filters.push( filt );
        }
    }
    filters.sort( snanasum.Context.filter_sort );
    return filters.join();
};

snanasum.Context.prototype.renderpage = function()
{
    var self = this;
    let connector = new rkWebUtil.Connector( "/summarydata" );
    connector.sendHttpRequest( "", {}, function( resp ) { self.actually_renderpage( resp ); } );
};

snanasum.Context.prototype.actually_renderpage = function( data )
{
    var self = this;

    this.shown = null;

    this.info = data.info;
    this.snrmax = data.snrmax;
    this.tier = data.tier;
    this.obs = data.obs;
    this.zhist = data.zhist;
    this.cosmo = data.cosmo;

    this.sims = Object.keys( this.cosmo );
    
    this.maindiv = document.getElementById( "pagebody" );

    let topdiv = rkWebUtil.elemaker( "div", this.maindiv );
    
    var p = rkWebUtil.elemaker( "p", topdiv );
    var a = rkWebUtil.elemaker( "a", p, { 'text': "Sims By FoM",
                                          'classes': [ 'link' ],
                                          'click': function() { self.show_by_fom(); } } );
    rkWebUtil.elemaker( "hr", this.maindiv );

    this.contentdiv = rkWebUtil.elemaker( "div", this.maindiv );
    this.show_by_fom();

};

snanasum.Context.prototype.show_by_fom = function()
{
    if ( this.shown == "by fom" ) return;

    var self = this;
    
    rkWebUtil.wipeDiv( this.contentdiv );
    let div = rkWebUtil.elemaker( "div", this.contentdiv, { "classes": [ "byfom_hbox" ] } );
    this.byfom_tabdiv = rkWebUtil.elemaker( "div", div, { "classes": [ "byfom_tabdiv" ] } );
    this.byfom_infodiv = rkWebUtil.elemaker( "div", div, { "classes": [ "byfom_infodiv" ] } );
    
    // WARNING : hardcoding fitpopt=0, mu=0
    var fitopt = 0;
    var mu = 0;

    this.sortkeys = [ "FoM" ];
    this.sortorders = [ -1 ];
    this.sorttier = Object.keys( this.tier[this.sims[0]] )[0];

    let p = rkWebUtil.elemaker( "p", this.byfom_tabdiv, { "text": "Sort rows based on values for: " } );
    this.byfom_which_tier_sort = rkWebUtil.elemaker( "select", p );
    let first = false;
    for ( let tier of Object.keys( this.tier[this.sims[0]] ) ) {
        let option = rkWebUtil.elemaker( "option", this.byfom_which_tier_sort,
                                         { "text": tier,
                                           "attributes": { "value": tier } } );
        if ( first ) {
            option.setAttribute( "selected", "selected" );
            first = false;
        }
    }
    this.byfom_which_tier_sort.addEventListener( "change", function() { self.changeSortTier() } );

    this.byfom_table = rkWebUtil.elemaker( "table", this.byfom_tabdiv );
    
    this.render_sim_table( this.sortkeys, this.sortorders );
}

snanasum.Context.prototype.render_sim_table = function( sortkeys, sortorders ) {
    var self = this;

    // WARNING : hardcoding fitopt=0, mu=0
    var fitopt = 0;
    var mu = 0;

    rkWebUtil.wipeDiv( this.byfom_table );
    
    this.sims.sort( function( a, b ) {
        for ( let i in sortkeys ) {
            let key = sortkeys[i];
            let order = sortorders[i];

            if ( key == 'FoM' ) {
                if ( self.cosmo[a][fitopt][mu].FoM > self.cosmo[b][fitopt][mu].FoM ) return 1 * order;
                else if ( self.cosmo[a][fitopt][mu].FoM < self.cosmo[b][fitopt][mu].FoM ) return -1 * order;
            }
            else if ( key == "filters" ) {
                let filta = self.get_filter_str( a, self.sorttier );
                let filtb = self.get_filter_str( b, self.sorttier );
                if ( filta > filtb ) return 1 * order;
                else if ( filta < filtb ) return -1 * order;
            }
            else {
                if ( self.tier[a][self.sorttier][key] > self.tier[b][self.sorttier][key] ) return 1 * order;
                else if ( self.tier[a][self.sorttier][key] < self.tier[b][self.sorttier][key] ) return -1 * order;
            }
        }
        return 0;
    } );
                
    var table, tr, th, td, p;

    tr = rkWebUtil.elemaker( "tr", this.byfom_table );
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
    th = rkWebUtil.elemaker( "th", tr, { "text": "FoM" } );
    rkWebUtil.elemaker( "span", th, { "text": "▲", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "FoM", 1 ) } } );
    rkWebUtil.elemaker( "span", th, { "text": "▼", "classes": [ "link" ],
                                      "click": function() { self.addSortKey( "FoM", -1 ) } } );
    
    let whichcolor = 0;
    for ( let sim of this.sims ) {
        let firstsim = true;
        for ( let tier in this.tier[sim] ) {
            tr = rkWebUtil.elemaker( "tr", this.byfom_table );
            if ( firstsim ) {
                td = rkWebUtil.elemaker( "td", tr, { "attributes": { "rowspan": Object.keys(this.tier[sim]).length }
                                                   } );
                let textnode = rkWebUtil.elemaker( "span", td, { "text": sim,
                                                                 "classes": [ "link" ],
                                                                 "click": function(e) { self.showSim(sim); } } );
                whichcolor = 1 - whichcolor;
            }
            let cls = (whichcolor == 1) ? "lotsfaded" : "mostfaded";
            tr.classList.add( cls );
            td = rkWebUtil.elemaker( "td", tr, { "text": tier } );
            td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].zSNRMATCH } );
            
            // let lamtd = rkWebUtil.elemaker( "td", tr );
            // let snrtd = rkWebUtil.elemaker( "td", tr );
            // let first = true;
            // for ( let ordinal in this.snrmax[sim] ) {
            //     if ( !first ) {
            //         snrtd.appendChild( document.createElement( "br" ) );
            //         lamtd.appendChild( document.createElement( "br" ) );
            //     } else {
            //         first = false;
            //     }
            //     snrtd.appendChild( document.createTextNode( this.snrmax[sim][ordinal].snr ) );
            //     lamtd.appendChild( document.createTextNode( String( this.snrmax[sim][ordinal].lam0 ) + "—" +
            //                                                 String( this.snrmax[sim][ordinal].lam1 ) ) )
            // }

            td = rkWebUtil.elemaker( "td", tr, { "text": this.get_filter_str( sim, tier ) } );
            td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].ntile } )
            td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].nvisit } )
            td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].dt_visit } )
            
            // WARNING : hardcoding fitopt=0, mu=0
            if ( firstsim ) {
                firstsim = false;
                td = rkWebUtil.elemaker( "td", tr, { "text": this.cosmo[sim][fitopt][mu].FoM,
                                                     "attributes": { "rowspan": Object.keys(this.tier[sim]).length }
                                                   } );
            }
        }
    }
};

snanasum.Context.prototype.changeSortTier = function() {
    let newtier = this.byfom_which_tier_sort.value;
    if ( newtier != this.sorttier ) {
        this.sorttier = newtier;
        this.render_sim_table( this.sortkeys, this.sortorders );
    }
}

snanasum.Context.prototype.addSortKey = function( sortkey, order ) {
    let i = this.sortkeys.indexOf( sortkey );
    if (  i >= 0 ) {
        this.sortkeys.splice( i, 1 );
        this.sortorders.splice( i, 1 );
    }
    this.sortkeys.unshift( sortkey );
    this.sortorders.unshift( order );
    this.render_sim_table( this.sortkeys, this.sortorders );
};


snanasum.Context.prototype.showSim = function( sim ) {
    let self = this;
    
    let table, tr, th, td, h3, h4, hbox, div, p;
    
    rkWebUtil.wipeDiv( this.byfom_infodiv );
    let img = rkWebUtil.elemaker( "img", this.byfom_infodiv,
                                  { "attributes": { "src": "/snzhist/" + sim + "/0/0",
                                                    "width": 600,
                                                    "height": 500,
                                                    "alt": "[z Histogram]" } } );

    let text = sim + " ; FoM = " + this.cosmo[sim][0][0].FoM;
    h3 = rkWebUtil.elemaker( "h3", this.byfom_infodiv, { "text": text } );
    text = "t_sum_obs (d)=" + this.info[sim].TIME_SUM_OBS + ", " +
    "t_sum_season (?)=" + this.info[sim].TIME_SUM_SEASON + ", " +
        "f_rej=" + this.info[sim].RANDOM_REJECT_OBS + ", " +
        "t_slew (s)=" + this.info[sim].TIME_SLEW;
    p = rkWebUtil.elemaker( "p", this.byfom_infodiv, { "text": text } );
    
    hbox = rkWebUtil.elemaker( "div", this.byfom_infodiv, { "classes": [ "hbox2emgap" ] } );

    for ( let tier of Object.keys( this.tier[sim] ) ) {
        div = rkWebUtil.elemaker( "div", hbox );
        table = rkWebUtil.elemaker( "table", div );
        tr = rkWebUtil.elemaker( "tr", table );
        th = rkWebUtil.elemaker( "th", tr, { "text": "tier" } );
        td = rkWebUtil.elemaker( "td", tr, { "text": tier } );
        tr = rkWebUtil.elemaker( "tr", table );
        th = rkWebUtil.elemaker( "th", tr, { "text": "ntile" } );
        td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].ntile } );
        tr = rkWebUtil.elemaker( "tr", table );
        th = rkWebUtil.elemaker( "th", tr, { "text": "nvisit" } );
        td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].nvisit } );
        tr = rkWebUtil.elemaker( "tr", table );
        th = rkWebUtil.elemaker( "th", tr, { "text": "Area" } );
        td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].Area } );
        tr = rkWebUtil.elemaker( "tr", table );
        th = rkWebUtil.elemaker( "th", tr, { "text": "z_S/N" } );
        td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].zSNRMATCH } );
        tr = rkWebUtil.elemaker( "tr", table );
        th = rkWebUtil.elemaker( "th", tr, { "text": "OpenFrac" } );
        td = rkWebUtil.elemaker( "td", tr, { "text": this.tier[sim][tier].OpenFrac } );

        let filters = [];
        for ( let filt of Object.keys( this.obs[sim][tier] ) ) {
            if ( this.obs[sim][tier][filt].EXPTIME > 0 ) {
                filters.push( filt );
            }
        }
        filters.sort( snanasum.Context.filter_sort );

        for ( let filt of filters ) {
            tr = rkWebUtil.elemaker( "tr", table );
            th = rkWebUtil.elemaker( "th", tr, { "text": "t_exp (" + filt + ") (s)" } )
            td = rkWebUtil.elemaker( "td", tr, { "text": this.obs[sim][tier][filt].EXPTIME } );
        }
    }

    p = rkWebUtil.elemaker( "p", this.byfom_infodiv,
                            { "text": "Numbers above include the low-z survey.  Numbers below " +
                              "are only from Roman." } );
    
    table = rkWebUtil.elemaker( "table", this.byfom_infodiv );
    tr = rkWebUtil.elemaker( "tr", table );
    th = rkWebUtil.elemaker( "th", tr, { "text": "z" } );
    for ( let tier of Object.keys( this.tier[sim] ) ) {
        th = rkWebUtil.elemaker( "td", tr, { "text": tier } );
    }
    for ( let z of Object.keys( this.zhist[sim][Object.keys(this.tier[sim])[0]][0] ) ) {
        tr = rkWebUtil.elemaker( "tr", table );
        td = rkWebUtil.elemaker( "td", tr, { "text": Math.round( z * 10 ) / 10 } );
        for ( let tier of Object.keys( this.tier[sim] ) ) {
            td = rkWebUtil.elemaker( "td", tr, { "text": this.zhist[sim][tier][0][z].n } );
        }
    }
}
    
export {snanasum}
