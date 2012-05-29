Cascadenik
==========

Cascadenik implements cascading stylesheets for Mapnik.

It’s an abstraction layer and preprocessor that converts special, CSS-like
syntax into Mapnik-compatible style definitions. It’s easier to write complex
style rules using the alternative syntax, because it allows for separation of
symbolizers and provides a mechanism for inheritance.

Cascadenik supports many of Mapnik’s features in a simple declarative form:

    /* Define a few colors */
    @black: #000;
    @orange: #f90;
    
    /* Start with a white background */
    Map
    {
        map-bgcolor: #fff;
    }
    
    /* Draw roads as orange lines */
    #roads
    {
        /* Usually, 3px wide */
        line-width: 3;
        line-color: @orange;
        
        /* Make the important ones wider */
        &[kind=major] { line-width: 4 }
        &[kind=highway] { line-width: 5 }
        
        /* Add the road names in black */
        name
        {
            text-placement: line;
            text-face-name: "DejaVu Sans Book";
            text-fill: @black;
            text-size: 12;
        }
    }

See more examples at https://github.com/mapnik/Cascadenik/wiki/Examples.

Usage
-----

See `INSTALL.md` for installation instructions.

See the `doc/` folder for more usage examples.

Unroll the rules in example.mss and show their cascade order:

    % cascadenik-style.py example.mss > example-ordered-unrolled.mss

Compile `example.mml` into a Mapnik-suitable XML file:

    % cascadenik-compile.py example.mml example-compiled.xml

Render a MML file directly to an image using nik2img.py:

    % nik2img.py example.mml example.png
