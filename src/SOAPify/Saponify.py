import h5py
import numpy as np
from ase import Atoms as aseAtoms
from dscribe.descriptors import SOAP
from HDF5er import HDF52AseAtomsChunckedwithSymbols as HDF2ase
import time

__all__ = ["saponify"]


def saponify(
    trajFname: str,
    trajectoryGroupPath: str,
    outputFname: str,
    exportDatasetName: str,
    SOAPOutputChunkDim: int = 100,
    SOAPnJobs: int = 1,
    SOAPatomMask: str = None,
    SOAPrcut: float = 8.0,
    SOAPnmax: int = 8,
    SOAPlmax: int = 8,
    SOAP_respectPBC: bool = True,
):
    """Calculates the SOAP fingerprints for each atom in a given hdf5 trajectory

    This routine sets up a SOAP engine to calculate the SOAP fingerprints for all
    the atoms in a given trajectory. The user can choose the otpio

    Args:
        trajFname (str): The name of the hdf5 file in wich the trajectory is stored
        trajectoryGroupPath (str): the path of the group that contains the trajectory in trajFname
        outputFname (str): the name of the hdf5 file that will contain the ouput or the SOAP analysis
        exportDatasetName (str): the name of the dataset that will contain the SOAP
        results, it will be saved in the group called "SOAP"
        SOAPOutputChunkDim (int, optional): The dimension of the chunck of data
        in the SOAP results dataset. Defaults to 100.
        SOAPnJobs (int, optional): the number of concurrent SOAP calculations
        (option passed to dscribe's SOAP). Defaults to 1.
        SOAPatomMask (str, optional): the symbols of the atoms whose SOAP
        fingerprint will be calculated (option passed to dscribe's SOAP). Defaults to None.
        SOAPrcut (float, optional): The cutoff for local region in angstroms.
        Should be bigger than 1 angstrom (option passed to dscribe's SOAP). Defaults to 8.0.
        SOAPnmax (int, optional): The number of radial basis functions (option
        passed to dscribe's SOAP). Defaults to 8.
        SOAPlmax (int, optional): The maximum degree of spherical harmonics
        (option passed to dscribe's SOAP). Defaults to 8.
        SOAP_respectPBC (bool, optional): Determines whether the system is
        considered to be periodic (option passed to dscribe's SOAP). Defaults to True.
    """

    with h5py.File(trajFname, "r") as trajLoader, h5py.File(
        outputFname, "a"
    ) as soapOffloader:
        traj = trajLoader[f"Trajectories/{trajectoryGroupPath}"]

        symbols = traj["Types"].asstr()[:]
        # we are getting only the SOAP results of the oxigens from each water molecule in
        # this simulation
        centersMask = None
        if SOAPatomMask is not None:
            centersMask = [i for i in range(len(symbols)) if symbols[i] in SOAPatomMask]

        species = list(set(symbols))
        soapEngine = SOAP(
            species=species,
            periodic=SOAP_respectPBC,
            rcut=SOAPrcut,
            nmax=SOAPnmax,
            lmax=SOAPlmax,
            average="off",
        )

        NofFeatures = soapEngine.get_number_of_features()

        soapDir = soapOffloader.require_group("SOAP")
        nCenters = len(symbols) if centersMask is None else len(centersMask)
        if exportDatasetName not in soapDir.keys():
            soapDir.create_dataset(
                exportDatasetName,
                (0, nCenters, NofFeatures),
                compression="gzip",
                compression_opts=9,
                chunks=(100, nCenters, NofFeatures),
                maxshape=(None, nCenters, NofFeatures),
            )
        SOAPout = soapDir[exportDatasetName]
        SOAPout.resize((len(traj["Trajectory"]), nCenters, NofFeatures))

        for chunkTraj in traj["Trajectory"].iter_chunks():
            chunkBox = (chunkTraj[0], slice(0, 6, 1))
            print(f'working on trajectory chunk "{chunkTraj}"')
            print(f'   and working on box chunk "{repr(chunkBox)}"')
            # load in memory a chunk of data
            atoms = HDF2ase(traj, chunkTraj, chunkBox, symbols)

            jobchunk = min(SOAPOutputChunkDim, len(atoms))
            jobStart = 0
            jobEnd = jobStart + jobchunk
            while jobStart < len(atoms):
                t1 = time.time()
                frameStart = jobStart + chunkTraj[0].start
                FrameEnd = jobEnd + chunkTraj[0].start
                print(f"working on frames: [{frameStart}:{FrameEnd}]")
                SOAPout[frameStart:FrameEnd] = soapEngine.create(
                    atoms[jobStart:jobEnd],
                    positions=[centersMask] * jobchunk,
                    n_jobs=SOAPnJobs,
                )
                t2 = time.time()
                jobchunk = min(SOAPOutputChunkDim, len(atoms) - jobEnd)
                jobStart = jobEnd
                jobEnd = jobStart + jobchunk
                print(f"delta create= {t2-t1}")


if __name__ == "__main__":
    # this is an example script for Applying the SOAP analysis on a trajectory saved on an
    # HDF5 file formatted with our HDF5er and save the result in another HDF5 file
    saponify(
        "Water.hdf5",
        "1ns",
        "WaterSOAP.hdf5",
        "1nSOAP",
        SOAPatomMask="O",
        SOAPOutputChunkDim=100,
        SOAPnJobs=12,
    )