import numpy as np
from scipy.spatial import distance as dist

def get_centroid(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)

def update_tracks(objects, detections, max_distance=50):
    if len(objects) == 0:
        return {i: {'centroid': get_centroid(obj['box']), 'box': obj['box'], 'class': obj['class'], 'conf': obj['conf']}
                for i, obj in enumerate(detections)}, len(detections)
    
    object_centroids = np.array([obj['centroid'] for obj in objects.values()])
    detection_centroids = np.array([get_centroid(obj['box']) for obj in detections])
    
    if len(detection_centroids) == 0:
        return {}, len(objects)
    
    distances = dist.cdist(object_centroids, detection_centroids)
    rows = distances.min(axis=1).argsort()
    cols = distances.argmin(axis=1)[rows]
    
    used_rows, used_cols = set(), set()
    new_objects = {}
    next_id = max(objects.keys(), default=-1) + 1
    
    for row, col in zip(rows, cols):
        if row in used_rows or col in used_cols or distances[row, col] > max_distance:
            continue
        obj_id = list(objects.keys())[row]
        new_objects[obj_id] = {
            'centroid': detection_centroids[col],
            'box': detections[col]['box'],
            'class': detections[col]['class'],
            'conf': detections[col]['conf']
        }
        used_rows.add(row)
        used_cols.add(col)
    
    for col in range(len(detections)):
        if col not in used_cols:
            new_objects[next_id] = {
                'centroid': detection_centroids[col],
                'box': detections[col]['box'],
                'class': detections[col]['class'],
                'conf': detections[col]['conf']
            }
            next_id += 1
    
    return new_objects, next_id