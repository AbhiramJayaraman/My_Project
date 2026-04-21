"""
Multi-Camera Data Fusion Engine for Object Tracking System

OVERVIEW:
This module implements the core data fusion algorithm that combines object tracking data
from multiple Raspberry Pi cameras into globally consistent tracks. It handles track
matching, data fusion, global ID management, and state estimation across different
camera viewpoints.

MAIN FUNCTIONS:
1. Collects track data from multiple RPIs (up to 3 cameras)
2. Matches corresponding tracks across different camera views
3. Filters out unstable tracks using minimum age threshold
4. Fuses position, color, and confidence data from multiple sources
5. Applies Kalman filter per global track for position smoothing
6. Maintains global track IDs for consistent object identification
7. Handles missing or unavailable camera data gracefully

INPUTS:
- Track data from individual RPIs containing:
  * Local track IDs and positions [x, y]
  * Object labels (person, car, etc.)
  * Average colors in BGR format
  * Confidence scores
  * Timestamps for temporal alignment
- Configuration thresholds from config module:
  * POSITION_THRESHOLD: Maximum distance for track matching
  * COLOR_THRESHOLD: Maximum color difference for matching
  * MIN_CONFIDENCE: Minimum confidence for track consideration
  * TIME_THRESHOLD: Maximum time difference for temporal matching
  * MIN_AGE: Minimum number of frames a track must persist before being eligible for fusion
  * Kalman filter parameters: KALMAN_DT, KALMAN_Q_POSITION, KALMAN_Q_VELOCITY, KALMAN_R_VALUE, KALMAN_INITIAL_COVARIANCE

OUTPUTS:
- Fused track dictionary with global IDs:
  * global_id: Unique identifier (e.g., "GLOBAL_001")
  * label: Object class from reference track
  * position: Kalman-filtered position from fused inputs
  * avg_colour: Averaged RGB color from all sources
  * confidence: Averaged confidence score
  * timestamp: Fusion processing time
  * source_rpis: List of contributing cameras
  * source_tracks: Original (rpi_id, track_id) pairs
  * num_sources: Number of cameras that detected this object

FUSION ALGORITHM:
1. Three-phase processing:
   - Phase 1: Use RPI1 tracks as reference, find matches in RPI2/RPI3
   - Phase 2: Process remaining RPI2 tracks, find matches in RPI3
   - Phase 3: Process remaining RPI3 tracks individually

2. Track matching criteria (all must pass):
   - Label match: Same object class
   - Position match: Distance ≤ POSITION_THRESHOLD
   - Color match: Color difference ≤ COLOR_THRESHOLD
   - Time match: Timestamp difference ≤ TIME_THRESHOLD

3. Minimum Age Filtering:
   - Tracks must persist for at least MIN_AGE frames before being considered for fusion
   - Prevents flickering global tracks due to transient or noisy detections

4. Kalman Filtering:
   - Each global track is smoothed using a dedicated 2D Kalman filter
   - Improves position estimates by incorporating temporal continuity

5. Global ID management:
   - Maintains track continuity across frames
   - Reuses existing global IDs when track composition matches
   - Creates new global IDs for new track combinations

DATA STRUCTURES:
- data_buffer: {rpi_id: {track_id: track_data}} - incoming data storage
- global_tracks: {global_id: track_info} - current global tracks
- used_tracks: set of processed track keys - prevents double assignment
- prev_fused_tracks: {global_id: set(source_tracks)} - track continuity
- track_ages: {(rpi_id, track_id): int} - track age counter
- kalman_filters: {global_id: Kalman2D} - smoothing filters per global track

ROBUST OPERATION:
- Handles 1, 2, or 3 active cameras dynamically
- Filters immature or unstable detections using aging logic
- Smooths fused positions using Kalman prediction and update
- Gracefully processes missing or empty camera data
- Thread-safe operations for concurrent access
- Maintains track continuity even with intermittent camera failures

USAGE:
- Called by main system after receiving track data from RPIs
- Processes all available camera data simultaneously
- Returns fused and filtered tracks for publication to subscribers
"""


from collections import defaultdict
import numpy as np
import threading
from datetime import datetime
from config import POSITION_THRESHOLD, COLOR_THRESHOLD, MIN_CONFIDENCE, TIME_THRESHOLD, KALMAN_DT,KALMAN_Q_POSITION,KALMAN_R_VALUE,KALMAN_Q_VELOCITY,KALMAN_INITIAL_COVARIANCE,MIN_AGE

class Kalman2D:
    def __init__(self):
        self.dt = 1.0  # time interval (can be tuned)
        self.u = np.zeros((4, 1))  # control input

        # State: [x, y, vx, vy]
        self.x = np.zeros((4, 1))

        # State transition matrix
        self.F = np.array([
            [1, 0, self.dt, 0],
            [0, 1, 0, self.dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])

        # Observation model
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])

        # Initial covariance
        self.P = np.eye(4) * KALMAN_INITIAL_COVARIANCE

        # Process noise
        self.Q = np.array([
            [KALMAN_Q_POSITION, 0, 0, 0],
            [0, KALMAN_Q_POSITION, 0, 0],
            [0, 0, KALMAN_Q_VELOCITY, 0],
            [0, 0, 0, KALMAN_Q_VELOCITY]
        ])

        # Measurement noise
        self.R = np.eye(2) * KALMAN_R_VALUE

    def predict(self):
        self.x = self.F @ self.x + self.u
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x[:2].flatten()

    def update(self, z):
        z = np.reshape(z, (2, 1))
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P



class DataFusion:
    """
    Multi-RPI data fusion system for tracking objects across multiple Raspberry Pi cameras.
    
    This class handles:
    - Collecting track data from multiple RPIs
    - Matching tracks across different camera views
    - Creating globally consistent track IDs
    - Fusing position and color data from multiple sources
    """


    def __init__(self):
        """Initialize the data fusion engine with empty buffers and counters."""
        self.data_buffer = defaultdict(dict)  # {rpi_id: {track_id: track_data}} - stores incoming track data
        self.global_tracks = {}  # {global_id: track_info} - stores fused global tracks
        self.used_tracks = set()  # tracks already assigned to global IDs - prevents double assignment
        self.global_id_counter = 1  # counter for generating unique global IDs
        self.lock = threading.Lock()  # thread safety for multi-threaded access
        self.prev_fused_tracks = {}  # global_id -> set of (rpi_id, track_id) - maintains track continuity
        self.kalman_filters = {}  # global_id -> Kalman2D instance
        self.track_ages = defaultdict(int) #track age counter
        
    def find_matching_previous_global_id(self, current_source_tracks):
        """
        Find if current track combination matches a previous global track.
        
        Input: current_source_tracks - list of (rpi_id, track_id) tuples for current fusion
        Output: global_id (string) if match found, None otherwise
        Purpose: Maintains track continuity across frames by reusing global IDs
        """

        max_overlap = 0
        best_match = None

        current_set = set(current_source_tracks)  # convert to set for intersection operations

        for global_id, previous_set in self.prev_fused_tracks.items():
            overlap = len(current_set.intersection(previous_set))

            # Apply logic based on how many RPIs are contributing
            if len(current_set) == 1 and overlap >= 1:
                return global_id
            elif len(current_set) == 2 and overlap >= 1:
                return global_id
            elif len(current_set) == 3 and overlap >= 2:
                return global_id

        return None # no suitable match found

        
    def add_track_data(self, rpi_id, track_data):
        """
        Add track data from a specific RPI to the fusion buffer.
        
        Input: rpi_id (string) - identifier for the RPI source
               track_data (dict) - dictionary of track_id -> track_info
        Output: None
        Purpose: Collects data from multiple RPIs for fusion processing
        """
        with self.lock:
            # Only update if there's actual track data
            if track_data:
                self.data_buffer[rpi_id] = track_data
                for track_id in track_data.keys():
                    self.track_ages[(rpi_id, track_id)] += 1
                print(f" Added {len(track_data)} tracks from {rpi_id} to fusion buffer")
            else:
                # Clear empty data but keep the key to show RPI is active but has no tracks
                self.data_buffer[rpi_id] = {}
                print(f" {rpi_id} active but no tracks detected")
    def is_track_mature(self,rpi_id,track_id):
        """
        Check if a track has reached minimum age.
        """
        return self.track_ages[(rpi_id, track_id)] >= MIN_AGE
    def calculate_distance(self, pos1, pos2):
        """
        Calculate Euclidean distance between two 2D positions.
        
        Input: pos1, pos2 - lists/tuples containing [x, y] coordinates
        Output: float - Euclidean distance between positions
        Purpose: Measures spatial similarity for track matching
        """
        try:
            if len(pos1) >= 2 and len(pos2) >= 2:
                return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
            return float('inf')
        except:
            return float('inf')
    
    def calculate_color_difference(self, color1, color2):
        """
        Calculate color difference in RGB space.
        
        Input: color1, color2 - lists containing [R, G, B] values
        Output: float - Euclidean distance in RGB color space
        Purpose: Measures color similarity for track matching
        """
        try:
            if len(color1) >= 3 and len(color2) >= 3:
                return np.sqrt(sum((a - b)**2 for a, b in zip(color1[:3], color2[:3])))
            return float('inf')
        except:
            return float('inf')
    
    def convert_bgr_to_rgb(self, bgr_color):
        """
        Convert BGR color format to RGB format.
        
        Input: bgr_color - list containing [B, G, R] values
        Output: list containing [R, G, B] values
        Purpose: Standardizes color format since OpenCV uses BGR but RGB is more standard
        """
        if len(bgr_color) >= 3:
            return [bgr_color[2], bgr_color[1], bgr_color[0]]  # BGR to RGB
        return bgr_color
    
    def find_matching_tracks(self, reference_track, other_rpi_data, rpi_id, reference_time):   #time
        """
        Find tracks in another RPI that match the reference track.
        
        Input: reference_track - dict with position, label, color, confidence data
               other_rpi_data - dict of track_id -> track_data from another RPI
               rpi_id - string identifier for the other RPI
               reference_time - timestamp of reference track
        Output: list of matching track dictionaries with similarity scores
        Purpose: Identifies corresponding tracks across different camera views
        """
        matches = []
        ref_pos = reference_track.get("position", [0, 0])
        ref_label = reference_track.get("label", "")
        ref_label = ref_label.split()[0]
        ref_color = self.convert_bgr_to_rgb(reference_track.get("avg_colour", [0, 0, 0]))
        ref_confidence = reference_track.get("confidence", 0)
        
        
        if ref_confidence < MIN_CONFIDENCE:
            return matches
            
        for track_id, track_data in other_rpi_data.items():
            track_key = f"{rpi_id}_{track_id}"
            if track_key in self.used_tracks:
                continue
              
                
            other_pos = track_data.get("position", [0, 0])
            other_label = track_data.get("label", "")
            other_label = other_label.split()[0]
            other_color = self.convert_bgr_to_rgb(track_data.get("avg_colour", [0, 0, 0]))
            other_confidence = track_data.get("confidence", 0)
            #if other_confidence < MIN_CONFIDENCE:
                #continue
                
                # Check timestamp alignment
            other_time = track_data.get("timestamp", 0)  #time
            if abs(reference_time - other_time) > TIME_THRESHOLD:
                continue  # Time misaligned, skip
                
            # Check label match
            if ref_label == other_label:
                  
                # Check position threshold
                distance = self.calculate_distance(ref_pos, other_pos)
                if distance <= POSITION_THRESHOLD:
                    # Check color similarity
                    color_diff = self.calculate_color_difference(ref_color, other_color)
                    if color_diff <= COLOR_THRESHOLD:
                        matches.append({
                            'rpi_id': rpi_id,
                            'track_id': track_id,
                            'track_data': track_data,
                            'distance': distance,
                            'color_diff': color_diff,
                            'track_key': track_key
                        })
        
        return matches
    
    def fuse_tracks(self):
        """
        Main data fusion algorithm - combines tracks from multiple RPIs into global tracks.
        
        Input: None (uses internal data buffer)
        Output: dict of global_id -> fused_track_data
        Purpose: Creates globally consistent tracks by matching and fusing data from multiple cameras
        """
        with self.lock:
            if len(self.data_buffer) == 0:
                return {}
                
            fused_tracks = {}
            self.used_tracks.clear()
            
            # Get available RPI data (some may be empty or missing)
            rpi1_data = self.data_buffer.get('rpi1', {})
            rpi2_data = self.data_buffer.get('rpi2', {})
            rpi3_data = self.data_buffer.get('rpi3', {})
            
            # Check which RPIs have data
            available_rpis = []
            if rpi1_data:
                available_rpis.append('rpi1')
            if rpi2_data:
                available_rpis.append('rpi2')
            if rpi3_data:
                available_rpis.append('rpi3')
            
            print(f" Data Fusion Status:")
            print(f"  Available RPIs: {available_rpis} ({len(available_rpis)}/3)")
            print(f"  RPI1 tracks: {len(rpi1_data)}, RPI2 tracks: {len(rpi2_data)}, RPI3 tracks: {len(rpi3_data)}")
            
            if len(available_rpis) == 0:
                print(f"  No RPI data available for fusion")
                return {}
            elif len(available_rpis) == 1:
                print(f" Single RPI mode: Only {available_rpis[0]} has data")
            elif len(available_rpis) == 2:
                print(f" Dual RPI mode: Fusing data from {available_rpis}")
            else:
                print(f" Full fusion mode: All 3 RPIs participating")
            
            # Flexible fusion algorithm based on available RPIs
            if 'rpi1' in available_rpis:
                # Phase 1: Process RPI1 tracks as reference
                for track_id, track_data in rpi1_data.items():
                    # --- START MIN_AGE FILTER ---
                    if self.track_ages.get(('rpi1', track_id), 0) < MIN_AGE:
                        continue
                    # --- END MIN_AGE FILTER ---
                    ref_track_key = f"rpi1_{track_id}"
                    if ref_track_key in self.used_tracks:
                        continue
                        
                    # Find matches in available RPIs only
                    rpi2_matches = []
                    rpi3_matches = []
                    
                    ref_time = track_data.get("timestamp", 0) #time
                    
                    if 'rpi2' in available_rpis:
                        rpi2_matches = self.find_matching_tracks(track_data, rpi2_data, 'rpi2', ref_time)
                        # --- START MIN_AGE FILTER ON MATCHES ---
                        rpi2_matches = [m for m in rpi2_matches if
                                        self.track_ages.get(('rpi2', m['track_id']), 0) >= MIN_AGE]
                        # --- END MIN_AGE FILTER ON MATCHES ---

                    if 'rpi3' in available_rpis:
                        rpi3_matches = self.find_matching_tracks(track_data, rpi3_data, 'rpi3', ref_time)
                        # --- START MIN_AGE FILTER ON MATCHES ---
                        rpi3_matches = [m for m in rpi3_matches if
                                        self.track_ages.get(('rpi3', m['track_id']), 0) >= MIN_AGE]
                        # --- END MIN_AGE FILTER ON MATCHES ---
                    

                    
                    # Collect all matching tracks
                    all_tracks = [{'rpi_id': 'rpi1', 'track_id': track_id, 'track_data': track_data}]
                    
                    # Add best match from each available RPI
                    if rpi2_matches:
                        best_rpi2 = min(rpi2_matches, key=lambda x: x['distance'] + x['color_diff'])
                        all_tracks.append(best_rpi2)
                        self.used_tracks.add(best_rpi2['track_key'])
                    
                    if rpi3_matches:
                        best_rpi3 = min(rpi3_matches, key=lambda x: x['distance'] + x['color_diff'])
                        all_tracks.append(best_rpi3)
                        self.used_tracks.add(best_rpi3['track_key'])
                        
                    # Create global track
                    current_source_tracks = [(t['rpi_id'], t['track_id']) for t in all_tracks]
                    global_id = self.find_matching_previous_global_id(current_source_tracks)

                    if not global_id:
                        global_id = f"GLOBAL_{self.global_id_counter:03d}"
                        self.global_id_counter += 1    
                    
                    # Create fused track
                    fused_track = self.create_fused_track(global_id, all_tracks, track_data)
                    pos = fused_track['position']
                    fused_tracks[global_id] = fused_track
                    self.prev_fused_tracks[global_id] = set(current_source_tracks)
                    self.used_tracks.add(ref_track_key)
            
            # Phase 2: Process remaining RPI2 tracks (if RPI2 is available)
            if 'rpi2' in available_rpis:
                for track_id, track_data in rpi2_data.items():
                    # --- START MIN_AGE FILTER ---
                    if self.track_ages.get(('rpi2', track_id), 0) < MIN_AGE:
                        continue
                    # --- END MIN_AGE FILTER ---
                    track_key = f"rpi2_{track_id}"
                    if track_key in self.used_tracks:
                        continue
                        
                    # Find matches in RPI3 (if available)
                    rpi3_matches = []
                    
                    ref_time = track_data.get("timestamp", 0)
                    if 'rpi3' in available_rpis:
                        rpi3_matches = self.find_matching_tracks(track_data, rpi3_data, 'rpi3', ref_time)
                        # --- START MIN_AGE FILTER ON MATCHES ---
                        rpi3_matches = [m for m in rpi3_matches if
                                        self.track_ages.get(('rpi3', m['track_id']), 0) >= MIN_AGE]
                        # --- END MIN_AGE FILTER ON MATCHES ---
                    
                    if rpi3_matches:
                        # RPI2 + RPI3 fusion
                        best_rpi3 = min(rpi3_matches, key=lambda x: x['distance'] + x['color_diff'])
                        all_tracks = [
                            {'rpi_id': 'rpi2', 'track_id': track_id, 'track_data': track_data},
                            best_rpi3
                        ]
                        self.used_tracks.add(best_rpi3['track_key'])
                    else:
                        # RPI2 only
                        all_tracks = [{'rpi_id': 'rpi2', 'track_id': track_id, 'track_data': track_data}]
                        
                    current_source_tracks = [(t['rpi_id'], t['track_id']) for t in all_tracks]
                    global_id = self.find_matching_previous_global_id(current_source_tracks)

                    if not global_id:
                        global_id = f"GLOBAL_{self.global_id_counter:03d}"
                        self.global_id_counter += 1    
                    
                    # Create fused track
                    fused_track = self.create_fused_track(global_id, all_tracks, track_data)
                    pos = fused_track['position']
                    fused_tracks[global_id] = fused_track
                    self.prev_fused_tracks[global_id] = set(current_source_tracks)
                    self.used_tracks.add(track_key)
            
            # Phase 3: Process remaining RPI3 tracks (if RPI3 is available)
            if 'rpi3' in available_rpis:
                for track_id, track_data in rpi3_data.items():
                    # --- START MIN_AGE FILTER ---
                    if self.track_ages.get(('rpi3', track_id), 0) < MIN_AGE:
                        continue
                    # --- END MIN_AGE FILTER ---
                    track_key = f"rpi3_{track_id}"
                    if track_key in self.used_tracks:
                        continue
                        
                    all_tracks = [{'rpi_id': 'rpi3', 'track_id': track_id, 'track_data': track_data}]
                    
                    # Create individual track for RPI3
                    current_source_tracks = [(t['rpi_id'], t['track_id']) for t in all_tracks]
                    global_id = self.find_matching_previous_global_id(current_source_tracks)

                    if not global_id:
                        global_id = f"GLOBAL_{self.global_id_counter:03d}"
                        self.global_id_counter += 1
                        
                    fused_track = self.create_fused_track(global_id, all_tracks, track_data)
                    pos = fused_track['position']
                    fused_tracks[global_id] = fused_track
                    self.prev_fused_tracks[global_id] = set(current_source_tracks)
                    self.used_tracks.add(track_key)
            
            print(f" Fusion complete: Generated {len(fused_tracks)} global tracks from {len(available_rpis)} RPIs")
            return fused_tracks
    
    def create_fused_track(self, global_id, all_tracks, reference_track_data):
        """
        Create a fused track by combining data from multiple source tracks.
        
        Input: global_id - string identifier for the global track
               all_tracks - list of track dictionaries from different RPIs
               reference_track_data - dict with reference track properties
        Output: dict containing fused track data with averaged properties
        Purpose: Combines multiple camera views into single, more accurate track
        """
        # Calculate fused position (average)
        positions = [t['track_data'].get('position', [0, 0]) for t in all_tracks]
        valid_positions = [pos for pos in positions if len(pos) >= 2]
        
        if valid_positions:
            avg_position = [
                sum(pos[0] for pos in valid_positions) / len(valid_positions),
                sum(pos[1] for pos in valid_positions) / len(valid_positions)
            ]
        else:
            avg_position = [0, 0]
        
        # Calculate average color
        colors = [self.convert_bgr_to_rgb(t['track_data'].get('avg_colour', [0, 0, 0])) for t in all_tracks]
        valid_colors = [color for color in colors if len(color) >= 3]
        
        if valid_colors:
            avg_color = [
                int(sum(color[i] for color in valid_colors) / len(valid_colors))
                for i in range(3)
            ]
        else:
            avg_color = [0, 0, 0]

        if global_id not in self.kalman_filters:
           self.kalman_filters[global_id] = Kalman2D()
           self.kalman_filters[global_id].x[:2] = np.array(avg_position).reshape(2, 1)

        kf = self.kalman_filters[global_id]
        kf.predict()
        kf.update(avg_position)
        filtered_pos = kf.x[:2].flatten().tolist()    
        
        # Calculate average confidence
        confidences = [t['track_data'].get('confidence', 0) for t in all_tracks]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Return comprehensive fused track data
        return {
            'global_id': global_id,
            'label': reference_track_data.get('label', 'unknown'),
            'position': filtered_pos,
            'avg_colour': avg_color,  # RGB format
            'confidence': avg_confidence,
            'timestamp': datetime.now().timestamp(),
            'source_rpis': [t['rpi_id'] for t in all_tracks],
            'source_tracks': [(t['rpi_id'], t['track_id']) for t in all_tracks],
            'num_sources': len(all_tracks)
        }

# Global data fusion instance
fusion_engine = DataFusion()
