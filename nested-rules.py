from cascadenik.parse import stylesheet_declarations

s = """
    #roads,
    #stuff
    {
        line-color: #f90;
        line-width: 1;
        
        &.more,
        &[this=that]
        { line-width: 2; }
        
        &.one, &.two
        {
            &[three=3], &[four=4]
            { polygon-fill: #000; }
        }
        
        /*
        .purple
        { line-color: #909; }
        
        #green
        { line-color: #090; }
        
        [color=blue]
        { line-color: #00f; }
        */
        
        yellow
        { line-color: #ff0; }
    }
"""

for declaration in stylesheet_declarations(s):
    print declaration