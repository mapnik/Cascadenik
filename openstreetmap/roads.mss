.road
{
    line-cap: round;
    line-join: miter;
    outline-cap: butt;
    outline-join: miter;
}

.road.outline[tunnel=yes],
.road.outline[tunnel=true]
{
    line-cap: butt;
    line-dasharray: 4,6;
}

.road.inline[zoom>=14][prominence=major][bridge=true],
.road.inline[zoom>=14][prominence=major][bridge=yes],
.road.inline[zoom>=16][bridge=true],
.road.inline[zoom>=16][bridge=yes]
{
    outline-width: 1;
}

/*
.road.inline[zoom>=13][prominence=major][bridge=yes],
.road.inline[zoom>=13][prominence=major][bridge=true]
{
    outline-width: 1;
    outline-color: #888;
}
*/

/** Road Weights **/

.motorway.inline[zoom>=9][zoom<=11][highway=trunk] { line-width: 2; }
.motorway.outline[zoom>=9][zoom<=11][highway=trunk] { line-width: 4; }
.motorway.inline[zoom>=7][zoom<=11][highway=motorway] { line-width: 2; }
.motorway.outline[zoom>=7][zoom<=11][highway=motorway] { line-width: 4; }

.road.inline[zoom>=7][zoom<=11][prominence=major][highway=motorway] { line-width: 2; }
.road.outline[zoom>=7][zoom<=11][prominence=major][highway=motorway] { line-width: 4; }

.road.texture[zoom>=7][zoom<=10] { line-width: 1; } /* general background fuzz */

.road.inline[zoom>=7][zoom<=10][prominence=major][highway=motorway] { line-width: 2; }
.road.inline[zoom>=11][zoom<=12][prominence=major][highway!=motorway_link] { line-width: 2; }
.road.outline[zoom>=11][zoom<=12][prominence=major][highway!=motorway_link] { line-width: 4; }

.road.texture[zoom>=11][zoom<=12] { line-width: 1; }

.road.inline[zoom=13][prominence=major] { line-width: 5; }
.road.outline[zoom=13][prominence=major] { line-width: 7; }
.road.inline[zoom=13][prominence=major][highway=motorway_link] { line-width: 2; }
.road.outline[zoom=13][prominence=major][highway=motorway_link] { line-width: 4; }

.road.texture[zoom=13] { line-width: 1; }

.road.inline[zoom=14][prominence=major] { line-width: 7; }
.road.outline[zoom=14][prominence=major] { line-width: 9; }
.road.inline[zoom=14][prominence=major][highway=motorway_link] { line-width: 2; }
.road.outline[zoom=14][prominence=major][highway=motorway_link] { line-width: 4; }

.road.inline[zoom=14][prominence=minor][highway=tertiary] { line-width: 3; }
.road.outline[zoom=14][prominence=minor][highway=tertiary] { line-width: 5; }
.road.texture[zoom=14] { line-width: 2; }

.road.inline[zoom=15][prominence=major] { line-width: 11; }
.road.outline[zoom=15][prominence=major] { line-width: 13; }
.road.inline[zoom=15][prominence=major][highway=motorway_link] { line-width: 4; }
.road.outline[zoom=15][prominence=major][highway=motorway_link] { line-width: 6; }

.road.inline[zoom=15][prominence=minor][highway=tertiary] { line-width: 6; }
.road.outline[zoom=15][prominence=minor][highway=tertiary] { line-width: 8; }
.road.inline[zoom=15][prominence=minor][highway!=tertiary][highway!=service] { line-width: 4; }
.road.outline[zoom=15][prominence=minor][highway!=tertiary][highway!=service] { line-width: 6; }
.road.inline[zoom=15][prominence=minor][highway=service] { line-width: 2; }
.road.outline[zoom=15][prominence=minor][highway=service] { line-width: 4; }

.road.inline[zoom=16][prominence=major] { line-width: 13; }
.road.outline[zoom=16][prominence=major] { line-width: 15; }
.road.outline[zoom=16][prominence=major][highway=motorway] { line-width: 17; }
.road.inline[zoom=16][prominence=major][highway=motorway_link] { line-width: 8; }
.road.outline[zoom=16][prominence=major][highway=motorway_link] { line-width: 10; }

.road.inline[zoom=16][prominence=minor][highway!=service] { line-width: 8; }
.road.outline[zoom=16][prominence=minor][highway!=service] { line-width: 10; }
.road.inline[zoom=16][prominence=minor][highway=service] { line-width: 6; }
.road.outline[zoom=16][prominence=minor][highway=service] { line-width: 8; }

.road.inline[zoom>=17] { line-width: 15; }
.road.outline[zoom>=17] { line-width: 17; }
.road.outline[zoom>=17][highway=motorway] { line-width: 19; }
.road.inline[zoom>=17][highway=service],
.road.inline[zoom>=17][highway=motorway_link] { line-width: 10; }
.road.outline[zoom>=17][highway=service],
.road.outline[zoom>=17][highway=motorway_link] { line-width: 12; }



.road.label[zoom>=15][oneway=1][highway!=motorway],
.road.label[zoom>=15][oneway=yes][highway!=motorway],
.road.label[zoom>=15][oneway=true][highway!=motorway]
{
    line-pattern-file: url('img/oneway-arrow.png');
}

.road.inline[highway=motorway][zoom>=15]
{
    inline-width: 1;
    inline-color: #ff9460;
    inline-dasharray: 12, 12;
}

.road.inline[highway=motorway][zoom=16]
{
    inline-color: #ffad78;
}

.road.inline[highway=motorway][zoom>=17]
{
    inline-color: #f9c38d;
}



/** Road Labels **/

.road.label.major[zoom=12][highway=trunk] name,
.road.label.major[zoom=12][highway=primary] name,
.road.label.major[zoom=12][highway=secondary] name,
.road.label.major[zoom>=13][zoom<=14][highway!=motorway][highway!=motorway_link] name,
.road.label.minor[zoom=13][highway=tertiary] name,
.road.label[zoom>=14][highway!=motorway][highway!=motorway_link] name
{
    text-face-name: "DejaVu Sans Book";
    text-size: 9;
    text-fill: #000;
    text-placement: line;
    text-halo-radius: 1;
    text-halo-fill: #fff;
    text-max-char-angle-delta: 20;
    text-min-distance: 50;
    text-spacing: 400;
}

.road.label.minor[zoom>=13][zoom<=14] name
{
    text-halo-fill: #dceee9 !important;
}

.road.label[zoom>=17][highway!=motorway][highway!=motorway_link] name 
{
    text-size: 12 !important;
}

.road.label.major[zoom>=9][highway=trunk] ref_content,
.road.label.major[zoom>=11][highway=primary] ref_content,
.road.label.major[zoom>=7][highway=motorway] ref_content
{
    shield-face-name: "DejaVu Sans Bold";
    shield-min-distance: 100;
    shield-size: 9;
    shield-fill: #000;
}

.road.label.major[zoom>=9][ref_length=2][highway=trunk] ref_content,
.road.label.major[zoom>=11][ref_length=2][highway=primary] ref_content,
.road.label.major[zoom>=7][ref_length=2][highway=motorway] ref_content { shield-file: url('img/horizontal-shield-2.png'); }
.road.label.major[zoom>=9][ref_length=3][highway=trunk] ref_content,
.road.label.major[zoom>=11][ref_length=3][highway=primary] ref_content,
.road.label.major[zoom>=7][ref_length=3][highway=motorway] ref_content { shield-file: url('img/horizontal-shield-3.png'); }
.road.label.major[zoom>=9][ref_length=4][highway=trunk] ref_content,
.road.label.major[zoom>=11][ref_length=4][highway=primary] ref_content,
.road.label.major[zoom>=7][ref_length=4][highway=motorway] ref_content { shield-file: url('img/horizontal-shield-4.png'); }
.road.label.major[zoom>=9][ref_length=5][highway=trunk] ref_content,
.road.label.major[zoom>=11][ref_length=5][highway=primary] ref_content,
.road.label.major[zoom>=7][ref_length=5][highway=motorway] ref_content { shield-file: url('img/horizontal-shield-5.png'); }
.road.label.major[zoom>=9][ref_length=6][highway=trunk] ref_content,
.road.label.major[zoom>=11][ref_length=6][highway=primary] ref_content,
.road.label.major[zoom>=7][ref_length=6][highway=motorway] ref_content { shield-file: url('img/horizontal-shield-6.png'); }
.road.label.major[zoom>=9][ref_length=7][highway=trunk] ref_content,
.road.label.major[zoom>=11][ref_length=7][highway=primary] ref_content,
.road.label.major[zoom>=7][ref_length=7][highway=motorway] ref_content { shield-file: url('img/horizontal-shield-7.png'); }
.road.label.major[zoom>=9][ref_length=8][highway=trunk] ref_content,
.road.label.major[zoom>=11][ref_length=8][highway=primary] ref_content,
.road.label.major[zoom>=7][ref_length=8][highway=motorway] ref_content { shield-file: url('img/horizontal-shield-8.png'); }
.road.label.major[zoom>=9][ref_length=9][highway=trunk] ref_content,
.road.label.major[zoom>=11][ref_length=9][highway=primary] ref_content,
.road.label.major[zoom>=7][ref_length=9][highway=motorway] ref_content { shield-file: url('img/horizontal-shield-9.png'); }



/** Road Colors **/

.road.inline
{
    line-color: #f8f8f8;
    line-opacity: 1;
}

.road.outline
{
    line-color: #d2d2d2;
    line-opacity: 1;
}

.road.inline[highway=tertiary]
{
    line-color: #ffffff;
}

.road.outline[highway=tertiary]
{
    line-color: #c3c3c3;
}

.road.inline[highway=secondary]
{
    line-color: #fdffdd;
}

.road.outline[highway=secondary]
{
    line-color: #b5b880;
}

.motorway.inline[highway=trunk],
.road.inline[highway=trunk],
.road.inline[highway=primary]
{
    line-color: #ffec9f;
}

.motorway.outline[highway=trunk],
.road.outline[highway=trunk],
.road.outline[highway=primary]
{
    line-color: #b1a67b;
}

.road.inline[highway=motorway_link]
{
    line-color: #ff9460;
}

.road.outline[highway=motorway_link]
{
    line-color: #6d8aa7;
}

.motorway.inline[highway=motorway],
.road.inline[highway=motorway]
{
    line-color: #ff5559;
}

.motorway.outline[highway=motorway],
.road.outline[highway=motorway]
{
    line-color: #03317d;
}

/* lighten the motorways up a bit at higher zoom levels */
.road.inline[zoom=16][highway=motorway] { line-color: #ff7775; }
.road.inline[zoom>=17][highway=motorway] { line-color: #ff9d98; }
.road.outline[zoom>=16][highway=motorway] { line-color: #6c7dd5; }
.road.inline[zoom=16][highway=motorway_link] { line-color: #ffad78; }
.road.inline[zoom>=17][highway=motorway_link] { line-color: #f9c38d; }

/* all repeated from above but applicable to bridges specifically */
.road.inline { outline-color: #d2d2d2; }
.road.inline[highway=tertiary] { outline-color: #c3c3c3; }
.road.inline[highway=secondary] { outline-color: #b5b880; }
.motorway.inline[highway=trunk], .road.inline[highway=trunk], .road.inline[highway=primary] { outline-color: #b1a67b; }
.road.inline[highway=motorway_link] { outline-color: #6d8aa7; }
.motorway.inline[highway=motorway], .road.inline[highway=motorway] { outline-color: #03317d; }
.road.inline[highway=motorway] { outline-color: #03317d; }
.road.inline[zoom>=16][highway=motorway] { outline-color: #6c7dd5; }



.road.texture[zoom>=7][zoom<=11]
{
    line-color: #b6cccb;
    line-opacity: 1;
}

.road.texture[zoom>=12][zoom<=14]
{
    line-color: #5f6e6d;
    line-opacity: 0.37;
}
