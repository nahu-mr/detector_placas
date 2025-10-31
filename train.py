# train.py
from ultralytics import YOLO

# Carga un modelo base pequeño (nano)
model = YOLO("yolov8n.pt")

# Entrena con tu dataset
model.train(
    data="data.yaml",
    epochs=100,
    imgsz=640,
    batch=8,
    name="placas_peru_yolov8n",
    patience=15,
    device='cpu'  # si tu laptop no tiene GPU
)
