import base64, os

"""
simulate an unlimited-length kv store using normal directories
"""

def key(base):
    """ get a list of all *leaf* directories as strings """
    for root, dirs, files in os.walk(base, topdown=False):
        for file in files:
            yield os.path.join(root, file)
            # if root != base and root != dir:
            #     yield os.path.join(root, dir)

def chunk(url):
    """ create filesystem-safe places for url-keyed data to be stored """
    chunks = lambda l, n: [l[x: x+n] for x in xrange(0, len(l), n)]
    url_64 = base64.urlsafe_b64encode(url)
    return chunks(url_64, 255)

def dir(url):
    """ use safe64 to create a proper directory """
    return "/".join(chunk(url))

def decode(url):
    """ use safe64 to create a proper directory """
    return base64.urlsafe_b64decode(url.replace('/', ''))
