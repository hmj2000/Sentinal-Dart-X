import math
from Constants import Constants

class Face:
    def __init__(self, faceId, x, y, w, h): 
        self.faceId = faceId
        self.x, self.y, self.w, self.h = x,y,h,w
        self.framesSinceLastSeen = 0

class RawFace:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x,y,w,h       

class FaceBuffer:
    def __init__(self):
        self.nextFaceId = 0
        self.faceList = []
    
    def isNotOldFace(self, face):
        if face.framesSinceLastSeen >= Constants.deleteAtGoneFrame:
            return False
        return True    

    def incrementSinceLastSeen(self):
        faceCount = len(self.faceList)
        
        for i in range(faceCount):
            self.faceList[i].framesSinceLastSeen += 1

    def processIfFaceExists(self, rawFace):
        faceCount = len(self.faceList)

        for i in range(faceCount):
            currentFace = self.faceList[i]
            if currentFace.framesSinceLastSeen == 0:
                continue
            
            if math.dist([currentFace.x, currentFace.y], [rawFace.x, rawFace.y]) <= Constants.maxPixelDistanceSimilarity:
                self.faceList[i].framesSinceLastSeen = 0
                self.faceList[i].x = rawFace.x
                self.faceList[i].y = rawFace.y
                self.faceList[i].w = rawFace.w
                self.faceList[i].h = rawFace.h
                
                return True
                

        return False

    def addNewFace(self, rawFace):
        self.faceList.append(Face(self.nextFaceId, rawFace.x, rawFace.y, rawFace.w, rawFace.h))
        self.nextFaceId += 1

    def cullOldFaces(self):
        self.faceList = list(filter(self.isNotOldFace, self.faceList))

    #Only use this
    def processNewFrame(self, rawFaceList):
        self.incrementSinceLastSeen()
        
        for rawFace in rawFaceList:
            if not self.processIfFaceExists(rawFace):
                self.addNewFace(rawFace)
    
        self.cullOldFaces()

    #or this
    def getFaces(self):
        return self.faceList
    
    #or this 
    def getOldestTrackedFace(self):
        if len(self.faceList) == 0:
            return None
        
        lowestIdIndex = 0
        
        for i, face in enumerate(self.faceList):
            if face.faceId < self.faceList[lowestIdIndex].faceId:
                lowestIdIndex = i
        
        return self.faceList[lowestIdIndex]
                
