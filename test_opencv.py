import cv2
import sys

def main():
    # Load the pre-trained Haar Cascade face detection model
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    if face_cascade.empty():
        print("Error: Couldn't load face cascade classifier")
        return
    
    # Open the default webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return

    # Show exit option in console
    print("Instructions:")
    print("- Press 'q' or 'ESC' to exit the program")
    print("- Or close the window to exit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # Draw rectangles around detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        # Display the clean result without any text overlay
        cv2.imshow('Live Face Detection', frame)

        # Handle key press
        key = cv2.waitKey(30) & 0xFF
        if key == ord('q') or key == ord('Q') or key == 27:  # q, Q, or ESC
            print("Exit key detected")
            break
            
        # Check if window was closed
        if cv2.getWindowProperty('Live Face Detection', cv2.WND_PROP_VISIBLE) < 1:
            print("Window closed by user")
            break

    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    
    # Extra cleanup attempt
    for i in range(5):
        cv2.waitKey(1)
    
    print("Program terminated successfully")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()
        sys.exit(1)
