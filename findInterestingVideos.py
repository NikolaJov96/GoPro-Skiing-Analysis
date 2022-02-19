"""
This file is responsible for iterating through a requested directory and analyzing geojson files.
"""
import argparse
from pathlib import Path

from tqdm import tqdm

from geojsonInterface import GeojsonInterface


def main() -> None:
    # Analyze command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'directory_path',
        type=str,
        help='Path to a directory to be iterated')
    args = parser.parse_args()
    dir_path = args.directory_path

    # Find and analyze geojson files
    valid_videos = []
    for geojson_path in tqdm(list(Path(dir_path).rglob('*.geojson'))):
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

    # Display valid video information
    for i, valid_video in enumerate(valid_videos):
        print()
        print('Progress: {}/{}'.format(i + 1, len(valid_videos)))
        print('Video id: {}'.format(valid_video.video_id))
        print('Number of frames: {}'.format(valid_video.frames_num))
        print('Average speed: {} km/h'.format(sum(valid_video.frame_speeds_kmh) / valid_video.frames_num))
        print('Outlier frames num: {}'.format(valid_video.outlier_frames_num))
        valid_video.plot_trajectory()


if __name__ == '__main__':
    main()
