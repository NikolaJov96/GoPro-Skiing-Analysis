"""
This file is responsible for iterating through a requested directory and analyzing geojson files.
The main use case is finding file with valid GPS data and displaying the trajectory for examination.
"""
import argparse
from pathlib import Path

import matplotlib.cm as cm
import matplotlib.pyplot as plt
from tqdm import tqdm

from geojsonInterface import GeojsonInterface


def display_trajectory(video: GeojsonInterface) -> None:
    """
    Displays a 3D chart of the GPS points
    """
    # Get 3D coordinates
    x_coords, y_coords = video.get_lat_long_in_meters()
    heights = [x[2] for x in video.frame_coordinates]

    # Get some scaling values
    d_lon = max(x_coords) - min(x_coords)
    d_lat = max(y_coords) - min(y_coords)
    d_height = max(heights) - min(heights)
    avg_height = (max(heights) + min(heights)) / 2.0

    # Determine point colors using speed
    max_recorded_speed = max(video.frame_speeds_kmh)
    colors = cm.jet([x / max_recorded_speed for x in video.frame_speeds_kmh])

    # Create the graph
    plt.figure()
    ax = plt.axes(projection='3d')
    ax.set_title('Video {} trajectory'.format(video.video_id))

    graph_range = max(d_lat, d_lon, d_height) * 1.1
    ax.set_xlim(-graph_range / 2.0, graph_range / 2.0)
    ax.set_ylim(-graph_range / 2.0, graph_range / 2.0)
    ax.set_zlim(avg_height - graph_range / 2.0, avg_height + graph_range / 2.0)

    ax.set_xlabel('horizontal distance [m]')
    ax.set_ylabel('horizontal distance [m]')
    ax.set_zlabel('elevation [m]')

    ax.scatter(x_coords, y_coords, heights, color=colors)

    plt.show()


def main() -> None:
    # Analyze command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'directory_path',
        type=str,
        help='Path to a directory to be iterated')
    parser.add_argument(
        '--display_trajectory',
        '-d',
        action='store_true',
        help='Whether to display trajectories visually')
    args = parser.parse_args()

    # Find and analyze geojson files
    found_videos = list(Path(args.directory_path).rglob('*.geojson'))
    valid_videos = []
    for geojson_path in tqdm(found_videos):
        geojson_path = str(geojson_path)
        try:
            geojsonInterface = GeojsonInterface(geojson_path)
            # To be accepted the video has to have
            # - Maximum speed over 20 km/h
            # - Distance traveled over 200 m
            # - Outlier frames under 30
            video_valid = \
                max(geojsonInterface.frame_speeds_kmh) > 20.0 and \
                sum(geojsonInterface.frame_distances_m) > 200.0 and \
                geojsonInterface.outlier_frames_num < 30
            if video_valid:
                valid_videos.append(geojsonInterface)
        except:
            pass

    print('Valid videos out of total: {}/{}'.format(len(valid_videos), len(found_videos)))

    # Display valid video information
    for i, valid_video in enumerate(valid_videos):
        print()
        print('Progress: {}/{}'.format(i + 1, len(valid_videos)))
        print('Video id: {}'.format(valid_video.video_id))
        print('Number of frames: {}'.format(valid_video.frames_num))
        print('Average speed: {} km/h'.format(sum(valid_video.frame_speeds_kmh) / valid_video.frames_num))
        print('Outlier frames num: {}'.format(valid_video.outlier_frames_num))

        if args.display_trajectory:
            # Visually inspect the trajectory
            display_trajectory(valid_video)


if __name__ == '__main__':
    main()
