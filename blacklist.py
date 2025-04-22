# blacklist.py
import pickle
import os
import face_recognition
import numpy as np
import cv2
from typing import Dict, Optional, Tuple
from datetime import datetime

class BlacklistDatabase:
    def __init__(self, pickle_path: str = "blacklist.pickle"):
        self.pickle_path = pickle_path
        self.blacklist = self._load_database()
        self._preloaded = None

    def _load_database(self) -> Dict[str, Dict]:
        if os.path.exists(self.pickle_path):
            try:
                with open(self.pickle_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading DB: {e}")
                return {}
        return {}

    def _save_database(self):
        with open(self.pickle_path, 'wb') as f:
            pickle.dump(self.blacklist, f)

    def add_face(self, face_id: str, encoding: np.ndarray, metadata: Dict = None) -> bool:
        if metadata is None:
            metadata = {}
        metadata['added_on'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.blacklist[face_id] = {'encoding': encoding, 'metadata': metadata}
        self._preloaded = None
        self._save_database()
        return True

    def remove_face(self, face_id: str) -> bool:
        if face_id in self.blacklist:
            del self.blacklist[face_id]
            self._preloaded = None
            self._save_database()
            return True
        return False

    def preload_encodings(self):
        if self._preloaded is None:
            self._preloaded = {
                'encs': [e['encoding'] for e in self.blacklist.values()],
                'ids': list(self.blacklist.keys())
            }
        return self._preloaded

    def check_face(self, face_encoding: np.ndarray, tolerance: float = 0.5) -> Tuple[bool, Optional[str], Optional[Dict]]:
        if not self.blacklist:
            return False, None, None

        data = self.preload_encodings()
        known = data['encs']
        ids   = data['ids']
        if not known:
            return False, None, None

        # 向量化匹配 & 打印最小距离
        arr = np.stack(known)                 # (N,128)
        dists = np.linalg.norm(arr - face_encoding, axis=1)
        min_dist = float(np.min(dists))
        print(f"[DEBUG] min face distance = {min_dist:.3f}")
        idx = int(np.argmin(dists))
        if min_dist <= tolerance:
            fid = ids[idx]
            return True, fid, self.blacklist[fid]['metadata']

        return False, None, None

    def get_all_faces(self) -> Dict[str, Dict]:
        return self.blacklist


def convert_opencv_face_to_face_recognition(face, frame_height):
    left = face.x
    top = face.y
    right = face.x + face.w
    bottom = face.y + face.h
    return (top, right, bottom, left)


def check_face_against_blacklist(db: BlacklistDatabase,
                                 frame: np.ndarray,
                                 face,
                                 tolerance: float = 0.5):
    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        top, right, bottom, left = convert_opencv_face_to_face_recognition(face, frame.shape[0])
        encs = face_recognition.face_encodings(rgb, [(top, right, bottom, left)])
        if not encs:
            return False, None, None
        return db.check_face(encs[0], tolerance)
    except Exception as e:
        print(f"Check error: {e}")
        return False, None, None
