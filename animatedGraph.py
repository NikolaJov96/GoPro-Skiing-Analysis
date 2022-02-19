"""
This script creates an animated graph of the movement GPS data.
"""
import argparse
from typing import Iterable

import matplotlib.animation as animation
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np

from geojsonInterface import GeojsonInterface


class GraphAnimator:
    """
    Class that takes a geojson interface object and creates a 3D animation
    """

    def __init__(
            self,
            video: GeojsonInterface,
            output_video_fps: float,
            speedup_coefficient: float,
            revolution_duration_s: float,
            output_video_file_path: str,
            verbose: bool = False) -> None:
        """
        Remember the assigned video
        """
        self.__video = video
        self.__output_video_fps = output_video_fps
        self.__speedup_coefficient = speedup_coefficient
        self.__revolution_duration_s = revolution_duration_s
        self.__output_video_file_path = output_video_file_path
        self.__verbose = verbose

        self.__output_frame_batches = []
        self.__output_frame_batches_num = 0
        self.__x_coords = []
        self.__y_coords = []
        self.__heights = []
        self.__colors = []
        self.__ax = None
        self.__graph = None

    def render(self) -> None:
        """
        Create the 3D animation
        """
        # Get frame position coordinates
        lats = [x[1] for x in self.__video.frame_coordinates]
        lons = [x[0] for x in self.__video.frame_coordinates]
        self.__heights = [x[2] for x in self.__video.frame_coordinates]

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
        d_height = max(self.__heights) - min(self.__heights)
        avg_lons = (max(lons) + min(lons)) / 2.0
        avg_lats = (max(lats) + min(lats)) / 2.0
        avg_height = (max(self.__heights) + min(self.__heights)) / 2.0

        # Calculate graph data values
        self.__x_coords = [((x - avg_lons) / (max(lons) - min(lons))) * d_lon for x in lons]
        self.__y_coords = [((x - avg_lats) / (max(lats) - min(lats))) * d_lat for x in lats]
        max_recorded_speed = max(self.__video.frame_speeds_kmh)
        self.__colors = cm.jet([x / max_recorded_speed for x in self.__video.frame_speeds_kmh])

        # Determine per output video frame coordinate sets
        output_seconds_per_frame = self.__speedup_coefficient / self.__output_video_fps
        self.__output_frame_batches = [[0]]
        current_time = self.__video.frame_times_s[0]
        for i in range(self.__video.frames_num):
            if self.__video.frame_times_s[i] < current_time + output_seconds_per_frame:
                self.__output_frame_batches[-1].append(i)
            else:
                while self.__video.frame_times_s[i] >= current_time + output_seconds_per_frame:
                    self.__output_frame_batches.append([max(i - 1, 0)])
                    current_time += output_seconds_per_frame
                self.__output_frame_batches[-1].append(i)

        # Replicate the last frame the number of times needed for one full camera revolution
        for i in range(int(self.__revolution_duration_s * self.__output_video_fps)):
            self.__output_frame_batches.append(self.__output_frame_batches[-1])

        self.__output_frame_batches_num = len(self.__output_frame_batches)

        if self.__verbose:
            print('Number of output frames: {}'.format(self.__output_frame_batches_num))
            frames_per_output_frame = [len(i) for i in self.__output_frame_batches]
            print('Average data points per output video frame: {}'.format(
                sum(frames_per_output_frame) / len(frames_per_output_frame)))

        # Initialize the graph
        fig = plt.figure(figsize=(12, 10))
        self.__ax = plt.axes(projection='3d')
        self.__ax.set_title('Video {} animation'.format(self.__video.video_id))
        graph_range = max(d_lat, d_lon, d_height) * 1.1
        self.__ax.set_xlim(-graph_range / 2.0, graph_range / 2.0)
        self.__ax.set_ylim(-graph_range / 2.0, graph_range / 2.0)
        self.__ax.set_zlim(avg_height - graph_range / 2.0, avg_height + graph_range / 2.0)
        self.__ax.set_xlabel('horizontal distance [m]')
        self.__ax.set_ylabel('horizontal distance [m]')
        self.__ax.set_zlabel('elevation [m]')

        # Create the 3D scatter plot
        self.__graph = self.__ax.scatter([], [], [])

        # Run the animation
        ani = animation.FuncAnimation(
            fig,
            self.animate,
            np.arange(self.__output_frame_batches_num),
            interval=1000 / self.__output_video_fps,
            blit=True)
        ani.save(self.__output_video_file_path)

    def animate(self, out_frame_id) -> Iterable:
        """
        Invoked by func animation to update the graph before rendering each frame
        """
        if self.__verbose:
            print('\rAnimating frame: {}/{}'.format(out_frame_id + 1, self.__output_frame_batches_num), end='')
            if out_frame_id == self.__output_frame_batches_num - 1:
                print()

        # Get the id of the final original frame to be included
        original_frame_id = self.__output_frame_batches[out_frame_id][-1]

        # Update scatter point postitions and colors
        self.__graph._offsets3d = (
            self.__x_coords[:original_frame_id],
            self.__y_coords[:original_frame_id],
            self.__heights[:original_frame_id])
        self.__graph.set_color(self.__colors[:original_frame_id])
        self.__graph._facecolor3d = self.__graph.get_facecolor()
        self.__graph._edgecolor3d = self.__graph.get_edgecolor()

        # Update camera view
        elev = (1.0 - out_frame_id / self.__output_frame_batches_num) * 25.0
        time_s = out_frame_id / self.__output_video_fps
        azim = (time_s / self.__revolution_duration_s - int(time_s / self.__revolution_duration_s)) * 360.0
        self.__ax.view_init(elev=elev, azim=azim)

        return self.__graph,


def main() -> None:
    """
    Main script method
    """
    # Analyze command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'geojson_file_path',
        type=str,
        help='File path to the requested geojson file')
    parser.add_argument(
        'output_video_file_path',
        type=str,
        help='File path to the created mp4 video')
    parser.add_argument(
        '--output_video_fps',
        '-fps',
        type=float,
        default=30.0,
        help='FPS of the output video file')
    parser.add_argument(
        '--speedup_coefficient',
        '-su',
        type=float,
        default=1.0,
        help='How many times to speedup the video')
    parser.add_argument(
        '--revolution_duration_s',
        '-rd',
        type=float,
        default=1.0,
        help='Duration of one camera rotation in seconds')
    args = parser.parse_args()
    geojson_file_path = args.geojson_file_path
    output_video_file_path = args.output_video_file_path
    output_video_fps = args.output_video_fps
    speedup_coefficient = args.speedup_coefficient
    revolution_duration_s = args.revolution_duration_s

    # Load the data
    video = GeojsonInterface(geojson_file_path)

    # Debug printout
    print('Video id: {}'.format(video.video_id))
    print('Number of frames: {}'.format(video.frames_num))
    print('Average speed: {} km/h'.format(sum(video.frame_speeds_kmh) / video.frames_num))
    print('Outlier frames num: {}'.format(video.outlier_frames_num))

    # Render the animation
    graphAnimator = GraphAnimator(
        video,
        output_video_fps,
        speedup_coefficient,
        revolution_duration_s,
        output_video_file_path,
        verbose=True)
    graphAnimator.render()


if __name__ == '__main__':
    main()
