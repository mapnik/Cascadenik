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

.path.outline[highway!=steps][zoom>=16] { line-width: 4; }
.path.inline[highway!=steps][zoom>=16]
{
    line-width: 2;
    line-dasharray: 3, 3;
}

.path.outline[highway=steps][zoom>=16] { line-width: 7; }
.path.inline[highway=steps][zoom>=16]
{
    line-width: 5;
    line-dasharray: 2, 3;
}

.path.outline[highway!=steps][zoom>=14][zoom<=15] { line-width: 3; }
.path.inline[highway!=steps][zoom>=14][zoom<=15]
{
    line-width: 2;
    line-dasharray: 2, 2;
}

.path.outline[highway=steps][zoom>=14][zoom<=15] { line-width: 5; }
.path.inline[highway=steps][zoom>=14][zoom<=15]
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
