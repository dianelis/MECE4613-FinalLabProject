
import os
import cv2
from file_watcher import FileWatcher


# Define hyper parameters
IMG_PATH = os.environ['XDG_RUNTIME_DIR'] + '/robot_stream.jpg'
ESC_KEY = 27


# Watch the IMG_PATH file, if changed, read and show it
def main():
    watcher = FileWatcher(IMG_PATH)
    while cv2.waitKey(1) not in [ord('q'), ESC_KEY]:
        if watcher.has_changed():
            img = cv2.imread(IMG_PATH)
            cv2.imshow('preview', img)


if __name__ == "__main__":
    main()
