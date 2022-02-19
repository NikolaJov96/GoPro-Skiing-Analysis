# GoPro skiing analysis

A tool for extracting GPS data from GoPro videos and analyzing them in the context of skiing.

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

## Picking videos

A step needed if there are a lot of videos, with most of them having invalid GPS data (this was the reason for creating this script). To automatically analyze all of the videos and display some stats and movement plots of the valid ones, run:

```
python3 findInterestingVideos.py geojson_directory_path
```
