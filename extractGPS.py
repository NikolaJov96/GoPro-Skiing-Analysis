"""
This file is responsible for iterating through a requested directory and running GPS extraction
for each chaptered video.
"""
import argparse
import os
from pathlib import Path


def main() -> None:
    # Analyze command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'video_directory_path',
        type=str,
        help='Path to a directory containing GoPro videos to be iterated')
    parser.add_argument(
        'geojson_directory_path',
        type=str,
        help='Path to a geojson output directory')
    args = parser.parse_args()

    found_videos = {}

    # Find videos and the number of chapters
    for video_chapter_path in Path(args.video_directory_path).rglob('*.MP4'):
        # Create video chapter properties
        video_chapter_name = os.path.basename(video_chapter_path)
        video_directory_path = os.path.dirname(video_chapter_path)
        chapter_id = int(video_chapter_name[2:4])
        video_id = int(video_chapter_name[4:8])

        if video_id not in found_videos:
            # Add new video
            found_videos[video_id] = {
                'video_id': video_id,
                'chapters': chapter_id,
                'dir': video_directory_path
            }
        else:
            # Update existing video
            found_videos[video_id]['chapters'] = max(found_videos[video_id]['chapters'], chapter_id)

    # Extract GPS from concatenated videos
    os.makedirs(args.geojson_directory_path, exist_ok=True)
    failed_video_ids = []
    for i, video in enumerate(found_videos.values()):
        # Get video properties
        video_id = video['video_id']
        chapters = video['chapters']
        directory = video['dir']

        # Create the video chapter file list
        video_file_list = [os.path.join(directory, 'GH{:02}{:04}.MP4'.format(chapter + 1, video_id)) for chapter in range(chapters)]
        video_file_list = [f'"{video_file}"' for video_file in video_file_list]

        # Create the external analysis command
        output_file = os.path.join(args.geojson_directory_path, '{:04}.geojson'.format(video_id))
        cmd = 'node ./GPSExtractor/extractGPS.js {} {}'.format(output_file, ' '.join(video_file_list))
        print('Video: {}/{}'.format(i + 1, len(found_videos)))
        print(cmd)
        if os.system(cmd) == 0:
            print('success')
        else:
            failed_video_ids.append(video_id)
            print('failed')

    print()
    if len(failed_video_ids) == 0:
        print('all data successfully extracted')
    else:
        print('Data extraction failed for videos:')
        for video_id in failed_video_ids:
            print(video_id)


if __name__ == '__main__':
    main()
