"""
This script adds information inferred from GPS data to the video.
"""
import argparse
import os
from pathlib import Path

import cv2
from wandb import Video

from geojsonInterface import GeojsonInterface


class VideoEditor:
    """
    """

    def __init__(
            self,
            geojson_file_path: str,
            video_directory_path: str,
            video_id: int,
            output_video_path: str,
            start_time: float = None,
            end_time: float = None) -> None:
        """
        """
        self.__geojson_file_path = geojson_file_path
        self.__video_directory_path = video_directory_path
        self.__video_id = video_id
        self.__output_video_path = output_video_path
        self.__start_time = start_time
        self.__end_time = end_time

    def edit(self) -> None:
        """
        """
        # Load GPS data
        gps = GeojsonInterface(self.__geojson_file_path)
        gps_frame_id = 0

        # Find number of chapters
        chapter_num = 0
        for video_chapter_path in Path(self.__video_directory_path).rglob('*.MP4'):
            video_chapter_name = os.path.basename(video_chapter_path)
            video_id = video_chapter_name[4:8]
            if video_id == self.__video_id:
                chapter_id = int(video_chapter_name[2:4])
                chapter_num = max(chapter_num, chapter_id)

        assert chapter_num > 0

        video_chapter_paths = [
            os.path.join(self.__video_directory_path, 'GH{:02d}{}.MP4'.format(chapter_id, self.__video_id))
            for chapter_id in range(1, chapter_num + 1)
        ]
        print(video_chapter_paths)

        video_chapters = [cv2.VideoCapture(chapter_path) for chapter_path in video_chapter_paths]

        # Get video metadata
        fps = video_chapters[0].get(cv2.CAP_PROP_FPS)
        resolution = (
            int(video_chapters[0].get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(video_chapters[0].get(cv2.CAP_PROP_FRAME_HEIGHT)))

        # Create the new video
        new_video = cv2.VideoWriter(self.__output_video_path, cv2.VideoWriter_fourcc(*"MPEG"), fps, resolution)

        # Edit video frames
        for chapter_id, chapter in enumerate(video_chapters):
            # Frame count of the current video chapter
            chapter_frame_num = int(chapter.get(cv2.CAP_PROP_FRAME_COUNT))

            while chapter.isOpened():
                this_frame_id = int(chapter.get(cv2.CAP_PROP_POS_FRAMES))
                if this_frame_id == 20000:
                    break

                r, frame = chapter.read()

                next_frame_id = int(chapter.get(cv2.CAP_PROP_POS_FRAMES))

                # Log
                print('\rChapter: {}/{} Frame: {}/{} - {}%'.format(
                        chapter_id + 1, chapter_num, next_frame_id, chapter_frame_num, next_frame_id * 100 // chapter_frame_num),
                    end='')

                # Check for invalid frames and the video end
                if not r:
                    assert this_frame_id == next_frame_id
                    continue

                assert this_frame_id + 1 == next_frame_id

                current_seconds = chapter.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                while gps_frame_id < gps.frames_num - 1 and gps.frame_times_s[gps_frame_id + 1] < current_seconds:
                    gps_frame_id += 1

                self.__add_speed(frame, gps.frame_speeds_kmh[gps_frame_id])
                self.__add_map(frame)

                new_video.write(frame)

                if next_frame_id >= chapter_frame_num:
                    break

            print()

        new_video.release()

    @staticmethod
    def __add_speed(frame, speed):
        """
        """
        cv2.putText(
            img=frame,
            text='{:0.0f} kmh'.format(speed),
            org=(150, 250),
            fontFace=cv2.FONT_HERSHEY_TRIPLEX,
            fontScale=3,
            color=(0, 255, 0),
            thickness=3)

    @staticmethod
    def __add_map(frame):
        """
        """
        pass


def main() -> None:
    """
    """
    # Analyze command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'video_directory_path',
        type=str,
        help='Path to a directory containing all chapters of the GoPro video')
    parser.add_argument(
        'video_id',
        type=str,
        help='Four-digit GoPro video id')
    parser.add_argument(
        'geojson_file_path',
        type=str,
        help='File path to the geojson file of the GoPro video')
    parser.add_argument(
        'output_video_path',
        type=str,
        help='File path to the output video')
    parser.add_argument(
        '--start_time',
        type=float,
        help='Time in the input video to start from')
    parser.add_argument(
        '--end_time',
        type=float,
        help='Time in the input video to end at')
    args = parser.parse_args()

    assert len(args.video_id) == 4
    assert str.lower(args.output_video_path[-4:]) == ".mp4"

    video_editor = VideoEditor(
        geojson_file_path=args.geojson_file_path,
        video_directory_path=args.video_directory_path,
        video_id=args.video_id,
        output_video_path=args.output_video_path,
        start_time=args.start_time,
        end_time=args.end_time)
    video_editor.edit()


if __name__ == '__main__':
    main()
