#!/usr/bin/env python

from argparse import ArgumentParser
import json
from os import path
from shlex import split as shlex_split
from subprocess import Popen, PIPE
import sys
from time import sleep

from .util import exit_with_interrupt, handle_keyboard_interrupt

ALLOWED_EXT_LIST = [".avi", ".flv", ".mkv", ".mov", ".mp4", ".webm"]


def parse_args():
    parser = ArgumentParser(
        description="A script for encoding videos in succession using ffmpeg."
    )
    parser.add_argument("input_file_paths", help="input files", nargs="+")
    parser.add_argument("--ffmpeg-options", help="ffmpeg options")
    parser.add_argument(
        "--interval", type=int, help="interval in seconds [0-3600]", default=0
    )
    parser.add_argument("--output-ext", help="output ext")
    parser.add_argument("--calc-metrics", action="store_true")
    return parser.parse_args()


def is_valid_video_file(video_path):
    _, ext = path.splitext(video_path)
    return ext.lower() in ALLOWED_EXT_LIST and path.isfile(video_path)


def get_output_path(input_file_path, output_ext):
    dirname = path.dirname(input_file_path)
    basename = path.basename(input_file_path)
    basename_without_ext, ext = path.splitext(basename)

    count = 1
    while True:
        output_path = path.join(dirname, f"output-{basename_without_ext[:64]}")
        if count > 1:
            output_path += f"-{count}"

        if output_ext:
            output_path += output_ext
        else:
            output_path += ext

        if not path.exists(output_path):
            return output_path
        count += 1

        if count > 100:
            print("Too many files with the same name")
            sys.exit(1)


def run_ffmpeg(input_filename, output_filename, options):
    ffmpeg_options = shlex_split(options)
    ffmpeg_command = (
        ["ffmpeg", "-i", input_filename] + ffmpeg_options + [output_filename]
    )
    try:
        process = Popen(ffmpeg_command)
        process.wait()
    except KeyboardInterrupt:
        process.wait()
        exit_with_interrupt()


def run_ffmpeg_quality_metrics(original, converted):
    ffmpeg_qm_command = ["ffmpeg-quality-metrics", converted, original]
    try:
        process = Popen(ffmpeg_qm_command, stdout=PIPE, text=True)
        stdout, _ = process.communicate()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        exit_with_interrupt()
    return stdout.strip()


def get_video_duration(video_path):
    ffprobe_command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        process = Popen(ffprobe_command, stdout=PIPE, text=True)
        stdout, _ = process.communicate()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        exit_with_interrupt()
    return float(stdout.strip())


def is_same_video_duration(original, converted):
    return abs(get_video_duration(original) - get_video_duration(converted)) < 0.05


def write_metrics_global(metrics_global, output_filename):
    output_basename = path.splitext(output_filename)[0]
    with open(f"{output_basename}-metrics.txt", "w") as f:
        f.write(json.dumps(metrics_global, indent=4))


def print_progress(current, total):
    print(f"\n{current} out of {total} files are encoded.")


def apply_interval(interval):
    if 0 < interval <= 3600:
        print(f"Waiting for {interval} seconds...")
        sleep(interval)


@handle_keyboard_interrupt
def main():
    args = parse_args()
    total_files_count = len(args.input_file_paths)

    for current_count, input_file_path in enumerate(args.input_file_paths, 1):
        if not is_valid_video_file(input_file_path):
            print(f"File {input_file_path} is not a valid video file path.")
            total_files_count -= 1
            continue

        if current_count != 1:
            apply_interval(args.interval)

        output_file_path = get_output_path(input_file_path, args.output_ext)
        run_ffmpeg(input_file_path, output_file_path, args.ffmpeg_options)

        if args.calc_metrics and is_same_video_duration(
            input_file_path, output_file_path
        ):
            sleep(10)
            metrics_json = run_ffmpeg_quality_metrics(input_file_path, output_file_path)
            metrics_global_dict = json.loads(metrics_json)["global"]
            write_metrics_global(metrics_global_dict, output_file_path)

        print_progress(current_count, total_files_count)
