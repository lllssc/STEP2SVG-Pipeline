import os
import sys
import argparse

import numpy as np
import cairosvg
from PIL import Image
from moviepy import ImageSequenceClip
from svgpathtools import svg2paths, Path, wsvg, Line, CubicBezier
from tqdm import tqdm


# Straight line style
LINE_STYLE = {
    "stroke": "#005E2A",
    "stroke-width": "1",
    "stroke-opacity": "1",
    "stroke-linecap": "round",
    "stroke-linejoin": "bevel",
    "fill": "none",
    "fill-rule": "evenodd",
}

# Bézier curves style
CURVE_STYLE = {
    "stroke": "#DC0502",
    "stroke-width": "1",
    "stroke-opacity": "1",
    "stroke-linecap": "round",
    "stroke-linejoin": "bevel",
    "fill": "none",
    "fill-rule": "evenodd",
}

# Final complete drawing: solid black lines
FINAL_STYLE = {
    "stroke": "black",
    "stroke-width": "1.25",
    "stroke-opacity": "1",
    "stroke-linecap": "round",
    "stroke-linejoin": "bevel",
    "fill": "none",
    "fill-rule": "evenodd",
}

# Node (anchor point) style — all black
NODE_RADIUS = 0.85
NODE_COLOR = "#031F34"


def ensure_dir(path: str) -> str:
    """Create the directory if it does not exist; return the path unchanged."""
    os.makedirs(path, exist_ok=True)
    return path


def is_straight_line(segment) -> bool:
    """Return True if the segment is a straight line."""
    return isinstance(segment, Line)


def is_bezier_curve(segment) -> bool:
    """Return True if the segment is a Bézier curve (cubic or quadratic)."""
    return isinstance(segment, CubicBezier)


def extract_nodes(paths: list):
    """Collect unique endpoints from all segments across a list of Paths.

    Returns a (nodes, colors, radii) tuple suitable for wsvg's
    nodes / node_colors / node_radii parameters.
    """
    points = set()
    for path in paths:
        for seg in path:
            points.add(seg[0])    # segment start point
            points.add(seg[-1])   # segment end point

    pts = list(points)
    colors = [NODE_COLOR] * len(pts)
    radii = [NODE_RADIUS] * len(pts)
    return pts, colors, radii


def frame_index(filename: str) -> int:
    """Extract the trailing frame index from a filename like 'drawing_42.svg'."""
    stem = os.path.splitext(filename)[0]
    return int(stem.rsplit("_", 1)[-1])


# Animation pipeline
class AnimationPipeline:
    """Complete pipeline: SVG → per-stroke SVG frames → PNG → GIF.

    Parameters
    ----------
    svg_path : str
        Path to the input SVG file.
    width : int
        Output PNG / GIF width in pixels (default 512).
    height : int
        Output PNG / GIF height in pixels (default 512).
    viewbox : str
        SVG viewBox string (default "0 0 500 500").
    fps : int
        Output GIF frame rate (default 24).
    hold_seconds : float
        How long the final completed drawing stays on screen in seconds (default 1.0).
    blend_steps : int
        Number of blend frames between consecutive strokes (default 10).
    """

    def __init__(
        self,
        svg_path: str,
        width: int = 512,
        height: int = 512,
        viewbox: str = "0 0 200 200",
        fps: int = 24,
        hold_seconds: float = 1.0,
        blend_steps: int = 10,
    ):
        self.svg_path = svg_path
        self.width = width
        self.height = height
        self.viewbox = viewbox
        self.fps = fps
        self.hold_frames = max(1, int(fps * hold_seconds))
        self.blend_steps = blend_steps

        # Derive output paths
        self.base_name = os.path.splitext(os.path.basename(svg_path))[0]
        parent = os.path.dirname(svg_path) or "."
        self.output_dir = os.path.join(parent, f"{self.base_name}_frames")
        self.svg_dir = os.path.join(self.output_dir, "svg")
        self.png_dir = os.path.join(self.output_dir, "png")
        self.gif_path = os.path.join(self.output_dir, f"{self.base_name}.gif")


    # Directory scaffolding
    def setup_dirs(self):
        """Create the output directory hierarchy."""
        ensure_dir(self.svg_dir)
        ensure_dir(self.png_dir)


    # SVG parsing & segment classification
    def _load_segments(self) -> list:
        """Parse the input SVG and return a flat list of all segments."""
        paths, _ = svg2paths(self.svg_path)
        segments = []
        for path in paths:
            for seg in path:
                segments.append(seg)
        return segments

    def _split_by_type(self, segments: list):
        """Split segments by type into line and curve groups.

        Each segment becomes its own single-segment Path so it can carry
        an independent color. Arcs are treated as curves.

        Returns:
            (line_paths, curve_paths, line_attrs, curve_attrs)
        """
        line_paths, curve_paths = [], []
        line_attrs, curve_attrs = [], []

        for seg in segments:
            if is_straight_line(seg):
                line_paths.append(Path(seg))
                line_attrs.append(dict(LINE_STYLE))
            elif is_bezier_curve(seg):
                curve_paths.append(Path(seg))
                curve_attrs.append(dict(CURVE_STYLE))

        return line_paths, curve_paths, line_attrs, curve_attrs


    # SVG frame generation
    def generate_svg_frames(self):
        """Generate per-stroke SVG frames, each adding one more segment.

        Intermediate frames: type-based coloring + black node markers.
        Final frame: complete drawing, solid black lines, no nodes.
        """
        segments = self._load_segments()
        total = len(segments)

        pbar = tqdm(range(total), desc="Generating SVG frames", unit="frame")
        for i in pbar:
            visible_segs = segments[: i + 1]
            line_paths, curve_paths, line_attrs, curve_attrs = self._split_by_type(visible_segs)

            all_paths = line_paths + curve_paths
            all_attrs = line_attrs + curve_attrs

            if all_paths:
                nodes, node_colors, node_radii = extract_nodes(all_paths)
            else:
                nodes, node_colors, node_radii = [], [], []

            filename = f"{self.base_name}_{i}.svg"
            filepath = os.path.join(self.svg_dir, filename)

            wsvg(
                paths=all_paths,
                attributes=all_attrs,
                viewbox=self.viewbox,
                nodes=nodes,
                node_colors=node_colors,
                node_radii=node_radii,
                filename=filepath,
            )

        # ---- Final frame: complete drawing, black, no nodes ----
        filename = f"{self.base_name}_{total}.svg"
        filepath = os.path.join(self.svg_dir, filename)

        all_paths, _ = svg2paths(self.svg_path)
        final_attrs = [dict(FINAL_STYLE) for _ in all_paths]

        wsvg(
            paths=all_paths,
            attributes=final_attrs,
            viewbox=self.viewbox,
            filename=filepath,
        )


    # SVG → PNG rendering
    def render_png_frames(self):
        """Render all SVG frames to PNG via Cairo."""
        svg_files = sorted(os.listdir(self.svg_dir), key=frame_index)

        pbar = tqdm(svg_files, desc="Rendering PNG frames", unit="frame")
        for svg_file in pbar:
            svg_path = os.path.join(self.svg_dir, svg_file)
            png_name = os.path.splitext(svg_file)[0] + ".png"
            png_path = os.path.join(self.png_dir, png_name)

            cairosvg.svg2png(
                url=svg_path,
                write_to=png_path,
                output_width=self.width,
                output_height=self.height,
                background_color="white",
                scale=2,
            )


    # Frame interpolation
    @staticmethod
    def _blend(img_a: np.ndarray, img_b: np.ndarray, steps: int) -> list:
        """Linear cross-fade between two frames, returning ``steps`` intermediate images."""
        a = img_a.astype(float)
        b = img_b.astype(float)
        blended = []
        for k in range(steps):
            alpha = k / steps
            blended.append(((1 - alpha) * a + alpha * b).astype(np.uint8))
        return blended


    # GIF assembly
    def compose_gif(self):
        """Load PNG frames, interpolate smooth transitions, and write the final GIF."""
        png_files = sorted(os.listdir(self.png_dir), key=frame_index)

        frames = []
        for png_file in png_files:
            img = Image.open(os.path.join(self.png_dir, png_file))
            frames.append(np.array(img))

        # Insert blend frames between consecutive original frames
        smooth = []
        for i in range(len(frames) - 1):
            smooth.append(frames[i])
            smooth.extend(self._blend(frames[i], frames[i + 1], self.blend_steps))

        # Hold the final frame
        smooth.append(frames[-1])
        smooth.extend([frames[-1]] * (self.hold_frames - 1))

        print(f"Total frames after interpolation: {len(smooth)}")
        print(f"Final hold: {self.hold_frames} frames ≈ {self.hold_frames / self.fps:.1f}s")

        clip = ImageSequenceClip(smooth, fps=self.fps)
        clip.write_gif(self.gif_path)
        print(f"GIF saved to: {self.gif_path}")


    # Public entry point
    def run(self):
        """Execute the full pipeline: dirs → SVG frames → PNG → GIF."""
        print(f"Processing: {self.svg_path}")
        self.setup_dirs()
        self.generate_svg_frames()
        self.render_png_frames()
        self.compose_gif()
        print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert an SVG line drawing into a stroke-by-stroke animated GIF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python animation.py drawing.svg
    python animation.py drawing.svg --width 1024 --height 1024
    python animation.py drawing.svg --fps 30 --hold 2.0
        """,
    )

    parser.add_argument(
        "input",
        metavar="SVG_FILE",
        help="Path to the input SVG file.",
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=512,
        help="Output GIF width in pixels (default: 512).",
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=512,
        help="Output GIF height in pixels (default: 512).",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=24,
        help="Output GIF frame rate (default: 24).",
    )
    parser.add_argument(
        "--hold",
        type=float,
        default=1.0,
        help="Seconds to hold the final completed drawing (default: 1.0).",
    )
    parser.add_argument(
        "--blend",
        type=int,
        default=10,
        help="Number of blend frames between consecutive strokes (default: 10).",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: file not found — {args.input}", file=sys.stderr)
        sys.exit(1)

    pipeline = AnimationPipeline(
        svg_path=args.input,
        width=args.width,
        height=args.height,
        fps=args.fps,
        hold_seconds=args.hold,
        blend_steps=args.blend,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
