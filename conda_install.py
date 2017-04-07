import sys
import os

env = sys.argv[1]

prefix = '/nv/hp22/amedford6/medford-shared/builds/anaconda/4.2.0/none/anaconda2/envs/'+env
assert os.path.exists(prefix)

path = prefix+'/lib/python2.7/site-packages'
if not os.path.exists(path):
    os.system('mkdir -p '+path)

print('Installing espresso interface in: '+path)

os.system('python setup.py install --prefix='+path)
