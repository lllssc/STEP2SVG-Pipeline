# STEP2SVG
This repository contains the automation scripts for exporting and preprocessing SVG drawings from CAD models. This work is part of our project: [Drawing2CAD: Sequence-to-Sequence Learning for CAD Generation from Vector Drawings](https://github.com/lllssc/Drawing2CAD), ACM MM 2025.

## Export SVG Drawings
Follow these steps to set up the automation pipeline:

1. **Install FreeCAD** Download and install the latest version of [FreeCAD](https://www.freecad.org/).

2. **Set up the Macro** - Open FreeCAD.
   - Go to the navigation bar and select **Macro > Macros...**.
   - You can either create a new macro and paste the code, or copy the `step2svg.FCMacro` from this project into your FreeCAD Macro folder.

3. **Configuration & Execution** Open the script and update the following paths to match your local environment:
   - `step_file`: Path to your source CAD models.
   - `drawing_folder`: Destination folder for the exported SVGs.
   - `template`: Path to your SVG drawing template.
   
   Once configured, click **Execute macro** within the Macro editor.

💡 **Notes**

- **Dynamic Delays:** The `time.sleep(0.5)` commands are used to allow sufficient time for template and drawing loading. Please adjust these durations based on your computer's performance and the complexity of your CAD models.

- **UI Refreshing:** Frequent use of `doc.recompute()` and `Gui.updateGui()` ensures the interface refreshes constantly, which is critical for the drawings to render and export correctly.

- **Batch Processing:** While it is entirely possible to wrap this logic into a Python loop for batch processing, **FreeCAD must remain open and visible** throughout the entire process to ensure the GUI-dependent rendering functions correctly.

## Preprocess SVG Drawings

This section of the code was refactored and reorganized with AI assistance based on the original implementation to improve readability and ease of use.

### Dependencies

```bash
pip install -r requirements.txt
```

### Workflow Overview

The preprocessing follows a two-stage pipeline: **normalize → reorder**. Always run `normalize.py` first, then feed its output into `reorder.py`.

### 1. Normalize (`normalize.py`)

We scale the SVG engineering drawings exported from FreeCAD into a 200×200 viewBox while preserving the original line styles.

```bash
python normalize.py input.svg                           # output → input_normalized.svg
python normalize.py input.svg -o output.svg             # custom output path
python normalize.py input.svg -w 0.5 -c "#FF0000"       # custom stroke width & color
```

### 2. Reorder (`reorder.py`)

To standardize path ordering, we used the canvas top-left corner as origin and applied graph theory algorithms to identify all contours. These contours were then arranged by increasing distance from origin, with each contour drawn clockwise.

```bash
python reorder.py input_normalized.svg                  # output → input_normalized_reordered.svg
python reorder.py input_normalized.svg -o output.svg    # custom output path
```

> ⚠️ **Important:** Always reorder a **normalized** SVG. The greedy-chaining step uses distance-to-origin heuristics that assume a well-scaled coordinate space.

### 3. Visualize (`animation.py`)

We also provide pre-rendered animations to illustrate the difference before and after reordering:

**Before reordering**:

![Normalized animation](preprocess/test_normalized_frames/test_normalized.gif)

**After reordering**:

![Reordered animation](preprocess/test_normalized_reordered_frames/test_normalized_reordered.gif)

You can also use our pipeline to visualize the path ordering of your own SVG engineering drawings (containing only line and Bézier curve commands), which will generate an individual SVG and PNG file for each stroke, and export an animated GIF illustrating the drawing process. 

```bash
python animation.py input_normalized.svg
```

## Cite

Please consider citing our work if you find it useful:

```
@article{qin2025drawing2cad,
  title={Drawing2CAD: Sequence-to-Sequence Learning for CAD Generation from Vectorized Drawings},
  author={Qin, Feiwei and Lu, Shichao and Hou, Junhao and Wang, Changmiao and Fang, Meie and Liu, Ligang},
  journal={arXiv preprint arXiv:2508.18733},
  year={2025}
}

@inproceedings{qin2025drawing2cad,
  author = {Qin, Feiwei and Lu, Shichao and Hou, Junhao and Wang, Changmiao and Fang, Meie and Liu, Ligang},
  title = {Drawing2CAD: Sequence-to-Sequence Learning for CAD Generation from Vector Drawings},
  year = {2025},
  doi = {10.1145/3746027.3755782},
  booktitle = {Proceedings of the 33rd ACM International Conference on Multimedia},
  pages = {10573–10582},
}
```