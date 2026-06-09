import argparse
import os
from svgpathtools import Path, Line, CubicBezier, svg2paths, wsvg

# Fixed output viewbox — the target coordinate space for all normalized SVGs.
VIEWBOX = "0 0 200 200"

# Offset that brings coordinates from [-2000, 2000] into [0, 4000].
_OFFSET = complex(2000, 2000)

# Scale factor: viewbox_dim / 4000.
_SCALE = int(VIEWBOX.split()[-1]) / 4000

# Suffix appended to the input filename when no explicit output path is given.
_DEFAULT_SUFFIX = "_normalized"


def svg_normalize(
    input_svg,
    output_svg=None,
    stroke_width=1,
    stroke_color="#000000",
):
    """Normalize an SVG file into the fixed 200×200 viewbox with uniform style.

    Args:
        input_svg: Path to the input SVG file.
        output_svg: Path for the normalized output SVG.  Defaults to the same
            directory as *input_svg* with ``_normalized`` inserted before the
            extension (e.g. ``test.svg`` → ``test_normalized.svg``).
        stroke_width: Stroke width in viewbox units (default: ``1``).
        stroke_color: Stroke colour as a CSS hex string (default: ``"#000000"``).
    """
    if output_svg is None:
        dir_name = os.path.dirname(input_svg)
        base_name = os.path.basename(input_svg)
        name, ext = os.path.splitext(base_name)
        output_svg = os.path.join(dir_name, f"{name}{_DEFAULT_SUFFIX}{ext}")

    paths, _ = svg2paths(input_svg)

    new_paths = []
    for path in paths:
        new_segments = []
        for segment in path:
            if isinstance(segment, Line):
                new_segments.append(
                    Line(
                        start=(segment.start + _OFFSET) * _SCALE,
                        end=(segment.end + _OFFSET) * _SCALE,
                    )
                )
            elif isinstance(segment, CubicBezier):
                new_segments.append(
                    CubicBezier(
                        start=(segment.start + _OFFSET) * _SCALE,
                        control1=(segment.control1 + _OFFSET) * _SCALE,
                        control2=(segment.control2 + _OFFSET) * _SCALE,
                        end=(segment.end + _OFFSET) * _SCALE,
                    )
                )
        new_paths.append(Path(*new_segments))

    # Uniform style: only stroke width and colour are user-configurable;
    # the remaining attributes are sensible defaults for line-art output.
    attributes = [
        {
            "stroke": stroke_color,
            "stroke-width": str(stroke_width),
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
            "fill": "none",
        }
    ] * len(new_paths)

    wsvg(paths=new_paths, attributes=attributes, viewbox=VIEWBOX, filename=output_svg)


def main():
    """CLI entry point — parse arguments and run normalization."""
    parser = argparse.ArgumentParser(
        description="Normalize an SVG file to a fixed 200×200 viewbox with uniform stroke styling."
    )
    parser.add_argument(
        "input",
        help="Path to the input SVG file.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path for the output SVG (default: <input>_normalized.svg in the same directory).",
    )
    parser.add_argument(
        "-w", "--stroke-width",
        type=float,
        default=1,
        help="Stroke width in viewbox units (default: 1).",
    )
    parser.add_argument(
        "-c", "--stroke-color",
        default="#000000",
        help="Stroke colour as a CSS hex string (default: #000000).",
    )
    args = parser.parse_args()

    svg_normalize(
        input_svg=args.input,
        output_svg=args.output,
        stroke_width=args.stroke_width,
        stroke_color=args.stroke_color,
    )


if __name__ == "__main__":
    main()
