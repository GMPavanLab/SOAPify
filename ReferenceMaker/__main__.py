from .referenceSaponificator import referenceSaponificator
from lammps import lammps
import numpy
from .ico5083 import ico5083
from .dhfat3049 import dhfat3049
from .th4116 import th4116
from .distanceVisualizer import distanceVisualizer

choice = [
    {
        "kind": "Au",
        "diameter": 2.88,
        "atomMass": 196.96655,
        "pair_coeff": "2.88 10.35	4.178	0.210	1.818	4.07293506	4.9883063257983666",
    },
    {
        "kind": "Cu",
        "diameter": 2.56,
        "atomMass": 64,
        "pair_coeff": "2.56 10.55	2.43	0.0894	1.2799	3.62038672	4.4340500673763259",
    },
]
print(
    "This procedure will create our standard reference dataset that contains the SOAP fingerprints\n"
    "for the following structures:\n"
    "\t* bulk sc\n"
    "\t* bulk bcc\n"
    "\t* bulk hcp\n"
    "\t* bulk fcc\n"
)
print("Please choose your metal type:")
n = 0
for metal in choice:
    print(f"{n} : {metal['kind']}, coeffs: {metal['pair_coeff']}")
    n += 1

idChosen = int(input("MetalID: "))
chosen = choice[idChosen]


kind = chosen["kind"]
pair_coeff = f"pair_coeff	1 1 {chosen['pair_coeff']}"
atomMass = chosen["atomMass"]
diameter = chosen["diameter"]
referencesFile = f"{kind}References.hdf5"
latticebcc = 2 * diameter / numpy.sqrt(3.0)
latticefcc = diameter * numpy.sqrt(2.0)

for d in [
    {"name": "bcc", "latticeCMD": f"lattice bcc {latticebcc}"},
    {"name": "fcc", "latticeCMD": f"lattice fcc {latticefcc}"},
    {"name": "hcp", "latticeCMD": f"lattice hcp {diameter}"},
    {"name": "sc", "latticeCMD": f"lattice sc {diameter}"},
    # "npMinimizer.in",
]:
    input = d["name"]
    with lammps() as lmp:

        lmp.commands_list(
            [
                "units           metal",
                "atom_style      atomic",
                "boundary	p p p",
                d["latticeCMD"],
                "region myreg block 0 8 0 8 0 8",
                "create_box      1 myreg",
                "create_atoms    1 box",
                f"mass 1 {atomMass}",
                "pair_style	smatb/single",
                pair_coeff,
                "neighbor	8.0 bin",
                "neigh_modify	every 1 delay 0 check yes",
                "fix            boxmin all box/relax iso 1.0",
                "minimize       1.0e-8 1.0e-10 10000 100000",
                "unfix boxmin",
                "minimize       1.0e-8 1.0e-10 10000 100000",
                f"write_data     {input}.data",
            ]
        )
        # print(lmp.extract_box())
        # print(0,lmp.extract_atom("id")[0],[lmp.extract_atom("x")[0][i] for i in [0, 1, 2]],)
        ## TODO extract box and atoms data and pass them to ase, so writing data files is not necessary
for np in [
    {"name": "dhfat3049", "data": dhfat3049},
    {"name": "ico5083", "data": ico5083},
    {"name": "th4116", "data": th4116},
]:
    with lammps() as lmp:
        np["data"] *= diameter / 2.0
        commands_list = [
            "units           metal",
            "atom_style      atomic",
            "boundary	p p p",
            "region myreg block -40 40 -40 40 -40 40",
            "create_box      1 myreg",
            f"mass 1 {atomMass}",
        ]
        commands_list += [
            f"create_atoms 1 single {row[0]} {row[1]} {row[2]}" for row in np["data"]
        ]
        commands_list += [
            "pair_style	smatb/single",
            pair_coeff,
            "neighbor	8.0 bin",
            "neigh_modify	every 1 delay 0 check yes",
            "minimize       1.0e-8 1.0e-10 10000 100000",
            f"write_data {np['name']}.data",
        ]
        lmp.commands_list(commands_list)

referenceSaponificator(rcuts=[2.9, 3.0, 5.8, 6.0], referencesFile=referencesFile)
distanceVisualizer(rcuts=[2.9, 3.0, 5.8, 6.0], referencesFile=referencesFile, kind=kind)