from ase.io import iread as aseIRead
from ase.io import read as aseRead
import numpy as np
import h5py

# this is "legacy code", use with caution

__all__ = ["xyz2hdf5Converter"]

# TODO: convert use exportChunk2HDF5
def xyz2hdf5Converter(xyzName: str, boxfilename: str, group: h5py.Group):
    """Generate an HDF5 trajectory from an xyz file and a box file

        This function reads an xyz file with ase and then export it to an trajectory in and hdf5 file,
        the user should pass the group within the hdf5file to this function

    Args:
        xyzName (str): the filename of the xyz trajaectory
        boxfilename (str): the filename of the  per frame box dimensions
        group (h5py.Group): the group within the hdf5 file where the trajectroy will be saved
    """
    frame = aseRead(xyzName)
    nat = len(frame.get_positions())
    if "Types" not in list(group.keys()):
        group.create_dataset(
            "Types", (nat), compression="gzip", data=frame.get_chemical_symbols()
        )
    if "Trajectory" not in list(group.keys()):
        group.create_dataset(
            "Trajectory",
            (0, nat, 3),
            compression="gzip",
            chunks=(10, nat, 3),
            maxshape=(None, nat, 3),
        )
    if "Box" not in list(group.keys()):
        group.create_dataset(
            "Box", (0, 6), compression="gzip", chunks=True, maxshape=(None, 6)
        )
    xyz = aseIRead(xyzName)
    with open(boxfilename, "r") as bf:
        frameNum = 0
        first = 0
        boxes = []
        atomicframes = []
        for box, frame in zip(bf, xyz):
            t = box.split()
            boxInfo = np.array(
                [float(t[0]), float(t[1]), float(t[2]), 90.0, 90.0, 90.0]
            )
            boxes.append(boxInfo)
            atomicframes.append(frame.get_positions())
            frameNum += 1
            if frameNum % 20 == 0:
                group["Box"].resize((frameNum, 6))
                group["Trajectory"].resize((frameNum, nat, 3))
                print(
                    f"[{first}-{frameNum}]",
                    len(boxes),
                    len(group["Box"][first:frameNum]),
                )

                group["Box"][first:frameNum] = boxes
                group["Trajectory"][first:frameNum] = atomicframes

                first = frameNum
                boxes = []
                atomicframes = []

        if frameNum != first:
            group["Box"].resize((frameNum, 6))
            group["Trajectory"].resize((frameNum, nat, 3))
            print(
                f"[{first}-{frameNum}]",
                len(boxes),
                len(group["Box"][first:frameNum]),
            )
            group["Box"][first:frameNum] = boxes
            group["Trajectory"][first:frameNum] = atomicframes
