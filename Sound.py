import time
import pygame
import threading
from Constants import Constants

class Sound:
    def soundLoop(self):
        def isExit():
            self.stateLock.acquire()
            ex = self.exit
            self.stateLock.release()
            return ex
            
        def isPlay():
            self.stateLock.acquire()
            play = self.playSound
            self.stateLock.release()
            return play
        
        def setPlay(value):
            self.stateLock.acquire()
            self.playSound = value
            self.stateLock.release()
        
        def playSound():
            self.pygameSound.play()
            time.sleep(self.soundSeconds)
        
        while True:
            if isExit():
                break
            if isPlay():
                playSound()
                setPlay(False)
                
            time.sleep(Constants.playSoundRepeatDelay)
    
    def __init__(self, file=Constants.robotSoundEffectFile):
        pygame.mixer.init()
        self.pygameSound = pygame.mixer.Sound(file)
        self.soundSeconds = self.pygameSound.get_length()
        
        self.playSound = False
        self.exit = False
        self.stateLock = threading.Lock()
        self.thread = threading.Thread(target=self.soundLoop)
        self.thread.start()

    def __del__(self):
        self.stateLock.acquire()
        self.exit = True
        self.playSound = False
        self.stateLock.release()
        self.thread.join()
    
    def play(self):
        self.stateLock.acquire()
        self.playSound = True
        self.stateLock.release()
