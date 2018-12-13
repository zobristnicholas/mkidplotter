import os
import pymeasure.display.Qt as Qt


def get_image_path(image_name):
    """Return the absolute path of the image_name"""
    # all images are currently in this directory
    current_path = os.path.abspath(__file__)
    directory = os.path.dirname(current_path)
    image_path = os.path.join(directory, image_name)
    if not os.path.isfile(image_path):
        raise ValueError("{} does not exist in the mkidplotter module"
                         .format(image_name))
    return image_path


def get_image_icon(image_name):
    """Return at QIcon of the image_name"""
    return Qt.QtGui.QIcon(get_image_path(image_name))
