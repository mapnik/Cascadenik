- Usage -

* See INSTALL.txt for installation instructions. *

* See the doc/ folder for more usage examples *

Unroll the rules in example.mss and show their cascade order:

    % cascadenik-style.py example.mss > example-ordered-unrolled.mss

Compile example.mml into a Mapnik-suitable XML file:

    % cascadenik-compile.py example.mml > example-compiled.xml

Render a MML file directly to an image using nik2img.py:

    % nik2img.py example.mml example.png
