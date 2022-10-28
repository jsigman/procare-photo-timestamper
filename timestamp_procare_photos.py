import datetime
import subprocess
import sys
from bdb import BdbQuit
from pathlib import Path
from typing import List

import pytz
from dateutil.tz import tzlocal
from PIL.ExifTags import TAGS

# The exif tag we want to write to
DATETIME_TAGS = {"DateTime", "DateTimeOriginal", "DateTimeDigitized"}
datetime_tag_ids = [x for x, v in TAGS.items() if v in DATETIME_TAGS]

OFFSET_TAGS = {"OffsetTime", "OffsetTimeOriginal", "OffsetTimeDigitized"}
offset_tag_ids = [x for x, v in TAGS.items() if v in OFFSET_TAGS]

local_timezone = tzlocal()


def _get_photo_paths(photos_dir: Path) -> List[Path]:
    # example: img_1650306747855986_photo.jpg
    return list(photos_dir.glob("img_*_photo.jpg"))


def _get_offset_time(timestamp: datetime.datetime) -> str:
    corrected_time = datetime.datetime.fromtimestamp(
        timestamp.timestamp(), local_timezone
    )
    offset = corrected_time - timestamp.replace(tzinfo=pytz.UTC)
    offset_hours = -1 * (offset.seconds // 3600)
    return f"{offset_hours:02d}:00"


def _timestamp_to_exif_string(timestamp: datetime.datetime) -> str:
    return timestamp.strftime("%Y:%m:%d %H:%M:%S")


def _get_timestamp_from_filename(filepath: Path) -> datetime.datetime:
    file_stem = filepath.stem

    # there should only be one of these
    number_string = next(x for x in file_stem.split("_") if x.isdigit())

    num_digits = len(number_string)
    assert num_digits > 10

    num_decimal_points = num_digits - 10
    unix_time = int(number_string) / (10**num_decimal_points)
    timestamp = datetime.datetime.fromtimestamp(unix_time)

    # sanity check
    assert timestamp.year > 2010 and timestamp.year < 2099

    return timestamp


def _add_timestamp_metadata_to_photo(filepath: Path) -> None:
    timestamp = _get_timestamp_from_filename(filepath)

    # write unix time to metadata
    timestamp_string = _timestamp_to_exif_string(timestamp)
    for tag in DATETIME_TAGS:
        subprocess.run(
            [
                "exiftool",
                f"-{tag}={timestamp_string}",
                str(filepath),
                "-overwrite_original",
            ]
        )

    offset_string = _get_offset_time(timestamp)
    for tag in OFFSET_TAGS:
        subprocess.run(
            [
                "exiftool",
                f"-{tag}={offset_string}",
                str(filepath),
                "-overwrite_original",
            ]
        )


def main(photos_dir: str):
    photos_dir = Path(photos_dir).resolve()
    assert photos_dir.exists()

    photo_paths = _get_photo_paths(photos_dir)
    for photo_path in photo_paths:
        try:
            _add_timestamp_metadata_to_photo(photo_path)
            print(f"Done processing: {photo_path}")
        except Exception as exc:
            if isinstance(exc, BdbQuit):
                raise exc
            print(f"Error processing:{photo_path}:")
            print(exc)


if __name__ == "__main__":
    main(sys.argv[1])
