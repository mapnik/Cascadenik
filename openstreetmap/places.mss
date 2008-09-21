.place name
{
    text-face-name: "DejaVu Sans Book";
    text-fill: #000;
    text-placement: point;
    text-wrap-width: 65;
}

.place[place=town][zoom>=9] name,
.place[place=city] name
{
    text-face-name: "DejaVu Sans Bold";
    text-halo-radius: 2 !important;
    text-fill: #222;
}

.place[zoom<=11] { text-halo-radius: 1; }
.place[zoom>=12] { text-halo-radius: 2; }

.place[zoom<=12] { text-halo-fill: #eee; }
.place[zoom>=13] { text-halo-fill: #fff; }

.place[zoom>=14][zoom<=15] name { text-size: 10; }
.place[zoom=16] name { text-size: 12; }

.place[place=village][zoom>=12][zoom<=13] name { text-size: 10; }
.place[place=village][zoom>=14][zoom<=16] name { text-size: 12; }

.place[place=town][zoom>=9][zoom<=12] name { text-size: 10; }
.place[place=town][zoom>=13][zoom<=14] name { text-size: 12; }

.place[place=city][zoom>=7][zoom<=8] name { text-size: 10; }
.place[place=city][zoom>=9][zoom<=13] name { text-size: 12; }
.place[place=city][zoom=14] name { text-size: 14; }
