from BlackList import BlackList
import matplotlib.pyplot as plt

def main():
    bl = BlackList("blacklistdb")

    
    while True:
        fs = bl.getBlackListedFacesInView()
    
        if len(fs) != 0:
            print("Black Listed Face Found")
        else:
            print("Black Listed Face Not Found")
        
        
    
main()
