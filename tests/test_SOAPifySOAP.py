import pytest
import SOAPify
import numpy
from numpy.testing import assert_array_equal
import h5py
import SOAPify.HDF5er as HDF5er
from .testSupport import getUniverseWithWaterMolecules


@pytest.fixture(
    scope="module",
    params=[
        None,
        ["O"],
    ],
)
def fixture_AtomMask(request):
    return request.param


def test_FeedingSaponifyANonTrajGroups(tmp_path):
    fname = tmp_path / "wrongFIle.hdf5"
    with h5py.File(fname, "w") as f:
        f.create_group("Trajectories/notTraj")
    with pytest.raises(ValueError):
        n_max = 4
        l_max = 4
        rcut = 10.0
        with h5py.File(fname, "a") as f:
            soapGroup = f.require_group("SOAP")
            trajGroup = f["Trajectories/notTraj"]
            SOAPify.saponifyTrajectory(
                trajGroup,
                soapGroup,
                rcut,
                n_max,
                l_max,
            )


def test_MultiAtomicSoapify(fixture_AtomMask, engineKind_fixture, tmp_path):
    nMol = 27
    u = getUniverseWithWaterMolecules(nMol)
    fname = f"testH2O_{engineKind_fixture}_{''.join([i for i in fixture_AtomMask]) if fixture_AtomMask else ''}.hdf5"
    fname = tmp_path / fname
    HDF5er.MDA2HDF5(u, fname, "testH2O", override=True)
    n_max = 4
    l_max = 4
    rcut = 10.0
    with h5py.File(fname, "a") as f:
        soapGroup = f.require_group("SOAP")
        trajGroup = f["Trajectories/testH2O"]
        SOAPify.saponifyTrajectory(
            trajGroup,
            soapGroup,
            rcut,
            n_max,
            l_max,
            useSoapFrom=engineKind_fixture,
            SOAPatomMask=fixture_AtomMask,
        )
        assert soapGroup["testH2O"].attrs["SOAPengine"] == engineKind_fixture
        assert soapGroup["testH2O"].attrs["n_max"] == n_max
        assert soapGroup["testH2O"].attrs["l_max"] == l_max
        assert "O" in soapGroup["testH2O"].attrs["species"]
        assert "H" in soapGroup["testH2O"].attrs["species"]
        assert numpy.abs(soapGroup["testH2O"].attrs["r_cut"] - rcut) < 1e-8
        if fixture_AtomMask == None:
            assert "centersIndexes" not in soapGroup["testH2O"].attrs
        else:
            assert_array_equal(
                soapGroup["testH2O"].attrs["centersIndexes"],
                [i * 3 for i in range(nMol)],
            )
        assert (
            soapGroup[f"testH2O"].shape[-1]
            == (1 + l_max) * n_max * n_max
            + 2 * (1 + l_max) * ((n_max + 1) * n_max) // 2
        )


def test_MultiAtomicSoapifyGroup(fixture_AtomMask, engineKind_fixture, tmp_path):
    nMol = 27
    u = getUniverseWithWaterMolecules(nMol)
    fname = f"testH2O_{engineKind_fixture}_{''.join([i for i in fixture_AtomMask]) if fixture_AtomMask else ''}.hdf5"
    fname = tmp_path / fname
    HDF5er.MDA2HDF5(u, fname, "testH2O", override=True)
    n_max = 4
    l_max = 4
    rcut = 10.0
    with h5py.File(fname, "a") as f:
        soapGroup = f.require_group("SOAP")
        SOAPify.saponifyMultipleTrajectories(
            f["Trajectories"],
            soapGroup,
            rcut,
            n_max,
            l_max,
            useSoapFrom=engineKind_fixture,
            SOAPatomMask=fixture_AtomMask,
        )
        assert soapGroup["testH2O"].attrs["SOAPengine"] == engineKind_fixture
        assert soapGroup["testH2O"].attrs["n_max"] == n_max
        assert soapGroup["testH2O"].attrs["l_max"] == l_max
        assert "O" in soapGroup["testH2O"].attrs["species"]
        assert "H" in soapGroup["testH2O"].attrs["species"]
        assert numpy.abs(soapGroup["testH2O"].attrs["r_cut"] - rcut) < 1e-8
        assert (
            soapGroup[f"testH2O"].shape[-1]
            == (1 + l_max) * n_max * n_max
            + 2 * (1 + l_max) * ((n_max + 1) * n_max) // 2
        )
        if fixture_AtomMask == None:
            assert "centersIndexes" not in soapGroup["testH2O"].attrs
        else:
            assert_array_equal(
                soapGroup["testH2O"].attrs["centersIndexes"],
                [i * 3 for i in range(nMol)],
            )


def test_slicesNo(tmp_path):
    nMol = 1
    u = getUniverseWithWaterMolecules(nMol)

    fname = tmp_path / "testH2O_slices.hdf5"
    HDF5er.MDA2HDF5(u, fname, "testH2O", override=True)
    n_max = 4
    l_max = 4
    upperDiag = (l_max + 1) * ((n_max) * (n_max + 1)) // 2
    fullmat = n_max * n_max * (l_max + 1)
    rcut = 10.0
    with h5py.File(fname, "a") as f:
        soapGroup = f.require_group("SOAP")
        SOAPify.saponifyMultipleTrajectories(
            f["Trajectories"],
            soapGroup,
            rcut,
            n_max,
            l_max,
            useSoapFrom="dscribe",
        )
        species, slices = SOAPify.getSlicesFromAttrs(f["SOAP/testH2O"].attrs)
        assert "O" in species
        assert "H" in species
        assert slices["H" + "H"] == slice(0, upperDiag)
        assert slices["H" + "O"] == slice(upperDiag, upperDiag + fullmat)
        assert slices["O" + "H"] == slice(upperDiag, upperDiag + fullmat)  # redundant
        assert slices["O" + "O"] == slice(upperDiag + fullmat, 2 * upperDiag + fullmat)
        fullSpectrum = SOAPify.fillSOAPVectorFromdscribe(
            f["SOAP/testH2O"][:], l_max, n_max, species, slices
        )
        assert fullSpectrum.shape[-1] == 3 * fullmat


def test_MultiAtomicSoapkwargs(tmp_path):
    nMol = 27
    u = getUniverseWithWaterMolecules(nMol)
    fname = tmp_path / "testH2O_kwargs.hdf5"
    HDF5er.MDA2HDF5(u, fname, "testH2O", override=True)
    n_max = 4
    l_max = 4
    rcut = 10.0
    upperDiag = (l_max + 1) * ((n_max) * (n_max + 1)) // 2
    fullmat = n_max * n_max * (l_max + 1)
    with h5py.File(fname, "a") as f:
        soapGroup = f.require_group("SOAPNoCrossover")
        SOAPify.saponifyMultipleTrajectories(
            f["Trajectories"],
            soapGroup,
            rcut,
            n_max,
            l_max,
            SOAPkwargs={"crossover": False},
            useSoapFrom="dscribe",
        )
        assert soapGroup["testH2O"].attrs["n_max"] == n_max
        assert soapGroup["testH2O"].attrs["l_max"] == l_max
        assert "O" in soapGroup["testH2O"].attrs["species"]
        assert "H" in soapGroup["testH2O"].attrs["species"]
        assert numpy.abs(soapGroup["testH2O"].attrs["r_cut"] - rcut) < 1e-8
        assert "centersIndexes" not in soapGroup["testH2O"].attrs
        species, slices = SOAPify.getSlicesFromAttrs(soapGroup["testH2O"].attrs)
        print(slices)
        assert "O" in species
        assert "H" in species
        assert slices["H" + "H"] == slice(0, upperDiag)
        assert "HO" not in slices.keys()
        assert "OH" not in slices.keys()
        assert slices["O" + "O"] == slice(upperDiag, 2 * upperDiag)
        assert 22
        for gname, args in [
            ("SOAPinner", {"average": "inner"}),
            ("SOAPouter", {"average": "outer"}),
        ]:
            soapGroup = f.require_group(gname)
            SOAPify.saponifyMultipleTrajectories(
                f["Trajectories"],
                soapGroup,
                rcut,
                n_max,
                l_max,
                SOAPkwargs=args,
                useSoapFrom="dscribe",
            )
            assert soapGroup["testH2O"].attrs["n_max"] == n_max
            assert soapGroup["testH2O"].attrs["l_max"] == l_max
            assert "O" in soapGroup["testH2O"].attrs["species"]
            assert "H" in soapGroup["testH2O"].attrs["species"]
            assert numpy.abs(soapGroup["testH2O"].attrs["r_cut"] - rcut) < 1e-8
            assert "centersIndexes" not in soapGroup["testH2O"].attrs

            assert soapGroup[f"testH2O"].shape[-1] == 2 * upperDiag + fullmat
            species, slices = SOAPify.getSlicesFromAttrs(soapGroup["testH2O"].attrs)
            print(slices)
            assert "O" in species
            assert "H" in species
            assert slices["H" + "H"] == slice(0, upperDiag)
            assert slices["H" + "O"] == slice(upperDiag, upperDiag + fullmat)
            # redundant
            assert slices["O" + "H"] == slice(upperDiag, upperDiag + fullmat)
            assert slices["O" + "O"] == slice(
                upperDiag + fullmat, 2 * upperDiag + fullmat
            )

        soapGroup = f.require_group("SOAPsparse")
        SOAPify.saponifyMultipleTrajectories(
            f["Trajectories"],
            soapGroup,
            rcut,
            n_max,
            l_max,
            SOAPkwargs={"sparse": True},
            useSoapFrom="dscribe",
        )
        assert soapGroup["testH2O"].attrs["n_max"] == n_max
        assert soapGroup["testH2O"].attrs["l_max"] == l_max
        assert "O" in soapGroup["testH2O"].attrs["species"]
        assert "H" in soapGroup["testH2O"].attrs["species"]
        assert numpy.abs(soapGroup["testH2O"].attrs["r_cut"] - rcut) < 1e-8
        assert "centersIndexes" not in soapGroup["testH2O"].attrs
        upperDiag = int((l_max + 1) * (n_max) * (n_max + 1) / 2)
        assert soapGroup[f"testH2O"].shape[-1] == 2 * upperDiag + fullmat
        species, slices = SOAPify.getSlicesFromAttrs(soapGroup["testH2O"].attrs)
        print(slices)
        assert "O" in species
        assert "H" in species
        assert slices["H" + "H"] == slice(0, upperDiag)
        assert slices["H" + "O"] == slice(upperDiag, upperDiag + fullmat)
        assert slices["O" + "H"] == slice(upperDiag, upperDiag + fullmat)  # redundant
        assert slices["O" + "O"] == slice(upperDiag + fullmat, 2 * upperDiag + fullmat)

        soapGroup = f.require_group("SOAPOxygen")
        SOAPify.saponifyMultipleTrajectories(
            f["Trajectories"],
            soapGroup,
            10.0,
            n_max,
            l_max,
            SOAPatomMask=["O"],
            useSoapFrom="dscribe",
        )
        assert soapGroup["testH2O"].attrs["n_max"] == n_max
        assert soapGroup["testH2O"].attrs["l_max"] == l_max
        assert "O" in soapGroup["testH2O"].attrs["species"]
        assert "H" in soapGroup["testH2O"].attrs["species"]
        assert numpy.abs(soapGroup["testH2O"].attrs["r_cut"] - rcut) < 1e-8
        assert_array_equal(
            soapGroup["testH2O"].attrs["centersIndexes"], [i * 3 for i in range(nMol)]
        )


def test_overrideOutput(tmp_path):
    nMol = 27
    u = getUniverseWithWaterMolecules(nMol)
    fname = f"testH2O_override.hdf5"
    fname = tmp_path / fname
    HDF5er.MDA2HDF5(u, fname, "testH2O", override=True)
    n_max = 4
    l_max = 4
    rcut = 10.0
    with h5py.File(fname, "a") as f:
        soapGroup = f.require_group("SOAP")
        SOAPatomMask = [0, 1]
        SOAPify.saponifyMultipleTrajectories(
            f["Trajectories"],
            soapGroup,
            rcut,
            n_max,
            l_max,
            useSoapFrom="dscribe",
            centersMask=SOAPatomMask,
        )
        for SOAPoutDataset in soapGroup:
            for i in SOAPatomMask:
                assert i in soapGroup[SOAPoutDataset].attrs["centersIndexes"]
        SOAPatomMask = ["O"]
        with pytest.raises(ValueError):
            # raise exception if the user does not ask explicitly to override
            SOAPify.saponifyMultipleTrajectories(
                f["Trajectories"],
                soapGroup,
                rcut,
                n_max,
                l_max,
                useSoapFrom="dscribe",
                SOAPatomMask=SOAPatomMask,
            )
        SOAPify.saponifyMultipleTrajectories(
            f["Trajectories"],
            soapGroup,
            rcut,
            n_max,
            l_max,
            useSoapFrom="dscribe",
            SOAPatomMask=SOAPatomMask,
            doOverride=True,
        )
        for SOAPoutDataset in soapGroup:
            for i in [j for j in range(len(u.atoms)) if u.atoms.names[j] == "O"]:
                assert i in soapGroup[SOAPoutDataset].attrs["centersIndexes"]
        return
        SOAPify.saponifyMultipleTrajectories(
            f["Trajectories"],
            soapGroup,
            rcut,
            n_max,
            l_max,
            useSoapFrom="dscribe",
        )
        for SOAPoutDataset in soapGroup:
            assert "centersIndexes" not in soapGroup[SOAPoutDataset].attrs


def test_MathSOAP():
    rng = numpy.random.default_rng(12345)

    for i in range(5):
        size = rng.integers(2, 150)
        x = rng.random((size,))
        y = rng.random((size,))
        print(x, y)
        sks = SOAPify.simpleKernelSoap(x, y)
        numpy.testing.assert_almost_equal(
            sks,
            numpy.dot(x, y) / (numpy.linalg.norm(x) * numpy.linalg.norm(y)),
            decimal=8,
        )
        numpy.testing.assert_almost_equal(
            SOAPify.SOAPdistanceNormalized(
                x / numpy.linalg.norm(x), y / numpy.linalg.norm(y)
            ),
            numpy.sqrt(2.0 - 2.0 * sks),
            decimal=8,
        )
        numpy.testing.assert_almost_equal(
            SOAPify.simpleSOAPdistance(x, y),
            numpy.sqrt(2.0 - 2.0 * sks),
            decimal=8,
        )
        for n in range(2, 10):
            nks = SOAPify.KernelSoap(x, y, n)
            numpy.testing.assert_almost_equal(
                nks,
                (numpy.dot(x, y) / (numpy.linalg.norm(x) * numpy.linalg.norm(y))) ** n,
                decimal=8,
            )
            numpy.testing.assert_almost_equal(
                SOAPify.SOAPdistance(x, y, n),
                numpy.sqrt(2.0 - 2.0 * nks),
                decimal=8,
            )
