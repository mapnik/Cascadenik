.rail.line[tunnel!=yes][tunnel!=true][zoom>=17]
{
    line-pattern-file: url('img/rail-wide.png');
}

.rail.line[tunnel!=yes][tunnel!=true][zoom=16]
{
    line-pattern-file: url('img/rail-normal.png');
}

.rail.line[tunnel!=yes][tunnel!=true][zoom>=14][zoom<=15]
{
    line-pattern-file: url('img/rail-medium.png');
}

.rail.line[tunnel!=yes][tunnel!=true][zoom>=12][zoom<=13]
{
    line-pattern-file: url('img/rail-narrow.png');
}

.rail.point[zoom>=15] name
{
    text-face-name: "DejaVu Sans Book";
    text-size: 12;
    text-fill: #000;
    text-placement: point;
}

.rail.point[zoom>=15]
{
    point-file: url('img/station-large.png');
    point-allow-overlap: true;
}

.rail.point[zoom>=17] name
{
    text-size: 12;
    text-halo-radius: 2;
    text-wrap-width: 65;
    text-dy: 20;
}

.rail.point[zoom>=15][zoom<=16] name
{
    text-size: 9;
    text-halo-radius: 1;
    text-wrap-width: 50;
    text-dy: 19;
}

.rail.point[zoom>=12][zoom<=14]
{
    point-file: url('img/station-small.png');
    /* point-allow-overlap: true; */
}
