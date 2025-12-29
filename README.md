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
coming soon.

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