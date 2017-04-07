import sys
import os

if len(sys.argv) < 2:
    print('Pass the name of the environment as the argument')
env = sys.argv[1]

prefix = '/nv/hp22/amedford6/medford-shared/builds/anaconda/4.2.0/none/anaconda2/envs/'+env
assert os.path.exists(prefix)

print('Installing espresso interface in: '+prefix)

os.system('python setup.py install --prefix='+prefix)
