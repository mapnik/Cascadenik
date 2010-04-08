- Usage -

Run `make` to download a copy of cssutils, or get it directly from the source:

    http://code.google.com/p/cssutils/

Unroll the rules in example.mss and show their cascade order:

    % python cascadenik-style.py example.mss > example-ordered-unrolled.mss

Compile example.mml into a Mapnik-suitable XML file:

    % python cascadenik-compile.py example.mml > example-compiled.xml

Render a MML file directly to an image using nik2img.py:

    % nik2img.py example.mml example.png

Will write more here later.
