# test_mediapipe_blacklist.py
import os
import time
import gc
import cv2
import numpy as np
from blacklist import BlacklistDatabase, check_face_against_blacklist
from face_detector_mediapipe import MPFaceDetector

class SimpleFace:
    def __init__(self, x, y, w, h, fid):
        self.x, self.y, self.w, self.h, self.faceId = x, y, w, h, fid
        self.framesSinceLastSeen = 0

def setup_camera(idx=0):
    cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        raise RuntimeError("Cannot open camera")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  426)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 320)
    cap.set(cv2.CAP_PROP_FPS,          15)
    return cap, 426, 320

def calc_dist(px, focal=400, real_cm=15):
    return (real_cm * focal) / (px * 10)  # meters

def draw_faces(frame, faces, blacklisted, focal=400):
    for fid, f in faces.items():
        d = calc_dist(f.w, focal)
        in4m = d <= 4.0
        if fid in blacklisted:
            col, label, act = (0,0,255), f"MATCH:{blacklisted[fid].get('name','')}", "FIRE"
        elif in4m:
            col, label, act = (0,255,255), f"{d:.1f}m", ""
        else:
            col, label, act = (0,255,0), "", ""
        cv2.rectangle(frame, (f.x, f.y), (f.x+f.w, f.y+f.h), col, 2)
        cv2.putText(frame, f"ID:{fid}", (f.x, f.y-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
        if label:
            cv2.putText(frame, label, (f.x, f.y+f.h+15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
        if act:
            cv2.putText(frame, act, (f.x, f.y+f.h+35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)

def main():
    os.environ['OPENCV_OPENCL_RUNTIME'] = ''
    os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'

    db = BlacklistDatabase()
    total = len(db.get_all_faces())
    print(f"Loaded {total} blacklisted faces.")
    if total == 0 and input("Empty => continue? (y/n): ").lower() != 'y':
        return

    cap, W, H = setup_camera()
    detector = MPFaceDetector(min_confidence=0.6)

    tracked = {}    # fid -> SimpleFace
    cache   = {}    # fid -> [match, blk_id, md, ttl]
    cnt     = {}    # fid -> counter
    stable  = {}    # fid -> md

    next_id = 0
    check_every = 5
    ttl = 30
    stable_th = 2
    un_st_th = -4

    frame_ctr = 0
    start = time.time()
    frames = 0

    print("Press 'q' to quit, 's' to save frame.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frames += 1
        frame_ctr += 1
        now = time.time()
        if now - start > 5:
            print(f"FPS: {frames/(now-start):.1f}")
            frames, start = 0, now

        # MediaPipe 检测
        boxes = detector.detect(frame)

        # 标记未见
        for f in tracked.values():
            f.framesSinceLastSeen += 1

        # 更新 / 新增跟踪
        for (top, right, bottom, left) in boxes:
            x, y, w, h = left, top, right-left, bottom-top
            matched = False
            for fid, f in tracked.items():
                dx = (f.x + f.w/2) - (x + w/2)
                dy = (f.y + f.h/2) - (y + h/2)
                if np.hypot(dx, dy) < (f.w + w)/3:
                    f.x, f.y, f.w, f.h = x, y, w, h
                    f.framesSinceLastSeen = 0
                    matched = True
                    break
            if not matched:
                tracked[next_id] = SimpleFace(x, y, w, h, next_id)
                next_id += 1

        # 清除久未见
        for fid in list(tracked):
            if tracked[fid].framesSinceLastSeen > 15:
                tracked.pop(fid)
                cache.pop(fid, None)
                cnt.pop(fid, None)
                stable.pop(fid, None)

        # 缓存 TTL
        for fid in list(cache):
            cache[fid][3] -= 1
            if cache[fid][3] <= 0:
                cache.pop(fid)

        # 黑名单比对
        if frame_ctr % check_every == 0:
            for fid, face in tracked.items():
                if fid in cache and cache[fid][0]:
                    stable[fid] = cache[fid][2]
                    continue
                d = calc_dist(face.w)
                if d <= 4.0:
                    match, bid, md = check_face_against_blacklist(db, frame, face, tolerance=0.5)
                    cache[fid] = [match, bid, md, ttl]
                    if match:
                        print(f"Blacklist hit @ {d:.1f}m → {bid}")
                        stable[fid] = md

        # 稳定性滤波
        for fid in list(tracked):
            if fid in stable:
                cnt[fid] = cnt.get(fid, 0) + 1
            else:
                cnt[fid] = cnt.get(fid, 0) - 1
                if cnt[fid] <= un_st_th:
                    stable.pop(fid, None)

        # 绘制与显示
        disp = frame.copy()
        draw_faces(disp, tracked, stable)
        cv2.imshow("MP Blacklist Test", disp)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('s'):
            fn = f"frame_{int(now)}.jpg"
            cv2.imwrite(fn, disp)
            print("Saved", fn)

    cap.release()
    detector.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
