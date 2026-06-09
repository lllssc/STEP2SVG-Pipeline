import argparse
import os
import copy
from collections import defaultdict

import networkx as nx
from svgpathtools import svg2paths, wsvg, Line, CubicBezier, Path


def _calc_distance(a, b):
    """Compute squared Euclidean distance between two complex-coordinate points."""
    return (b.real - a.real) ** 2 + (b.imag - a.imag) ** 2


def _reverse_segment(segment):
    """Reverse segment direction (start <-> end). Supports Line and CubicBezier."""
    if isinstance(segment, Line):
        return Line(segment.end, segment.start)
    elif isinstance(segment, CubicBezier):
        p0, p1, p2, p3 = segment.start, segment.control1, segment.control2, segment.end
        return CubicBezier(p3, p3 + (p2 - p3), p0 + (p1 - p0), p0)


def _build_edge_index(paths):
    """
    Extract all unique undirected edges from SVG paths.

    Returns:
        edges: {(start_node_idx, end_node_idx): segment_object}
    """
    nodes = defaultdict(str)
    edges = defaultdict(int)
    index = 0

    for path in paths:
        for segment in path:
            edges_keys = list(edges.keys())

            start = (segment.start.real, segment.start.imag)
            end = (segment.end.real, segment.end.imag)

            if nodes[start] == '':
                nodes[start] = index
                index += 1
            if nodes[end] == '':
                nodes[end] = index
                index += 1

            line = (nodes[start], nodes[end])
            line_reversed = (nodes[end], nodes[start])

            # Deduplicate undirected edges
            if line not in edges_keys and line_reversed not in edges_keys:
                edges[line] = segment

    return edges


def _build_graph(edges):
    """Build an undirected graph from the edge set using NetworkX."""
    G = nx.Graph()
    for edge in edges.keys():
        G.add_edge(edge[0], edge[1], line=edge)
    print(G)
    return G


def _classify_edges_by_cycles(edges, cycles):
    """
    Classify edges by cycle membership.

    Returns:
        loop_paths:      [{edge_pair: segment}, ...]  one dict per cycle
        remaining_edges:  {edge_pair: segment}         edges not in any cycle
    """
    edges_keys = list(edges.keys())
    loop_paths = []
    remaining_edges = copy.deepcopy(edges)

    for cycle in cycles:
        temp_loop = defaultdict(int)
        cycle_len = len(cycle)

        for i in range(cycle_len):
            start_end = ()

            if i == cycle_len - 1:
                # Closing edge: last node back to first node
                test_1 = (cycle[i], cycle[0])
                test_2 = (cycle[0], cycle[i])
            else:
                test_1 = (cycle[i], cycle[i + 1])
                test_2 = (cycle[i + 1], cycle[i])

            # Check both directions (original edge may be reversed vs. cycle order)
            if test_1 in edges_keys:
                start_end = test_1
            elif test_2 in edges_keys:
                start_end = test_2
            else:
                continue

            temp_loop[start_end] = edges[start_end]
            if start_end in edges_keys:
                edges_keys.pop(edges_keys.index(start_end))
                remaining_edges.pop(start_end)

        loop_paths.append(temp_loop)

    # Print statistics
    seen = []
    for lp in loop_paths:
        for pair in lp:
            if pair not in seen:
                seen.append(pair)
    print('loops number:', len(loop_paths))
    print('loops edges number:', len(seen))
    print('remaining edges number:', len(remaining_edges))

    return loop_paths, remaining_edges


def _find_loops(edges):
    """Detect all closed cycles from the edge set. Returns (loop_paths, remaining_edges)."""
    G = _build_graph(edges)
    cycles = nx.cycle_basis(G)
    return _classify_edges_by_cycles(edges, cycles)


# ============================================================================
# Intra-Loop Ordering
# ============================================================================

def _sort_single_loop(loop_path):
    """
    Greedily order segments within a single loop into a continuous chain.

    Algorithm:
        1. Pick the segment closest to the origin as the starting segment.
        2. Repeatedly pick the segment whose endpoint is nearest to the tail.
        3. If the nearest match is via the candidate's end (not start), reverse it.
    """
    sorted_loop = defaultdict(int)
    temp_path = copy.deepcopy(loop_path)

    # Pick the segment closest to the origin as the starting segment
    start_index = ()
    min_modulus = 10000
    for pair in loop_path:
        if abs(loop_path[pair].start) < min_modulus:
            start_index = pair
            min_modulus = abs(loop_path[pair].start)

    # Greedy chaining
    sorted_loop[start_index] = temp_path.pop(start_index)
    while temp_path:
        sorted_keys = list(sorted_loop.keys())
        tail_point = sorted_loop[sorted_keys[-1]].end

        min_d = float('inf')
        min_d_pair = ()
        use_forward = True

        for pair in temp_path:
            d1 = _calc_distance(temp_path[pair].start, tail_point)
            d2 = _calc_distance(temp_path[pair].end, tail_point)
            if d1 < min_d:
                min_d = d1
                min_d_pair = (pair[0], pair[1])
                use_forward = True
            if d2 < min_d:
                min_d = d2
                min_d_pair = (pair[0], pair[1])
                use_forward = False

        if use_forward:
            sorted_loop[min_d_pair] = temp_path.pop(min_d_pair)
        else:
            reversed_pair = (min_d_pair[1], min_d_pair[0])
            reversed_seg = _reverse_segment(temp_path.pop(min_d_pair))
            sorted_loop[reversed_pair] = reversed_seg

    return sorted_loop


def _sort_all_loops(loop_paths):
    """
    Sort all loops:
        1. Within each loop, chain segments greedily into a continuous path.
        2. Across loops, order by the distance from the first segment's start to the origin.
    """
    sorted_list = [_sort_single_loop(lp) for lp in loop_paths]
    sorted_list.sort(key=lambda x: abs(next(iter(x.values())).start))
    return sorted_list


def _assemble_paths(sorted_loops, remaining_edges):
    """
    Build svgpathtools Path objects from sorted loop segments and remaining edges.

    Returns:
        [Path, ...]  — one Path per loop, plus one Path for remaining edges (if any)
    """
    reordered_paths = []
    added_pairs = []

    for sl in sorted_loops:
        segments = []
        for pair in sl:
            if pair in added_pairs:
                continue
            segments.append(sl[pair])
            added_pairs.append(pair)
        reordered_paths.append(Path(*segments))

    if remaining_edges:
        remaining_segments = [remaining_edges[pair] for pair in remaining_edges]
        reordered_paths.append(Path(*remaining_segments))

    return reordered_paths


def _merge_attributes(path_attributes, num_paths):
    """
    Build an output attribute list from the original path attributes.

    Strategy: slice if there are enough; pad with the first entry otherwise.
    Falls back to a default if no original attributes exist.
    """
    default_attr = {
        "stroke": "#000000",
        "stroke-width": "1",
        "stroke-opacity": "1",
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        "fill": "none"
    }

    if not path_attributes:
        return [default_attr] * num_paths

    if len(path_attributes) >= num_paths:
        return path_attributes[:num_paths]

    # Pad with the first entry
    template = path_attributes[0] if path_attributes else default_attr
    return path_attributes + [template] * (num_paths - len(path_attributes))


def _make_output_path(input_path):
    """Generate default output path by inserting _reordered before the extension."""
    dir_name = os.path.dirname(input_path)
    base_name = os.path.basename(input_path)
    stem, ext = os.path.splitext(base_name)
    if not ext:
        ext = '.svg'
    output_name = f"{stem}_reordered{ext}"
    return os.path.join(dir_name, output_name) if dir_name else output_name


# Main Processing Pipeline
def reorder_svg(input_path):
    """
    Read an SVG file and reorder its path segments.

    Returns:
        reordered_paths:  list of reordered Path objects
        svg_attributes:   original SVG-level attributes (viewBox, width, height, etc.)
        path_attributes:  original path-level attributes (stroke, fill, etc.)
    """
    paths, path_attributes = svg2paths(input_path)

    edges = _build_edge_index(paths)
    loops, remaining_edges = _find_loops(edges)
    sorted_loops = _sort_all_loops(loops)
    reordered_paths = _assemble_paths(sorted_loops, remaining_edges)

    return reordered_paths, path_attributes


def export_svg(reordered_paths, path_attributes, output_path):
    """Export reordered paths to an SVG file, preserving original attributes."""
    attrs = _merge_attributes(path_attributes, len(reordered_paths))
    wsvg(
        paths=reordered_paths,
        attributes=attrs,
        viewbox="0 0 200 200",
        filename=output_path,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Reorder SVG path segments into continuous stroke paths."
    )
    parser.add_argument(
        'input',
        help='Path to input SVG file',
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Path to output SVG file (default: appends _reordered suffix to input name)',
    )
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.isfile(input_path):
        parser.error(f"Input file not found: {input_path}")

    output_path = args.output or _make_output_path(input_path)
    output_path = os.path.abspath(output_path)

    reordered_paths, path_attrs = reorder_svg(input_path)
    export_svg(reordered_paths, path_attrs, output_path)


if __name__ == '__main__':
    main()
