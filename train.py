from ultralytics import YOLO

if __name__ == '__main__':
    model = YOLO("yolo26s.pt") 

    results = model.train(
        data="campus-swap-dataset/data.yaml",
        epochs=100,
        patience=15,
        imgsz=640,
        batch=-1,
        device=0,
        workers=4,
        amp=True
    )