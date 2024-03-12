import { snanasum } from "./snana_summary.js"

// **********************************************************************
// **********************************************************************
// **********************************************************************
// Here is the thing that will make the code run when the document has loaded

snanasum.started = false

// console.log("About to window.setInterval...");
snanasum.init_interval = window.setInterval(
    function()
    {
        var requestdata, renderer
        
        if (document.readyState == "complete")
        {
            // console.log( "document.readyState is complete" );
            if ( !snanasum.started )
            {
                snanasum.started = true;
                window.clearInterval( snanasum.init_interval );
                renderer = new snanasum.Context();
                renderer.renderpage();
            }
        }
    },
    100);

export { }
