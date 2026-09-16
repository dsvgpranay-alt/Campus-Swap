import requests

YOLO_SERVER = ""

def predict(image_path):
    with open(image_path, "rb") as image:
        response = requests.post(
            YOLO_SERVER,
            files={"image": image}
        )

    response.raise_for_status()
    return response.json()