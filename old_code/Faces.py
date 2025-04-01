class Faces:
    def __init__(self, croppedFaceImageData, x,y,w,h, screenSize):
        self._image = croppedFaceImageData
        self._rectangle = (x,y,w,h)
        self._screenSize = screenSize

    def getFace(self):
        return self._image
    
    def getRectangle(self):
        return self._rectangle
    
    def getScreenSize(self):
        return self._screenSize
