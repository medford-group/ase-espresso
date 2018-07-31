#****************************************************************************
# Copyright (C) 2013 SUNCAT
# This file is distributed under the terms of the
# GNU General Public License. See the file `COPYING'
# in the root directory of the present distribution,
# or http://www.gnu.org/copyleft/gpl.txt .
#****************************************************************************


from ase.calculators.general import Calculator
from espresso import espresso
import numpy as np

class vibespresso(Calculator):
    """
    Special espresso calculator, which expects the first calculation to
    be performed for a structure without displacements. All subsequent
    calculations are then initialized with the Kohn-Sham potential of
    the first calculation to speed up vibrational calculations.
    """
    def __init__(self,
        outdirprefix = 'out',
        **kwargs
        ):
        """
        In addition to the parameters of a standard espresso calculator,
        outdirprefix (default: 'out') can be specified, which will be the
        prefix of the output of the calculations for different displacements
        """
        
        self.arg = kwargs.copy()
        self.outdirprefix = outdirprefix
        self.counter = 0
        self.equilibriumdensity = outdirprefix+'_equi.tgz'
        self.firststep = True
        self.ready = False
    
    def update(self, atoms):
        if self.atoms is not None:
            x = atoms.positions-self.atoms.positions
            if np.max(x)>1E-13 or np.min(x)<-1E-13:
                self.ready = False
        else:
            self.atoms = atoms.copy()
        self.runcalc(atoms)
        if atoms is not None:
            self.atoms = atoms.copy()
    
    def runcalc(self, atoms):
        if not self.ready:
            self.arg['outdir'] = self.outdirprefix+'_%04d' % self.counter
            self.counter += 1
            if self.firststep:
                self.esp = espresso(**self.arg)
                self.esp.set_atoms(atoms)
                self.esp.get_potential_energy(atoms)
                self.esp.save_chg(self.equilibriumdensity)
                self.firststep = False
            else:
                self.arg['startingpot'] = 'file'
                self.esp = espresso(**self.arg)
                self.esp.set_atoms(atoms)
                self.esp.load_chg(self.equilibriumdensity)
                self.esp.get_potential_energy(atoms)
                self.esp.stop()
            self.ready = True

    def get_potential_energy(self, atoms, force_consistent=False):
        self.update(atoms)
        if force_consistent:
            return self.esp.energy_free
        else:
            return self.esp.energy_zero

    def get_forces(self, atoms):
        self.update(atoms)
        return self.esp.forces
    
    def get_dipole_moment(self,charge_type='DDEC6'):
        """ function to calculate the total dipole of a system in chargemol"""
        dipole = self.esp.get_dipole_moment()
        return dipole 
    def get_name(self):
        return 'VibEspresso'

    def get_version(self):
        return '0.1'

