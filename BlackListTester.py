from BlackList import BlackList

def main():
    bl = BlackList("blacklistdb")
    while True:
        bfaces = bl.getBlackListedFacesInView()
        if len(bfaces) == 0:
            print("BLACKLIST FACE NOT PRESENT")
        else:
            print("BLACKLIST FACE PRESENT")
main()