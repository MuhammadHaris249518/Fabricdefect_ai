Put YOLO-format .txt labels here for every image in ../images/, same
base filename (e.g. cookie_defect_003.txt for cookie_defect_003.jpg).

Each line: class_id x_center y_center width height (all normalized 0-1).
  0 = hole
  1 = oil_stain
(must match the `names:` list in 6_yolo_sandbox/dataset.yaml)

Unlike the synthetic images, these can't be auto-labeled from a mask -
draw these boxes by hand in a tool like CVAT, LabelImg, or Roboflow and
export as "YOLO" format.
