"""Assignment 1 - Simulation

=== CSC148 Fall 2017 ===
Diane Horton and David Liu
Department of Computer Science,
University of Toronto


=== Module Description ===

This file contains the Simulation class, which is the main class for your
bike-share simulation.

At the bottom of the file, there is a sample_simulation function that you
can use to try running the simulation at any time.
"""
import csv
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple

from bikeshare import Ride, Station
from container import PriorityQueue
from visualizer import Visualizer

# Datetime format to parse the ride data
DATETIME_FORMAT = '%Y-%m-%d %H:%M'


class Simulation:
    """Runs the core of the simulation through time.

    === Attributes ===
    all_rides:
        A list of all the rides in this simulation.
        Note that not all rides might be used, depending on the timeframe
        when the simulation is run.
    all_stations:
        A dictionary containing all the stations in this simulation.
    visualizer:
        A helper class for visualizing the simulation.
    active rides:
        A list o all rides that are in progress at the current time in
        the simulation
    """
    all_stations: Dict[str, Station]
    all_rides: List[Ride]
    visualizer: Visualizer
    active_rides: List[Ride]
    event_list: List['Event']

    def __init__(self, station_file: str, ride_file: str) -> None:
        """Initialize this simulation with the given configuration settings.
        """
        self.visualizer = Visualizer()
        self.all_stations = create_stations(station_file)
        self.all_rides = create_rides(ride_file, self.all_stations)
        self.active_rides = []
        self.event_list = PriorityQueue()

    def run(self, start: datetime, end: datetime) -> None:
        """Run the simulation from <start> to <end>.
        """
        step = timedelta(minutes=1)  # Each iteration spans one minute of time

        for ride in self.all_rides:
            if ride.start_time > start or start <= ride.end_time <= end:
                start_event = RideStartEvent(self, ride.start_time)
                self.event_list.add(start_event)
        simulation_start = start
        while not start > end:
            self._update_active_rides_fast(start)
            if not start == simulation_start:
                self.low_avail_check()
                self.low_occ_check()
            drawables = self.active_rides + list(self.all_stations.values())
            self.visualizer.render_drawables(drawables +
                                             self.active_rides, start)
            start += step
        # Leave this code at the very bottom of this method.
        # It will keep the visualization window open until you close
        # it by pressing the 'X'.
        while True:
            if self.visualizer.handle_window_events():
                return  # Stop the simulation

    def low_avail_check(self):
        """Check whether station's current state is "low available".
        If it is update station's low availability time
        """
        for id_ in self.all_stations:
            station = self.all_stations[id_]
            if station.is_low_availability():
                station.low_avail += 60.0

    def low_occ_check(self):
        """Check whether station's current state is "low unoccupied."
        If it is update station's low availability time
        """
        for id_ in self.all_stations:
            station = self.all_stations[id_]
            if station.is_low_unoccupied():
                station.low_occ += 60.0

    def _update_active_rides(self, time: datetime) -> None:
        """Update this simulation's list of active rides for the given time.

        REQUIRED IMPLEMENTATION NOTES:
        -   Loop through `self.all_rides` and compare each Ride's start and
            end times with <time>.

            If <time> is between the ride's start and end times (inclusive),
            then add the ride to self.active_rides if it isn't already in
            that list.

            Otherwise, remove the ride from self.active_rides if it is in
            that list.

        -   This means that if a ride started before the simulation's time
            period but ends during or after the simulation's time period,
            it should still be added to self.active_rides.
        """
        for ride in self.all_rides:
            if ride.start_time <= time <= ride.end_time:
                if ride not in self.active_rides:
                    if not ride.start.num_bikes == 0:
                        self.active_rides.append(ride)
                        ride.start.num_bikes -= 1
                        ride.start.rides_start += 1
                    else:
                        self.all_rides.remove(ride)
            else:
                if ride in self.active_rides:
                    if not ride.end.is_full():
                        ride.end.num_bikes += 1
                        ride.end.rides_end += 1
                    self.active_rides.remove(ride)

    def calculate_statistics(self) -> Dict[str, Tuple[str, float]]:
        """Return a dictionary containing statistics for this simulation.

        The returned dictionary has exactly four keys, corresponding
        to the four statistics tracked for each station:
          - 'max_start'
          - 'max_end'
          - 'max_time_low_availability'
          - 'max_time_low_unoccupied'

        The corresponding value of each key is a tuple of two elements,
        where the first element is the name (NOT id) of the station that has
        the maximum value of the quantity specified by that key,
        and the second element is the value of that quantity.

        For example, the value corresponding to key 'max_start' should be the
        name of the station with the most number of rides started at that
        station, and the number of rides that started at that station.
        """
        return {
            'max_start': (self.max_start()),
            'max_end': (self.max_end()),
            'max_time_low_availability': (self.lowest_avail()),
            'max_time_low_unoccupied': (self.lowest_occ())
        }

    def max_start(self):
        """Return the station and the amount
        with most rides that starts there
        """
        max_ = -1
        name = ''
        for id_ in self.all_stations:
            station = self.all_stations[id_]
            if station.rides_start > max_:
                max_ = station.rides_start
                name = station.name
            elif station.rides_start == max_:
                if station.name < name:
                    name = station.name
        return name, max_

    def max_end(self):
        """Return the station and the amount
        with most rides that starts there
        """
        max_ = -1
        name = ''
        for id_ in self.all_stations:
            station = self.all_stations[id_]
            if station.rides_end > max_:
                max_ = station.rides_end
                name = station.name
            elif station.rides_end == max_:
                if station.name < name:
                    name = station.name
        return name, max_

    def lowest_avail(self):
        """Return the station with longest time in the
        state of "low availability" and it's time
        """
        avail = -1
        name = ''
        for id_ in self.all_stations:
            station = self.all_stations[id_]
            if station.low_avail > avail:
                avail = station.low_avail
                name = station.name
            elif station.low_avail == avail:
                if station.name < name:
                    name = station.name
        return name, avail

    def lowest_occ(self):
        """Return the station with longest time in the
        state of "low unoccupied" and it's time
        """
        occ = -1
        name = ''
        for id_ in self.all_stations:
            station = self.all_stations[id_]
            if station.low_occ > occ:
                occ = station.low_occ
                name = station.name
            elif station.low_occ == occ:
                if station.name < name:
                    name = station.name
        return name, occ

    def _update_active_rides_fast(self, time: datetime) -> None:
        """Update this simulation's list of active rides for the given time.

        REQUIRED IMPLEMENTATION NOTES:
        -   see Task 5 of the assignment handout
        """
        if not self.event_list.is_empty():
            event = self.event_list.remove()
            if event.time > time:
                self.event_list.add(event)
            else:
                while event is not None and event.time == time:
                    new_events = event.process()
                    for event in new_events:
                        self.event_list.add(event)
                    event = None
                    if not self.event_list.is_empty():
                        event = self.event_list.remove()
                        if event.time > time:
                            self.event_list.add(event)


def create_stations(stations_file: str) -> Dict[str, 'Station']:
    """Return the stations described in the given JSON data file.

    Each key in the returned dictionary is a station id,
    and each value is the corresponding Station object.
    Note that you need to call Station(...) to create these objects!

    Precondition: stations_file matches the format specified in the
                  assignment handout.

    This function should be called *before* _read_rides because the
    rides CSV file refers to station ids.
    """
    # Read in raw data using the json library.
    with open(stations_file) as file:
        raw_stations = json.load(file)

    stations = {}
    for s in raw_stations['stations']:
        # Extract the relevant fields from the raw station JSON.
        # s is a dictionary with the keys 'n', 's', 'la', 'lo', 'da', and 'ba'
        # as described in the assignment handout.
        # NOTE: all of the corresponding values are strings, and so you need
        # to convert some of them to numbers explicitly using int() or float().
        id_ = s['n']
        name = s['s']
        position = s['lo'], s['la']  # CHANGGE INT AND FLOAT
        stored = s['da']
        capacity = s['da'] + s['ba']
        stations[id_] = Station(position, capacity, stored, name)
    return stations


def create_rides(rides_file: str,
                 stations: Dict[str, 'Station']) -> List['Ride']:
    """Return the rides described in the given CSV file.

    Lookup the station ids contained in the rides file in <stations>
    to access the corresponding Station objects.

    Ignore any ride whose start or end station is not present in <stations>.

    Precondition: rides_file matches the format specified in the
                  assignment handout.
    """
    rides = []
    with open(rides_file) as file:
        for line in csv.reader(file):
            # line is a list of strings, following the format described
            # in the assignment handout.
            #
            # Convert between a string and a datetime object
            # using the function datetime.strptime and the DATETIME_FORMAT
            # constant we defined above. Example:
            # >>> datetime.strptime('2017-06-01 8:00', DATETIME_FORMAT)
            # datetime.datetime(2017, 6, 1, 8, 0)
            start, end = line[1], line[3]
            if start and end in stations:
                times = (datetime.strptime(line[0], DATETIME_FORMAT),
                         datetime.strptime(line[2], DATETIME_FORMAT))
                ride = Ride(stations[start], stations[end], times)
                rides.append(ride)
    return rides


class Event:
    """An event in the bike share simulation.

    Events are ordered by their timestamp.
    """
    simulation: 'Simulation'
    time: datetime

    def __init__(self, simulation: 'Simulation', time: datetime) -> None:
        """Initialize a new event."""
        self.simulation = simulation
        self.time = time

    def __lt__(self, other: 'Event') -> bool:
        """Return whether this event is less than <other>.

        Events are ordered by their timestamp.
        """
        return self.time < other.time

    def process(self) -> List['Event']:
        """Process this event by updating the state of the simulation.

        Return a list of new events spawned by this event.
        """
        raise NotImplementedError


class RideStartEvent(Event):
    """An event corresponding to the start of a ride."""

    def process(self) -> List['Event']:
        """Process this event by updating the state of the simulation.

        Return a list of new events spawned by this event.
        """
        events = []
        for ride in self.simulation.all_rides:
            if ride.start_time == self.time:
                if not ride.start.num_bikes == 0:
                    ride.start.num_bikes -= 1
                    ride.start.rides_start += 1
                    self.simulation.active_rides.append(ride)
                    events.append(RideEndEvent(self.simulation, ride.end_time))
        return events


class RideEndEvent(Event):
    """An event corresponding to the end of a ride."""

    def process(self) -> List['Event']:
        """Process this event by updating the state of the simulation.

        Return a list of new events spawned by this event.
        """
        for ride in self.simulation.active_rides:
            if ride.end_time == self.time:
                self.simulation.active_rides.remove(ride)
                if not ride.end.is_full():
                    ride.end.num_bikes += 1
                    ride.end.rides_end += 1
        return []


def sample_simulation() -> Dict[str, Tuple[str, float]]:
    """Run a sample simulation. For testing purposes only."""
    sim = Simulation('stations.json', 'sample_rides.csv')
    sim.run(datetime(2017, 6, 1, 9, 35, 0),
            datetime(2017, 6, 1, 9, 45, 0))
    return sim.calculate_statistics()


if __name__ == '__main__':
    # Uncomment these lines when you want to check your work using python_ta!
    # import python_ta
    # python_ta.check_all(config={
    #     'allowed-io': ['create_stations', 'create_rides'],
    #     'allowed-import-modules': [
    #         'doctest', 'python_ta', 'typing',
    #         'csv', 'datetime', 'json',
    #         'bikeshare', 'container', 'visualizer'
    #     ]
    # })
    print(sample_simulation())
