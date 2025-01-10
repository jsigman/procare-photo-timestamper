import datetime
import subprocess
import sys
from bdb import BdbQuit
from pathlib import Path
from typing import List
import re
import pytz
from dateutil.tz import tzlocal
from PIL.ExifTags import TAGS

# The exif tag we want to write to
DATETIME_TAGS = {"DateTime", "DateTimeOriginal", "DateTimeDigitized"}
datetime_tag_ids = [x for x, v in TAGS.items() if v in DATETIME_TAGS]

OFFSET_TAGS = {"OffsetTime", "OffsetTimeOriginal", "OffsetTimeDigitized"}
offset_tag_ids = [x for x, v in TAGS.items() if v in OFFSET_TAGS]

local_timezone = tzlocal()


def _get_image_paths(directory: Path, pattern: str) -> List[Path]:
    return list(directory.glob(pattern))


def _get_offset_time(timestamp: datetime.datetime) -> str:
    corrected_time = datetime.datetime.fromtimestamp(
        timestamp.timestamp(), local_timezone
    )
    offset = corrected_time - timestamp.replace(tzinfo=pytz.UTC)
    offset_hours = -1 * (offset.seconds // 3600)
    return f"{offset_hours:02d}:00"

def extract_first_img_number(text) -> str:
    pattern = r'img_(\d+)_photo'  # captures digits between img_ and _photo
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Could not find img number in {text}")

def _timestamp_to_exif_string(timestamp: datetime.datetime) -> str:
    return timestamp.strftime("%Y:%m:%d %H:%M:%S")


def _get_timestamp_from_filename(filepath: Path) -> datetime.datetime:
    file_stem = filepath.stem

    # Take the first one if there are multiple
    number_string = extract_first_img_number(file_stem)

    num_digits = len(number_string)

    if num_digits > 10:
        num_decimal_points = num_digits - 10
        unix_time = int(number_string) / (10**num_decimal_points)
    else:
        unix_time = int(number_string)
    timestamp = datetime.datetime.fromtimestamp(unix_time)

    # sanity check
    assert timestamp.year > 2010 and timestamp.year < 2099

    return timestamp


def _add_timestamp_metadata_to_image(filepath: Path) -> None:
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

    photo_paths = _get_image_paths(photos_dir, "*img_*_photo*jpg")
    activity_paths = _get_image_paths(photos_dir, "*img_*_activity.jpg*")
    all_image_paths = photo_paths + activity_paths
    
    for image_path in all_image_paths:
        try:
            _add_timestamp_metadata_to_image(image_path)
            print(f"Done processing: {image_path}")
        except Exception as exc:
            if isinstance(exc, BdbQuit):
                raise exc
            print(f"Error processing: {image_path}:")
            print(exc)


if __name__ == "__main__":
    main(sys.argv[1])
