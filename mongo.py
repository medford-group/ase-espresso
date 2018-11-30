# A Mongo database for ASE calculations

"""This module will be like the ase-db but different in the following ways:

1. Booleans are stored as booleans.
2. There is no numeric id.
3. Tags are stored in an array.
"""

import os
import numpy as np
from collections import OrderedDict
import datetime
import json
import hashlib

from pymongo import MongoClient
from ase import Atoms, Atom
from ase.io.jsonio import encode
from espresso import espresso
import spglib
from ase.constraints import dict2constraint

def mongo_atoms_doc(atoms):
    """Return a dictionary of an Atoms object."""
    d = OrderedDict(atoms=[{'symbol': atom.symbol,
                            'position': json.loads(encode(atom.position)),
                            'tag': atom.tag,
                            'index': atom.index,
                            'charge': atom.charge,
                            'momentum': json.loads(encode(atom.momentum)),
                            'magmom': atom.magmom}
                           for atom in atoms],
                    cell=atoms.cell,
                    pbc=atoms.pbc,
                    info=atoms.info,
                    constraints=[c.todict() for c in atoms.constraints])

    # redundant information for search convenience.
    d['natoms'] = len(atoms)
    cell = atoms.get_cell()
    if cell is not None and np.linalg.det(cell) > 0:
        d['volume'] = atoms.get_volume()

    d['mass'] = sum(atoms.get_masses())

    syms = atoms.get_chemical_symbols()
    d['chemical_symbols'] = list(set(syms))
    d['symbol_counts'] = {sym: syms.count(sym) for sym in syms}
    d['spacegroup'] = spglib.get_spacegroup(atoms)

    return json.loads(encode(d))

def mongo_doc_atoms(doc):
    atoms = Atoms([Atom(atom['symbol'],
                                atom['position'],
                                tag=atom['tag'],
                                momentum=atom['momentum'],
                                magmom=atom['magmom'],
                                charge=atom['charge'])
                           for atom in doc['atoms']['atoms']],
                          cell=doc['atoms']['cell'],
                          pbc=doc['atoms']['pbc'],
                          info=doc['atoms']['info'],
                          constraint=[dict2constraint(c) for c in doc['atoms']['constraints']])

    from ase.calculators.singlepoint import SinglePointCalculator
    results = doc['results']
    calc = SinglePointCalculator(energy=results.get('energy', None),
                                 forces=results.get('forces', None),
                                 stress=results.get('stress', None),
                                 atoms=atoms)
    atoms.set_calculator(calc)
    return atoms

def mongo_doc(atoms, **kwargs):
        """atoms is an ase.atoms.Atoms object.
        kwargs are key-value pairs that will be written to the database.

        Returns a dictionary for inserting to Mongo. The dictionary
        has three subdocuments:

        atoms
        calculator - generated by the calculator.todict function
        results - energy, forces, and stress

        There are couple of additional fields including the user,
        creation and modified time, and an inserted-hash.

        """

        d = OrderedDict(atoms=mongo_atoms_doc(atoms))

        # Calculator document
        calc = atoms.get_calculator()
        if calc is not None:

            if hasattr(calc, 'todict'):
                d['calculator'] = calc.todict()
            else:
                d['calculator'] = {}

            # This might make it easier to reload these later.  I
            # believe you import the class from the module then create
            # an instance of the class.
            d['calculator']['module'] = calc.__module__
            d['calculator']['class'] = calc.__class__.__name__

        # Results. This may duplicate information in the calculator,
        # but we have no control on what the calculator does.
        d['results'] = OrderedDict()
        if atoms.get_calculator() is not None:
            calc = atoms.get_calculator()

            if not calc.calculation_required(atoms, ['energy']):
                d['results']['energy'] = atoms.get_potential_energy()
                if calc.beefensemble == True and calc.printensemble == True:
                    d['results']['beefensemble'] = \
                    calc.get_beef_ensemble()
            if not calc.calculation_required(atoms, ['forces']):
                f = atoms.get_forces()
                d['results']['forces'] = f.tolist()
                d['results']['fmax'] = max(np.abs(f.flatten()))

            if not calc.calculation_required(atoms, ['stress']):
                s = atoms.get_stress()
                d['results']['stress'] = s.tolist()
                d['results']['smax'] = max(np.abs(s.flatten()))

        d['user'] = os.getenv('USER')
        # This is a hash of what is inserted. You might use it to
        # check for uniqueness of the insert. It is not clear it
        # belongs here since d contains results and time data.
        d['inserted-hash'] = hashlib.sha1(encode(d)).hexdigest()

        # Created time.
        d['ctime'] = datetime.datetime.utcnow()
        # Modified time - depends on user to update
        d['mtime'] = datetime.datetime.utcnow()

        d.update(kwargs)

        return d


class MongoDatabase(MongoClient):

    def __init__(self,
                 host='localhost',
                 port=27017,
                 database='atoms',
                 collection='atoms',
                 user=None,
                 password=None):
        """
        user and password are currently unused.
        """
        MongoClient.__init__(self, host, port)

        self.db = self[database]
        if user is not None and password is not None:
            self.db.authenticate(user, password)

        #self.collection = getattr(self.db, collection)
        self.collection = self.db[collection]

    def write(self, d, **kwargs):
        """d should be a dictionary, e.g. from mongo_doc.
        This is a very thin wrapper on insert_one.

        """
        d.update(kwargs)
        return self.collection.insert(d)

    def find(self, *args, **kwargs):
        """Thin wrapper for collection.find().

        """
        return self.collection.find(*args, **kwargs)

    def get_atoms(self, *args, **kwargs):
        """Return an atoms object for each match in filter.  Each atoms object
        has a SinglePointCalculator attached to it with the results
        that were stored.

        args and kwargs are passed to the collection.find function.

        """

        cursor = self.collection.find(*args, **kwargs)
        for doc in cursor:
            yield mongo_doc_atoms(doc)
