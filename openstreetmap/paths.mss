.path[highway!=steps]
{
    line-cap: butt;
    line-join: round;
}

.path[highway=steps]
{
    line-cap: butt;
    line-join: miter;
}

.path.outline[zoom>=16][highway!=steps] { line-width: 4; }
.path.inline[zoom>=16][highway!=steps]
{
    line-width: 2;
    line-dasharray: 3, 3;
}

.path.outline[zoom>=16][highway=steps] { line-width: 7; }
.path.inline[zoom>=16][highway=steps]
{
    line-width: 5;
    line-dasharray: 2, 3;
}

.path.outline[zoom>=14][zoom<=15][highway!=steps] { line-width: 3; }
.path.inline[zoom>=14][zoom<=15][highway!=steps]
{
    line-width: 2;
    line-dasharray: 2, 2;
}

.path.outline[zoom>=14][zoom<=15][highway=steps] { line-width: 5; }
.path.inline[zoom>=14][zoom<=15][highway=steps]
{
    line-width: 3;
    line-dasharray: 1, 2;
}

/** Path Colors **/

.path.inline
{
    line-color: #000;
    line-opacity: 0.5;
}

.path.outline
{
    line-color: #fff;
    line-opacity: 0.2;
}
