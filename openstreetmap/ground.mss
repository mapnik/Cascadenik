Map
{
    map-bgcolor: #8cb6d3;
}

.coast.edge.outer
{
    line-width: 13;
    line-color: #a1cbea;
    line-join: round;
}

.coast.edge.inner
{
    line-width: 5;
    line-color: #7eaac1;
    line-join: round;
}

.coast.edge.outer[zoom<=12] { line-width: 9; }
.coast.edge.inner[zoom<=12] { line-width: 3; }

.water.area
{
    line-width: 2;
    line-color: #7eaac1;
    polygon-fill: #8cb6d3;
    line-join: round;
}

.water.line
{
    line-color: #8cb6d3;
    line-join: round;

    outline-color: #7eaac1;
    outline-join: round;
}

.water.line[zoom>=13][waterway=river] { outline-width: 1; }
.water.line[zoom>=15][waterway=stream] { outline-width: 1; }

.water.line[zoom>=11][zoom<=12][waterway=stream] { line-width: 1; }
.water.line[zoom>=11][zoom<=12][waterway=river] { line-width: 2; }

.water.line[zoom=13][waterway=stream] { line-width: 1; }
.water.line[zoom=13][waterway=river] { line-width: 3; }

.water.line[zoom=14][waterway=stream] { line-width: 2; }
.water.line[zoom=14][waterway=river] { line-width: 5; }

.water.line[zoom=15][waterway=stream] { line-width: 4; }
.water.line[zoom=15][waterway=river] { line-width: 9; }

.water.line[zoom=16][waterway=stream] { line-width: 8; }
.water.line[zoom=16][waterway=river] { line-width: 11; }

.water.line[zoom>=17] { line-width: 15; }

.coast.fill
{
    polygon-fill: #dceee9;
    /*
    line-width: 1;
    line-color: #dceee9;
    */
}

.citylike.area
{
    polygon-fill: #d0d0d0;
}

.parklike.area
{
    polygon-fill: #91b156;
}

.parklike.area[zoom>=16]
{
    polygon-pattern-file: url('img/trees-z.png');
}

.parklike.area[landuse=cemetery]
{
    polygon-fill: #94b580;
}

.parklike.area[zoom>=16][landuse=cemetery]
{
    polygon-pattern-file: url('img/graveyard-z.png');
}

.parklike.area[zoom>=11]
{
    line-width: 1;
    line-color: #6dbe3c;
}

.building.area[zoom>=13]
{
    polygon-fill: #aaaaaa;
}

.building.area[zoom>=15]
{
    line-width: 1;
    line-color: #808080;
}

.water.label name,
.parklike.label name,
.citylike.label[amenity!=parking] name,
.building.label name
{
    text-face-name: "DejaVu Sans Book";
    text-fill: #000;
    text-placement: point;
    text-halo-radius: 2;
}

.water.label[zoom>=13][zoom<=15][size=large] name,
.parklike.label[zoom>=13][zoom<=15][size=large] name,
.citylike.label[zoom>=13][zoom<=15][size=large][amenity!=parking] name,
.building.label[zoom>=13][zoom<=15][size=large] name,
.water.label[zoom>=15][zoom<=16][size=medium] name,
.parklike.label[zoom>=15][zoom<=16][size=medium] name,
.citylike.label[zoom>=15][zoom<=16][size=medium][amenity!=parking] name,
.building.label[zoom>=15][zoom<=16][size=medium] name,
.water.label[zoom=16][size=small] name,
.parklike.label[zoom=16][size=small] name,
.citylike.label[zoom=16][size=small][amenity!=parking] name,
.building.label[zoom=16][size=small] name
{
    text-size: 9;
    text-wrap-width: 50;
}

.citylike.label[zoom>=17][amenity=school]
{
    point-file: url('img/icons/24x24/symbol/landmark/amenity=school.png');
    text-dy: 20;
}

.citylike.label[zoom>=15][zoom<=16][amenity=school]
{
    point-file: url('img/icons/16x16/symbol/landmark/amenity=school.png');
    text-dy: 18;
}

.citylike.label[zoom=14][amenity=school]
{
    point-file: url('img/icons/12x12/symbol/landmark/amenity=school.png');
}

.citylike.label[zoom>=17][amenity=parking]
{
    point-file: url('img/icons/16x16/panel/transport/amenity=parking.png');
}

.water.label[zoom>=16][size=large] name,
.parklike.label[zoom>=16][size=large] name,
.citylike.label[zoom>=16][size=large][amenity!=parking] name,
.building.label[zoom>=16][size=large] name,
.water.label[zoom>=17] name,
.parklike.label[zoom>=17] name,
.citylike.label[zoom>=17][amenity!=parking] name,
.building.label[zoom>=17] name
{
    text-wrap-width: 100;
    text-size: 12;
}

.water.label name
{
    text-halo-fill: #affcff;
}

.parklike.label name
{
    text-halo-fill: #d1ffb6;
}

.citylike.label[amenity!=parking] name
{
    text-halo-fill: #eeeeee;
}

.building.label name
{
    text-halo-fill: #dddddd;
}
