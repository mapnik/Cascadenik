Map
{
    map-bgcolor: #81cee7;
}

.coast.edge.outer
{
    line-width: 13;
    line-color: #89dbf6;
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
    polygon-fill: #81cee7;
    line-join: round;
}

.coast.fill
{
    polygon-fill: #dceee9;
    /*
    line-width: 1;
    line-color: #dceee9;
    */
}

.citylike.area,
.parking.area
{
    polygon-fill: #d0d0d0;
}

.parklike.area
{
    polygon-fill: #91da65;
}

.parklike.area[zoom>=16]
{
    polygon-pattern-file: url('img/trees-z.png');
}

.parklike.area[landuse=cemetery]
{
    polygon-fill: #94b580;
}

.parklike.area[landuse=cemetery][zoom>=16]
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
.citylike.label name,
.building.label name
{
    text-face-name: "DejaVu Sans Book";
    text-fill: #000;
    text-placement: point;
    text-halo-radius: 2;
}

.water.label[zoom>=13][zoom<=15][size=large] name,
.parklike.label[zoom>=13][zoom<=15][size=large] name,
.citylike.label[zoom>=13][zoom<=15][size=large] name,
.building.label[zoom>=13][zoom<=15][size=large] name,
.water.label[zoom=15][size=medium] name,
.parklike.label[zoom=15][size=medium] name,
.citylike.label[zoom=15][size=medium] name,
.building.label[zoom=15][size=medium] name
{
    text-size: 9;
    text-wrap-width: 50;
}

.water.label[zoom>=16] name,
.parklike.label[zoom>=16] name,
.citylike.label[zoom>=16] name,
.building.label[zoom>=16] name
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

.citylike.label name
{
    text-halo-fill: #eeeeee;
}

.building.label name
{
    text-halo-fill: #dddddd;
}
