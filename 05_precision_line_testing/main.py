"""
main.py

Runs the localization evaluation pipeline based on config.py.
"""

from config import LOG_PATH, SOURCE_TO_ANALYZE, TRACK_ID,AUTO_SELECT_TRACK, LINE_START, LINE_END, OUTPUT_DIR, ENABLE_PLOTTING
from data_parser import read_log_file, save_positions_to_csv,get_track_ids_in_log
from evaluation import compute_mae
from plot_utils import plot_positions_vs_line
import os


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    selected_track_id = TRACK_ID

    if AUTO_SELECT_TRACK:
        print("Auto track selection enabled. Scanning log...")
        track_ids = get_track_ids_in_log(LOG_PATH, SOURCE_TO_ANALYZE)
        print(f"Available track_ids are {track_ids}")
        if not track_ids:
            raise ValueError(f"No track IDs found for source '{SOURCE_TO_ANALYZE}'.")

        # Find the track with the most points
        max_len = 0
        for tid in track_ids:
            data,label = read_log_file(LOG_PATH, SOURCE_TO_ANALYZE, tid)
            if len(data) == 0:
                continue
            if len(data) > max_len:
                max_len = len(data)
                selected_track_id = tid

        print(f"Selected track: {selected_track_id} with {max_len} points.")

    track_data,label = read_log_file(LOG_PATH, SOURCE_TO_ANALYZE, selected_track_id)
    num_sources = track_data[0]['num_sources'] if SOURCE_TO_ANALYZE == "fused" and track_data else None
    output_csv = os.path.join(OUTPUT_DIR, f'{SOURCE_TO_ANALYZE}_{selected_track_id}_positions.csv')
    #save_positions_to_csv(track_data, output_csv)

    mae = compute_mae(track_data, LINE_START, LINE_END)

    if len(SOURCE_TO_ANALYZE) == 1:
        title = f'Detected vs true position of RPI{SOURCE_TO_ANALYZE} Track {selected_track_id} ({label})'
    else:
        title = f'Detected vs true position of {SOURCE_TO_ANALYZE} Track {selected_track_id} ({label}), with {num_sources} source(s)'
    mae_text = f"The MAE of {title} is {mae:.3f} centimeters"
    if ENABLE_PLOTTING:
        plot_positions_vs_line(track_data, LINE_START, LINE_END, title=title,mae_text = mae_text)


if __name__ == "__main__":
    main()
