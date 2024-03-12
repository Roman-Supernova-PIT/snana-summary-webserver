import { rkWebUtil } from "./rkwebutil.js";

// Namespace

var snanasum = {};

// **********************************************************************
// **********************************************************************
// **********************************************************************

snanasum.Context = function()
{
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

    this.sims.sort( function( a, b ) { 
        if ( self.cosmo[ a ].fom > self.cosmo[b].fom ) return 1;
        else if ( self.cosmo[a].fom < self.cosmo[b].fom ) return -1;
        else return 0; } );

    var table, tr, th, td;
    
    table = rkWebUtil.elemaker( "table", this.contentdiv );
    tr = rkWebUtil.elemaker( "tr", table );
    th = rkWebUtil.elemaker( "th", tr, { "text": "Sim" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "Tier" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "z of S/N" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "λ range" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "S/N" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "Filters" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "Exptime" } );
    th = rkWebUtil.elemaker( "th", tr, { "text": "FoM" } );
    for ( let sim of this.sims ) {
        tr = rkWebUtil.elemaker( "tr", table );
        let firstsim = true;
        for ( let tier in this.tier[sim] ) {
            if ( firstsim ) {
                td = rkWebUtil.elemaker( "td", tr, { "text": sim,
                                                     "attributes": { "rowspan": this.tier[sim].length } } );
            }
            td = rkWebUtil.elemaker( "td", tr, { "text": tier } );

            let snrtext = ""
            let lamrange = ""
            let first = true
            for ( let ordinal in this.snrmax[sim] ) {
                if ( !first ) {
                    snrtext += "<br>";
                    lamrange += "<br>";
                    first = false;
                }
                snrtext += this.snrmax[sim][ordinal].snr
                lamrange += String( this.snrmax[sim][ordinal].lam0 ) + "—" +
                    String( this.snrmax[sim][ordinal].lam1 )
            }
            td = rkWebUtil.elemaker( "td", tr, { "text": snrtext } )
            td = rkWebUtil.elemaker( "td", tr, { "text": lamrange } )
        }
    }
};

export {snanasum}
