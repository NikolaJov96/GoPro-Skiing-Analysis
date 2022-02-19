/**
 * A file responsible for extracting GPS data from a GoPro video and storing it as a geojson file.
 */

const gpmfExtract = require('gpmf-extract');
const goproTelemetry = require(`gopro-telemetry`);
const fs = require('fs');

/**
 * Function for loading big files, see readme for more info
 *
 * @param {string} path Path to the file to be loaded
 */
function bufferAppender(path) {
    return function (mp4boxFile) {
        var stream = fs.createReadStream(path, { highWaterMark: 4 * 1024 * 1024 });
        var bytesRead = 0;
        stream.on('end', () => {
            mp4boxFile.flush();
        });
        stream.on('data', chunk => {
            var arrayBuffer = new Uint8Array(chunk).buffer;
            arrayBuffer.fileStart = bytesRead;
            mp4boxFile.appendBuffer(arrayBuffer);
            bytesRead += chunk.length;
        });
        stream.resume();
    };
}

// Check command line arguments validity
if (process.argv.length < 4) {
    console.log(`Usage: ${require('path').basename(__filename)} <geojson_out_file> <video_file_name> <video_file_name>...`);
    process.exit(1);
}

// Parse command line arguments
const geojsonOutFile = process.argv[2];
const files = process.argv.slice(3);

// Generate output
try {
    // Create a promise for each input file
    const promises = []
    for (const file of files) {
        promises.push(gpmfExtract(bufferAppender(file)));
    }

    // When all files are loaded, generate the output
    Promise.all(promises).then(extracted => {
        goproTelemetry(extracted, { preset: "geojson" }).then(telemetry => {
            fs.writeFileSync(geojsonOutFile, JSON.stringify(telemetry, null, 2));
        });
    });

} catch (err) {
    console.error(err);
}
