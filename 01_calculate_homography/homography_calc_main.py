"""
homography_calc_main.py

This script computes and evaluates planar homographies based on labeled 2D-2D point correspondences
between camera image coordinates and world coordinates. It is intended for camera calibration
or localization tasks, using a homography to transform image points to the ground plane.

Functionality:
- Loads labeled camera and world points from CSV files.
- Iterates through all non-colinear 4-point combinations to compute homographies.
- Evaluates each homography using average reprojection error.
- Selects the top-N% of homographies with the lowest error.
- Computes:
    - The best 2 individual homographies,
    - An average of all valid homographies,
    - An average of the best N% homographies.
- Saves the averaged best homography to a `.npy` file.
- Prints quantitative evaluation of each selected homography.

Configuration (config.py):
- `CAM_POINTS_PATH`, `WORLD_POINTS_PATH`: Paths to labeled 2D point CSVs.
- `AVG_BEST_HOMOGRAPHY_PATH`: Output path for saved average homography matrix.
- `PERCENTAGE_BEST_HOMOGRAPHIES`: Fraction of lowest-error homographies to average (e.g., 0.3 for 30%).

Requirements:
- NumPy
- Custom utility modules: `homography_calc_utils.py`, `config.py`
"""

import itertools
import numpy as np
from homography_calc_utils import (
    load_points,
    compute_homography,
    evaluate_homography,
    are_points_colinear,
    average_homographies,
    print_evaluation,
)
from config import CAM_POINTS_PATH, WORLD_POINTS_PATH, AVG_BEST_HOMOGRAPHY_PATH, PERCENTAGE_BEST_HOMOGRAPHIES
if __name__ == "__main__":
    cam_points, world_points, common_labels = load_points(CAM_POINTS_PATH, WORLD_POINTS_PATH)

    results = []
    for labels_subset in itertools.combinations(common_labels, 4):
        cam_subset = [cam_points[l] for l in labels_subset]
        world_subset = [world_points[l] for l in labels_subset]

        if are_points_colinear(world_subset):
            continue

        H = compute_homography(cam_subset, world_subset)
        avg_err, _ = evaluate_homography(H, cam_points, world_points)
        results.append((avg_err, H, labels_subset))

    print(f"Computed {len(results)} valid homographies.")

    # === Select Best Homographies ===
    results.sort(key=lambda x: x[0])
    best_homographies = results[:2]

    # === Best homographies are evaluated based on minimum reprojection error and given percentage===
    n_best = max(1, int(PERCENTAGE_BEST_HOMOGRAPHIES * len(results)))
    best_30_percent = results[:n_best]

    H_avg_best = average_homographies([r[1] for r in best_30_percent])
    np.save(AVG_BEST_HOMOGRAPHY_PATH, H_avg_best)

    # === Average overall for comparison purposes ===
    H_avg = average_homographies([r[1] for r in results])

    # === Evaluation ===
    print_evaluation(best_homographies[0][1], "Best Homography 1", cam_points, world_points)
    print_evaluation(best_homographies[1][1], "Best Homography 2", cam_points, world_points)
    print_evaluation(H_avg, "Average Homography", cam_points, world_points)
    print_evaluation(H_avg_best, f"Average of Best {PERCENTAGE_BEST_HOMOGRAPHIES*100:.0f}% Homographies ({n_best} sets)", cam_points, world_points)
