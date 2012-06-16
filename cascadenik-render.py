import cascadenik
from cascadenik import mapnik

import Image

def main(src_file):
    mmap = mapnik.Map(640, 480)
    
    cascadenik.load_map(mmap, src_file, '.', verbose=True)
    
    print mmap
    
    mmap.zoom_to_box(mapnik.Box2d(-20000000, -15000000, 20000000, 15000000))

    img = mapnik.Image(640, 480)
    mapnik.render(mmap, img)
    
    print img
    
    img = Image.fromstring('RGBA', (640, 480), img.tostring())
    
    img.show()

if __name__ == '__main__':
    
    main('doc/example4.mml')
