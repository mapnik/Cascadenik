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
        
        &[this=that]
        { line-color: #909; }
        
        name1
        { line-color: #ff6; }
    }
"""

for declaration in stylesheet_declarations(s):
    print declaration