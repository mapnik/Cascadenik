.rail.line[zoom>=17][tunnel!=yes][tunnel!=true] { line-pattern-file: url('img/rail-wide.png'); }
.rail.line[zoom=16][tunnel!=yes][tunnel!=true]  { line-pattern-file: url('img/rail-normal.png'); }
.rail.line[zoom>=14][zoom<=15][tunnel!=yes][tunnel!=true] { line-pattern-file: url('img/rail-medium.png'); }
.rail.line[zoom>=12][zoom<=13][tunnel!=yes][tunnel!=true] { line-pattern-file: url('img/rail-narrow.png'); }

.rail.line[zoom>=14][tunnel!=yes][tunnel!=true][bridge=yes],
.rail.line[zoom>=14][tunnel!=yes][tunnel!=true][bridge=true]
{
    line-color: #e4f7f2;
    outline-color: #d2d2d2;
    outline-width: 1;
}

.rail.line[zoom>=17][bridge=yes],
.rail.line[zoom>=17][bridge=true] { line-width: 16; }

.rail.line[zoom=16][bridge=yes],
.rail.line[zoom=16][bridge=true] { line-width: 13; }

.rail.line[zoom>=14][zoom<=15][bridge=yes],
.rail.line[zoom>=14][zoom<=15][bridge=true] { line-width: 8; }

.rail.point[zoom>=15] name
{
    text-face-name: "DejaVu Sans Book";
    text-size: 12;
    text-fill: #000;
    text-placement: point;
}

.rail.point[zoom>=17]
{
    point-file: url('img/icons/24x24/symbol/transport/railway=station.png');
    point-allow-overlap: true;
    text-dy: 20;
}

.rail.point[zoom>=15][zoom<=16]
{
    point-file: url('img/icons/16x16/symbol/transport/railway=station.png');
    point-allow-overlap: true;
    text-dy: 15;
}

.rail.point[zoom>=17] name
{
    text-size: 12;
    text-halo-radius: 2;
    text-wrap-width: 65;
}

.rail.point[zoom>=15][zoom<=16] name
{
    text-size: 9;
    text-halo-radius: 1;
    text-wrap-width: 50;
}

.rail.point[zoom>=12][zoom<=14]
{
    point-file: url('img/icons/12x12/symbol/transport/railway=station.png');
    /* point-allow-overlap: true; */
}
