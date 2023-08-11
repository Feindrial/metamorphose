fcounter = 0       
quited = False
paused = False

def process_video_action(key):
    global fcounter, quited, paused
    
    if key == ord('q'):
        quited = True
    elif key == ord('p'):
        paused = not paused
    elif key == 18: #ctrl+r
        paused = True
        fcounter -= 5
    elif key == 6: #ctrl+f
        paused = True
        fcounter += 5
    elif key == ord('r'):
        paused = True
        fcounter -= 1
    elif key == ord('f'):
        paused = True
        fcounter += 1
        
def at_draw_video():
    global fcounter, quited, paused

    import cv2

    cap = cv2.VideoCapture("C:\\Users\\Oto_Test2\\Desktop\\Metamorphose\\Videos\\1\\08_13_17.avi")

    fcounter = 0
    quited = False
    paused = False
    while cap.isOpened():
        
        if quited:
            break
        elif paused:
            fcounter -= 1
        
        
        ret, frame = cap.read()
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, fcounter)
                
        if not ret:
            break

        cv2.imshow("MetamophoseXXXX", frame)
        
        key = cv2.waitKey(1) & 0xFF
        process_video_action(key)
        print(key)
        
        fcounter += 1
        
    cap.release()
    cv2.destroyAllWindows()
    
at_draw_video()