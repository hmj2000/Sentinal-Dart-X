from deepface import DeepFace
from Faces import Faces
from FaceDetector import FaceDetector

class BlackList:
        def __init__(self, databaseFolder):
            self._fd = FaceDetector()
            self._fd.start_camera()
            self._databaseFolder = databaseFolder

        def _isBlackListed(self, numpyImage):
            results = DeepFace.find(img_path=numpyImage, db_path=self._databaseFolder,silent=True, enforce_detection=False, model_name="SFace")
            if results[0].empty:
                return False
            
            return True

        def getBlackListedFacesInView(self):
            result, faces = self._fd.getAllFacesInView()
            blackListedFaces = []
            for face in faces:
                if self._isBlackListed(face.getFace()):
                    blackListedFaces.append(face)
            return blackListedFaces

        def __del__(self):
            self._fd.stop_camera()
