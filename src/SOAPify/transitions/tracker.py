from ..classify import SOAPclassification

import numpy

#: the index of the component of the statetracker that stores the previous state
TRACK_PREVSTATE = 0
#: the index of the component of the statetracker that stores the current state
TRACK_CURSTATE = 1
#: the index of the component of the statetracker that stores the next state
TRACK_ENDSTATE = 2
#: the index of the component of the statetracker that stores the duration of the state, in frames
TRACK_EVENTTIME = 3


def _createStateTracker(
    prevState: int, curState: int, endState: int, eventTime: int = 0
) -> numpy.ndarray:
    """Compile the given collection of data in a state tracker

    Args:
        prevState (int): the id of the previous state
        curState (int): the id of the current state
        endState (int): the id of the next state
        eventTime (int, optional): the duration (in frames) of this event. Defaults to 0.

    Returns:
        numpy.ndarray: the state tracker
    """
    return numpy.array([prevState, curState, endState, eventTime], dtype=int)


# TODO add stride/window here
def trackStates(classification: SOAPclassification) -> list:
    """Creates an ordered list of events for each atom in the classified trajectory
    each event is a numpy.array with four compontents: the previous state, the current state, the final state and the duration of the current state

    Args:
        classification (SOAPclassification): the classified trajectory

    Returns:
        list: ordered list of events for each atom in the classified trajectory
    """
    nofFrames = classification.references.shape[0]
    nofAtoms = classification.references.shape[1]
    stateHistory = []
    # should I use a dedicated class?
    for atomID in range(nofAtoms):
        statesPerAtom = []
        atomTraj = classification.references[:, atomID]
        # TODO: this can be made concurrent per atom

        # the array is [start state, state, end state,time]
        # when PREVSTATE and CURSTATE are the same the event is the first event for the atom in the simulation
        # when ENDSTATE and CURSTATE are the same the event is the last event for the atom in the simulation
        stateTracker = _createStateTracker(
            prevState=atomTraj[0],
            curState=atomTraj[0],
            endState=atomTraj[0],
            eventTime=0,
        )
        for frame in range(1, nofFrames):
            if atomTraj[frame] != stateTracker[TRACK_CURSTATE]:
                stateTracker[TRACK_ENDSTATE] = atomTraj[frame]
                statesPerAtom.append(stateTracker)
                stateTracker = _createStateTracker(
                    prevState=stateTracker[TRACK_CURSTATE],
                    curState=atomTraj[frame],
                    endState=atomTraj[frame],
                )

            stateTracker[TRACK_EVENTTIME] += 1
        # append the last event
        statesPerAtom.append(stateTracker)
        stateHistory.append(statesPerAtom)
    return stateHistory


def RemoveAtomIdentityFromEventTracker(statesTracker: list) -> list:
    """Merge all of the list of stateTracker into a single lists, by removing the information of what atom did a given event.


    Args:
        statesTracker (list): a list of list of state trackers, organized by atoms

    Returns:
        list: the list of stateTracker organized only by states
    """
    if isinstance(statesTracker[0], list):
        t = []
        for tracks in statesTracker:
            t += tracks
        return t
    return statesTracker


def getResidenceTimesFromStateTracker(
    statesTracker: list, legend: list
) -> "list[numpy.ndarray]":
    """Given a state tracker and the list of the states returns the list of residence times per state

    Args:
        statesTracker (list): a list of list of state trackers, organized by atoms, or a list of state trackers
        legend (list): the list of states

    Returns:
        list[numpy.ndarray]: an ordered list of the residence times for each state
    """
    states = RemoveAtomIdentityFromEventTracker(statesTracker)

    residenceTimes = [[] for i in range(len(legend))]
    for event in states:
        residenceTimes[event[TRACK_CURSTATE]].append(
            event[TRACK_EVENTTIME]
            if event[TRACK_ENDSTATE] != event[TRACK_CURSTATE]
            else -event[TRACK_EVENTTIME]
        )
    for i in range(len(residenceTimes)):
        residenceTimes[i] = numpy.sort(numpy.array(residenceTimes[i]))
    return residenceTimes


def transitionMatrixFromStateTracker(
    statesTracker: list, legend: list
) -> numpy.ndarray:
    """Generates the unnormalized matrix of the transitions from a statesTracker

    see :func:`calculateTransitionMatrix` for a detailed description of an unnormalized transition matrix

    Args:
        statesTracker (list): a list of list of state trackers, organized by atoms, or a list of state trackers
        legend (list): the list of states

    Returns:
        numpy.ndarray[float]: the unnormalized matrix of the transitions
    """
    states = RemoveAtomIdentityFromEventTracker(statesTracker)

    nclasses = len(legend)
    transMat = numpy.zeros((nclasses, nclasses), dtype=numpy.float64)
    # print(len(states), states[0], file=sys.stderr)
    for event in states:
        transMat[event[TRACK_CURSTATE], event[TRACK_CURSTATE]] += (
            event[TRACK_EVENTTIME] - 1
        )

        # the transition matrix is genetated with:
        #   classFrom = data.references[frameID - stride][atomID]
        #   classTo = data.references[frameID][atomID]
        transMat[event[TRACK_PREVSTATE], event[TRACK_CURSTATE]] += 1
    return transMat
