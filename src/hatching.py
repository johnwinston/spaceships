"""Crosshatch pattern generation for pen plotters.

Vendored from the johnwinston/plotter repo (src/hatching.py) -- the
engine behind the original plotted Game of Life cards.  Unit-agnostic:
feed it rectangles in mm and it hatches in mm.  Emits paths as command
tuples; impose.paths_to_d serializes them for SVG.
"""

import math
from typing import List, Tuple, Dict, Set
from collections import defaultdict


class HatchGenerator:
    """Generates crosshatch patterns for rectangular regions.

    Uses the eggbot hatching algorithm to create plotter-optimized
    fill patterns with smooth curve connections between segments.
    """

    def __init__(self, spacing: float = 2.0, angle: float = 45.0,
                 crosshatch: bool = True, inset: float = 0.5):
        """Initialize hatch generator.

        Args:
            spacing: Distance between hatch lines in pixels
            angle: Angle of hatch lines in degrees
            crosshatch: If True, add perpendicular hatches
            inset: Distance to inset hatches from edges in pixels
        """
        self.spacing = spacing
        self.angle = angle
        self.crosshatch = crosshatch
        self.inset = inset

    def generate_for_rectangles(
        self,
        rectangles: List[Tuple[float, float, float, float]],
        connect_segments: bool = True,
        connection_radius: float = 3.0
    ) -> List[List[Tuple]]:
        """Generate hatch patterns for a list of rectangles.

        Args:
            rectangles: List of (x, y, width, height) tuples
            connect_segments: If True, connect nearby segments with curves
            connection_radius: Search radius for connections (multiple of spacing)

        Returns:
            List of paths, where each path is a list of drawing commands:
            - ('M', x, y) - Move to point
            - ('L', x, y) - Line to point
            - ('C', x1, y1, x2, y2, x, y) - Cubic Bezier curve
        """
        if not rectangles:
            return []

        # Convert rectangles to polygon edges with rectangle indices
        polygon_edges = []
        rect_indices = []

        for rect_idx, (x, y, w, h) in enumerate(rectangles):
            # Apply inset if requested
            if self.inset > 0:
                x += self.inset
                y += self.inset
                w -= 2 * self.inset
                h -= 2 * self.inset
                if w <= 0 or h <= 0:
                    continue

            # Create 4 edges: top, right, bottom, left
            edges = [
                ((x, y), (x + w, y)),           # top
                ((x + w, y), (x + w, y + h)),   # right
                ((x + w, y + h), (x, y + h)),   # bottom
                ((x, y + h), (x, y))            # left
            ]
            polygon_edges.extend(edges)
            rect_indices.extend([rect_idx] * len(edges))

        if not polygon_edges:
            return []

        # Find bounding box
        all_points = []
        for edge in polygon_edges:
            all_points.extend(edge)

        min_x = min(p[0] for p in all_points)
        max_x = max(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_y = max(p[1] for p in all_points)

        # Expand bounding box slightly
        bbox_margin = self.spacing * 2
        min_x -= bbox_margin
        max_x += bbox_margin
        min_y -= bbox_margin
        max_y += bbox_margin

        bbox_width = max_x - min_x
        bbox_height = max_y - min_y
        bbox_diag = math.sqrt(bbox_width**2 + bbox_height**2)

        # Generate hatch lines at specified angles
        angles = [self.angle]
        if self.crosshatch:
            angles.append(self.angle + 90)

        all_hatch_segments = []

        for angle in angles:
            angle_rad = math.radians(angle)
            cos_angle = math.cos(angle_rad)
            sin_angle = math.sin(angle_rad)

            num_lines = int(bbox_diag / self.spacing) + 2

            for i in range(num_lines):
                offset = i * self.spacing - bbox_diag / 2

                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2

                # Perpendicular direction for the hatch line
                perp_x = -sin_angle
                perp_y = cos_angle

                # Offset in the angle direction
                offset_x = cos_angle * offset
                offset_y = sin_angle * offset

                # Create a long line segment that spans the bounding box
                p1 = (center_x + offset_x - perp_x * bbox_diag,
                      center_y + offset_y - perp_y * bbox_diag)
                p2 = (center_x + offset_x + perp_x * bbox_diag,
                      center_y + offset_y + perp_y * bbox_diag)

                # Find all intersections with polygon edges
                intersections = []
                for edge_idx, edge in enumerate(polygon_edges):
                    p3, p4 = edge
                    s = self._line_intersect(p1, p2, p3, p4)
                    if 0.0 <= s <= 1.0:
                        intersections.append((s, rect_indices[edge_idx]))

                # Sort by intersection position
                intersections.sort(key=lambda x: x[0])

                # Remove duplicate positions
                unique_intersections = []
                last_s = -1.0
                for s, rect_idx in intersections:
                    if abs(s - last_s) > 1e-9:
                        unique_intersections.append((s, rect_idx))
                        last_s = s

                # Apply odd/even rule: segments between odd-even pairs are inside
                for j in range(0, len(unique_intersections) - 1, 2):
                    s1, rect_idx1 = unique_intersections[j]
                    s2, rect_idx2 = unique_intersections[j + 1]

                    segment_rect_idx = rect_idx1 if rect_idx1 == rect_idx2 else rect_idx1

                    # Calculate actual line segment coordinates
                    x1 = p1[0] + s1 * (p2[0] - p1[0])
                    y1 = p1[1] + s1 * (p2[1] - p1[1])
                    x2 = p1[0] + s2 * (p2[0] - p1[0])
                    y2 = p1[1] + s2 * (p2[1] - p1[1])

                    # Only add if line segment is long enough
                    length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    if length >= self.spacing * 0.25:
                        all_hatch_segments.append((x1, y1, x2, y2, segment_rect_idx))

        # Connect segments if requested
        if connect_segments and all_hatch_segments:
            return self._connect_hatch_segments(
                all_hatch_segments, connection_radius
            )
        else:
            # Return as simple line paths
            return [
                [('M', seg[0], seg[1]), ('L', seg[2], seg[3])]
                for seg in all_hatch_segments
            ]

    def _connect_hatch_segments(
        self,
        segments: List[Tuple[float, float, float, float, int]],
        connection_radius: float
    ) -> List[List[Tuple]]:
        """Connect nearby hatch segment endpoints with smooth Bezier curves.

        Only connects segments within the same rectangle.

        Args:
            segments: List of (x1, y1, x2, y2, rect_idx) tuples
            connection_radius: Search radius (multiple of spacing)

        Returns:
            List of connected paths
        """
        if not segments:
            return []

        # Group segments by rectangle
        segments_by_rect = defaultdict(list)
        for i, seg in enumerate(segments):
            rect_idx = seg[4]
            segments_by_rect[rect_idx].append((i, seg))

        all_paths = []

        for rect_idx, rect_segments in segments_by_rect.items():
            used = set()
            threshold_sq = (self.spacing * connection_radius) ** 2

            for start_local_idx, (start_idx, start_seg) in enumerate(rect_segments):
                if start_idx in used:
                    continue

                # Start a new path
                path = []
                current_idx = start_idx
                current_end = 1  # 1 = end point (x2,y2)

                used.add(current_idx)
                seg = start_seg

                # Add first segment
                path.append(('M', seg[0], seg[1]))
                path.append(('L', seg[2], seg[3]))
                current_point = (seg[2], seg[3])

                # Try to find and connect nearby segments
                while True:
                    best_idx = None
                    best_end = None
                    best_dist_sq = threshold_sq

                    # Search for nearest unused segment endpoint
                    for local_idx, (idx, seg) in enumerate(rect_segments):
                        if idx in used:
                            continue

                        for end in [0, 1]:
                            if end == 0:
                                point = (seg[0], seg[1])
                            else:
                                point = (seg[2], seg[3])

                            dx = point[0] - current_point[0]
                            dy = point[1] - current_point[1]
                            dist_sq = dx * dx + dy * dy

                            if dist_sq < best_dist_sq:
                                best_dist_sq = dist_sq
                                best_idx = idx
                                best_end = end

                    if best_idx is None:
                        break

                    # Connect to the best segment
                    used.add(best_idx)

                    # Find the segment data for best_idx
                    best_seg = None
                    for local_idx, (idx, seg) in enumerate(rect_segments):
                        if idx == best_idx:
                            best_seg = seg
                            break

                    if best_end == 0:
                        next_start = (best_seg[0], best_seg[1])
                        next_end = (best_seg[2], best_seg[3])
                    else:
                        next_start = (best_seg[2], best_seg[3])
                        next_end = (best_seg[0], best_seg[1])

                    # Calculate direction vectors for smooth Bezier curve
                    prev_seg = path[-1]
                    if prev_seg[0] == 'L':
                        prev_point = (path[-2][1], path[-2][2]) if len(path) > 1 else current_point
                        in_dx = current_point[0] - prev_point[0]
                        in_dy = current_point[1] - prev_point[1]
                    else:
                        in_dx = current_point[0] - path[0][1]
                        in_dy = current_point[1] - path[0][2]

                    # Outgoing direction
                    out_dx = next_end[0] - next_start[0]
                    out_dy = next_end[1] - next_start[1]

                    # Normalize and create control points
                    in_len = math.sqrt(in_dx**2 + in_dy**2)
                    out_len = math.sqrt(out_dx**2 + out_dy**2)

                    if in_len > 0 and out_len > 0:
                        # Control point distance (0.75 * spacing)
                        control_dist = self.spacing * 0.75

                        # First control point extends from current point
                        cp1_x = current_point[0] + (in_dx / in_len) * control_dist
                        cp1_y = current_point[1] + (in_dy / in_len) * control_dist

                        # Second control point extends backward from next start
                        cp2_x = next_start[0] - (out_dx / out_len) * control_dist
                        cp2_y = next_start[1] - (out_dy / out_len) * control_dist

                        # Add cubic Bezier curve
                        path.append(('C', cp1_x, cp1_y, cp2_x, cp2_y,
                                   next_start[0], next_start[1]))
                    else:
                        # Fallback to straight line
                        path.append(('L', next_start[0], next_start[1]))

                    # Add the new segment
                    path.append(('L', next_end[0], next_end[1]))
                    current_point = next_end
                    current_idx = best_idx

                all_paths.append(path)

        return all_paths

    @staticmethod
    def _line_intersect(p1: Tuple[float, float], p2: Tuple[float, float],
                       p3: Tuple[float, float], p4: Tuple[float, float]) -> float:
        """Calculate intersection of two line segments.

        Returns the fractional distance along line p1-p2 where intersection occurs,
        or -1.0 if no intersection.

        Args:
            p1, p2: Endpoints of first line (the hatch line)
            p3, p4: Endpoints of second line (polygon edge)

        Returns:
            Fractional distance along p1-p2 (0.0 to 1.0) or -1.0
        """
        d21x = p2[0] - p1[0]
        d21y = p2[1] - p1[1]
        d43x = p4[0] - p3[0]
        d43y = p4[1] - p3[1]

        # Denominator
        d = d21x * d43y - d21y * d43x

        # Lines are parallel if d == 0
        if d == 0:
            return -1.0

        # Check if intersection is within the polygon edge (p3-p4)
        nb = (p1[1] - p3[1]) * d21x - (p1[0] - p3[0]) * d21y
        sb = float(nb) / float(d)
        if sb < 0 or sb > 1:
            return -1.0

        # Check if intersection is within the hatch line (p1-p2)
        na = (p1[1] - p3[1]) * d43x - (p1[0] - p3[0]) * d43y
        sa = float(na) / float(d)
        if sa < 0 or sa > 1:
            return -1.0

        return sa
