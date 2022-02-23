"""
This file is responsible for providing interface to data stored inside a geojson file.
"""
import argparse
import json
import re
from math import atan2, cos, radians, sin, sqrt
from typing import List, Tuple


class GeojsonInterface:
    """
    A class that can read a geojson file and provide access to its contents
    """

    EXPECTED_GEOJSON_PATH_PATTERN = re.compile(".*\/[0-9]{4}\.geojson$")

    @staticmethod
    def geo_to_meters(geoloc1: List[float], geoloc2: List[float]) -> float:
        """
        Return the distance between two geo locations given as
        geoloc = [longitude, latitude]
        in meters
        """

        # Approximate radius of Earth in meters
        R = 6373000.0

        lat1 = radians(geoloc1[1])
        lon1 = radians(geoloc1[0])
        lat2 = radians(geoloc2[1])
        lon2 = radians(geoloc2[0])

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c

        return distance

    def __init__(self, geojson_path: str) -> None:
        """
        Check validity and load the provided geojson file
        """

        if not GeojsonInterface.EXPECTED_GEOJSON_PATH_PATTERN.match(geojson_path):
            raise ValueError('Invalid geojson file name')

        self.__geojson_path = geojson_path
        self.__video_id = int(geojson_path[-12:-8])
        self.__outlier_frames_num = 0
        self.__none_frames_num = 0
        self.__no_movement_frames_num = 0
        self.__frames_num = 0

        self.__frame_data = []
        self.__frame_times_s = []
        self.__frame_distances_m = []
        self.__frame_speeds_ms = []
        self.__frame_speeds_kmh = []

        self.__load_geojson_file()

        self.__calculate_relative_times_and_speeds()

    def __load_geojson_file(self) -> None:
        """
        Loads per frame data from the file
        Removes invalid coordinates and extreme outliers
        Converts Unix time to seconds
        """
        # Read geo data consisting of frames
        with open(self.__geojson_path, 'r') as fin:
            self.__frame_data = json.loads(fin.read())

        # Remove None frames
        i = len(self.frame_coordinates) - 1
        while i >= 0:
            if self.frame_coordinates[i] is None:
                del self.__frame_data['geometry']['coordinates'][i]
                del self.__frame_data['properties']['AbsoluteUtcMicroSec'][i]
                del self.__frame_data['properties']['RelativeMicroSec'][i]
                self.__none_frames_num += 1
            i -= 1

        # Remove drastic outliers
        i = len(self.__frame_data['geometry']['coordinates']) - 2
        threshold_m = 20.0
        while i >= 0:
            if GeojsonInterface.geo_to_meters(
                    self.frame_coordinates[i],
                    self.frame_coordinates[i + 1]) > threshold_m:
                del self.__frame_data['geometry']['coordinates'][i]
                del self.__frame_data['properties']['AbsoluteUtcMicroSec'][i]
                del self.__frame_data['properties']['RelativeMicroSec'][i]
                self.__outlier_frames_num += 1
            i -= 1

        # Confirm data validity
        coordinates_num = len(self.frame_coordinates)
        absolute_time_num = len(self.frame_abs_microsecs)
        relative_time_num = len(self.frame_rel_microsecs)
        assert coordinates_num == absolute_time_num and coordinates_num == relative_time_num
        self.__frames_num = coordinates_num

    def __calculate_relative_times_and_speeds(self) -> None:
        """
        Calculates frame durations, distances covered and movement speeds in seconds
        """
        # Convert time data to seconds
        self.__frame_times_s = [time / 1000.0 for time in self.frame_rel_microsecs]

        # Calculate per frame movement distance
        self.__frame_distances_m = [
            GeojsonInterface.geo_to_meters(self.frame_coordinates[i], self.frame_coordinates[i + 1])
            for i in range(self.frames_num - 1)
        ]

        # Calculate speeds
        for frame_id in range(self.frames_num):
            look_from = max(frame_id - 10, 0)
            look_to = min(frame_id + 10, self.frames_num)
            total_distance = sum([d for d in self.__frame_distances_m[look_from:look_to - 1]])
            total_time = self.__frame_times_s[look_to - 1] - self.__frame_times_s[look_from]
            self.__frame_speeds_ms.append(total_distance / total_time)
            self.__frame_speeds_kmh.append(total_distance / total_time / 1000.0 * 3600.0)

    def remove_no_movement(self, frame_range: int, min_distance_m: float) -> None:
        """
        Cuts-off parts of the recording without movement
        """
        assert self.__frames_num == len(self.frame_coordinates)

        frames_to_remove = []

        removed_micro_sec = 0

        distance_range = sum(self.__frame_distances_m[:2 * frame_range + 1])
        for frame_id in range(frame_range, self.__frames_num - frame_range):
            # Check if the frame should be removed
            distance_range = sum(self.__frame_distances_m[frame_id - frame_range:frame_id + frame_range + 1])
            if distance_range < min_distance_m:
                # The frame should be removed
                # Accumulate it's time
                removed_micro_sec += (self.frame_rel_microsecs[frame_id + 1] - self.frame_rel_microsecs[frame_id])
                # Add to the removal list
                frames_to_remove.append(frame_id)
            else:
                # The frame should not be remoed, updates it's timing
                self.__frame_data['properties']['AbsoluteUtcMicroSec'][frame_id] -= removed_micro_sec
                self.__frame_data['properties']['RelativeMicroSec'][frame_id] -= removed_micro_sec
                self.__frame_times_s[frame_id] -= removed_micro_sec / 1000.0

        for frame_id in frames_to_remove[::-1]:
            del self.__frame_data['geometry']['coordinates'][frame_id]
            del self.__frame_data['properties']['AbsoluteUtcMicroSec'][frame_id]
            del self.__frame_data['properties']['RelativeMicroSec'][frame_id]
            del self.__frame_times_s[frame_id]
            del self.__frame_distances_m[frame_id]
            del self.__frame_speeds_ms[frame_id]
            del self.__frame_speeds_kmh[frame_id]
        self.__no_movement_frames_num = len(frames_to_remove)
        self.__frames_num = len(self.frame_coordinates)

    def get_lat_long_in_meters(self) -> Tuple[List[float], List[float]]:
        """
        Converts latitude and longitude coordinates to meters
        Average latitude and longitude are taken as the coordinate system center
        """
        # Get frame position coordinates
        lats = [x[1] for x in self.frame_coordinates]
        lons = [x[0] for x in self.frame_coordinates]

        # Prepare the distance unit scaling
        min_lat_frame = lats.index(min(lats))
        max_lat_frame = lats.index(max(lats))
        min_lon_frame = lons.index(min(lons))
        max_lon_frame = lons.index(max(lons))
        d_lat = GeojsonInterface.geo_to_meters(
            [lats[min_lat_frame], lons[min_lat_frame]],
            [lats[max_lat_frame], lons[min_lat_frame]])
        d_lon = GeojsonInterface.geo_to_meters(
            [lats[min_lon_frame], lons[min_lon_frame]],
            [lats[min_lon_frame], lons[max_lon_frame]])
        avg_lons = (max(lons) + min(lons)) / 2.0
        avg_lats = (max(lats) + min(lats)) / 2.0

        # Calculate graph data values
        x_coords = [((x - avg_lons) / (max(lons) - min(lons))) * d_lon for x in lons]
        y_coords = [((x - avg_lats) / (max(lats) - min(lats))) * d_lat for x in lats]

        return x_coords, y_coords

    @property
    def geojson_path(self) -> str:
        """
        Provides path to the original geojson file
        """
        return self.__geojson_path

    @property
    def video_id(self) -> int:
        """
        Keeps the numerical id of the current video set
        """
        return self.__video_id

    @property
    def outlier_frames_num(self) -> int:
        """
        Counts number of frames removed due to being too far away from the base
        """
        return self.__outlier_frames_num

    @property
    def none_frames_num(self) -> int:
        """
        Counts number of frames removed due to being too coordinates being None
        """
        return self.__none_frames_num

    @property
    def no_movement_frames_num(self) -> int:
        """
        Counts number of frames removed due to no movement being detected
        """
        return self.__no_movement_frames_num

    @property
    def frames_num(self) -> int:
        """
        Number of valid data frames
        """
        return self.__frames_num

    @property
    def frame_coordinates(self) -> int:
        """
        Accesses the raw frame coordinates data
        """
        return self.__frame_data['geometry']['coordinates']

    @property
    def frame_abs_microsecs(self) -> int:
        """
        Accesses the raw frame absolute microsecond data
        """
        return self.__frame_data['properties']['AbsoluteUtcMicroSec']

    @property
    def frame_rel_microsecs(self) -> int:
        """
        Accesses the raw frame relative microsecond data
        """
        return self.__frame_data['properties']['RelativeMicroSec']

    @property
    def frame_times_s(self) -> int:
        """
        Frame duration in seconds
        """
        return self.__frame_times_s

    @property
    def frame_distances_m(self) -> int:
        """
        Distances covered during a frame in meters
        """
        return self.__frame_distances_m

    @property
    def frame_speeds_ms(self) -> int:
        """
        Frame speeds in meters per second
        """
        return self.__frame_speeds_ms

    @property
    def frame_speeds_kmh(self) -> int:
        """
        Frame speeds in kilometers per hour
        """
        return self.__frame_speeds_kmh


def demo() -> None:
    """
    Demos some of the interface functionality on the provided geojson file
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'geojson_file_path',
        type=str,
        help='File path to the requested geojson file')
    args = parser.parse_args()

    interface = GeojsonInterface(args.geojson_file_path)

    print('Geojson path: {}'.format(interface.geojson_path))
    print('Video set id: {}'.format(interface.video_id))
    print('Removed outliers: {}'.format(interface.outlier_frames_num))
    print('Removed Nones: {}'.format(interface.none_frames_num))
    print('Valid frames: {}'.format(interface.frames_num))
    print('Average speed: {} km/h'.format(sum(interface.frame_speeds_kmh) / interface.frames_num))
    print('Max speed: {} km/h'.format(max(interface.frame_speeds_kmh)))

if __name__ == '__main__':
    demo()
