from cascadenik.parse import stylesheet_declarations

s = """
    #roads,
    #stuff
    {
        line-color: #f90;
        line-width: 1;
        
        &.more,
        &.again
        { line-width: 2; }
        
        /*
        name1,
        name2
        { line-width: 2; }
        */
    }
"""

for declaration in stylesheet_declarations(s):
    print declaration