# cluster-dependent definitions
# espresso.py will make use of all "self" variables in config class
# although not necessary for the installation at the suncat cluster,
# we use a named pipe instead of stdio for sending coordinates back to pw.x
# as an example how to set this up
import os

class config:
    def __init__(self):
        user = os.getenv('USER')
        self.scratch = '/nv/hp22/'+user+'/scratch'
        self.mpiexec = 'mpirun'
        #self.scratch = '/nv/hp22/amedford6/medford-shared/.scratch'
        if not os.path.exists(self.scratch):
            self.scratch = '/tmp'
        self.submitdir = os.getenv('PBS_O_WORKDIR')
        self.batch = self.submitdir!=None
        #check for batch
        if self.batch:
            nodefile = os.getenv('PBS_NODEFILE')
            f = open(nodefile, 'r')
            procs = [x.strip() for x in f.readlines()]
            f.close()
            self.procs = procs
            self.jobid = os.getenv('PBS_JOBID')

            nprocs = len(procs)
            self.nprocs = nprocs
            
            uniqnodefile = self.scratch+'/uniqnodefile'
            os.system('uniq $PBS_NODEFILE >'+uniqnodefile)
            p = os.popen('wc -l <'+uniqnodefile, 'r')
            nnodes = p.readline().strip()
            p.close()
        
            self.perHostMpiExec = self.mpiexec+' -machinefile '+uniqnodefile+' -np '+nnodes
            self.perProcMpiExec = self.mpiexec+' -machinefile '+nodefile+' -np '+str(nprocs)+' -wdir %s %s'
            self.perSpecProcMpiExec = self.mpiexec+' -machinefile %s -np %d -wdir %s %s'

            #put mpi and pw.x in path if not already there
            p = os.environ['PATH']
            os.environ['PATH']='/nv/hp22/amedford6/medford-shared/builds/espresso/5.1.r11289-pybeef/intel-16.0+mvapich2-2.2+mkl-11.3/espresso-5.1.r11289-pybeef/bin:'+p

            #boot mpd if not already done
            ## Not necessary? AJM
            #if not os.environ.has_key('QEASE_MPD_BOOTED'):
            #    os.system('mpdboot -f '+uniqnodefile+' -r ssh -n '+nnodes)
            #    os.system('mpdtrace -l -v')
            #    os.environ['QEASE_MPD_BOOTED'] = 'yes'

            #self.mpdshutdown = 'mpdallexit'


    def do_perProcMpiExec(self, workdir, program):
        return os.popen2(self.perProcMpiExec % (workdir, program))

    def do_perProcMpiExec_outputonly(self, workdir, program):
        return os.popen(self.perProcMpiExec % (workdir, program), 'r')

    def runonly_perProcMpiExec(self, workdir, program):
        os.system(self.perProcMpiExec % (workdir, program))

    def do_perSpecProcMpiExec(self, machinefile, nproc, workdir, program):
        return os.popen3(self.perSpecProcMpiExec % (machinefile, nproc, workdir, program))
"""
            #how to create fifo
            self.fifogen = 'cd %s; [ -e ase3inpfifo ] || mkfifo ase3inpfifo'
            self.fifo = True

    def do_perProcMpiExec(self, workdir, program):
        os.system(self.fifogen%workdir)
        o = os.popen(self.perProcMpiExec % (workdir, program), 'r')
        return open(workdir+'/ase3inpfifo', 'w+'), o 

    def do_perProcMpiExec_outputonly(self, workdir, program):
        return os.popen(self.perProcMpiExec % (workdir, program), 'r')

    def runonly_perProcMpiExec(self, workdir, program):
        os.system(self.perProcMpiExec % (workdir, program))

    def do_perSpecProcMpiExec(self, machinefile, nproc, workdir, program):
        os.system(self.fifogen%workdir)
        i,o,e = os.popen3(self.perSpecProcMpiExec % (machinefile, nproc, workdir, program))
        return open(workdir+'/ase3inpfifo', 'w+'), o, e
"""
