from cascadenik.parse import stylesheet_declarations

s = '''
@orange: #f90;
@blue : #00c;

.orange { polygon-fill: @orange }
.blue { polygon-fill: @blue }
'''

for dec in stylesheet_declarations(s): print dec
