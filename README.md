# GoPro skiing analysis

A tool for extracting GPS data from GoPro videos and analyzing them in the context of skiing. The main purpose is finding videos with valid GPS data.

## GPS data extraction

Initialize GPS Extractor node app by running:

```
cd GPSExtractor
npm install
```

The extraction script will recursively iterate through the requested directory, find all videos, merge videos separated into chunks by the camera and generate `.geojson` files for each video. Extraction is executed by the `extractGPS.py` python script that utilizes the note app.

```
python3 extractGPS.py video_directory_path geojson_directory_path
```

The node app basically just wraps [this](https://github.com/JuanIrache/gpmf-extract) and [this](https://github.com/JuanIrache/gopro-telemetry) great library provided by [JuanIrache](https://github.com/JuanIrache).

## Picking videos

A step needed if there are a lot of videos, with most of them having invalid GPS data (this was the reason for creating this script). To automatically analyze all of the videos and display some stats and movement plots of the valid ones, run:

```
python3 findInterestingVideos.py geojson_directory_path --display_trajectory
```

## Creating an animated 3D plot

To create a fun animated 3D graph showing the movement trajectory, color coded using the movement speed, run the `animatedGraph.py`. Consult the script help `-h` for animation parameters such as the speedup coefficient and the camera revolution duration, and try out multiple combinations for the best results.

```
python3 animatedGraph.py geojson_file_path output_video_file_path --speedup_coefficient 12 --revolution_duration_s 8 --remove_no_movement
```

![Animated plot](ReadmeContent/animatedPlot.gif)
