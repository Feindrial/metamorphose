import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import glob
import os

def create_popup(textt):
    top= tk.Toplevel(window)
    top.title("ERROR")
    root_x = window.winfo_rootx()
    root_y = window.winfo_rooty()    
    win_x = root_x + 300
    win_y = root_y + 100
    top.geometry(f'+{win_x}+{win_y}')
    tk.Label(top, text=textt).pack()


class FolderHist:
    def __init__(self):
        self.bbox_rois_list = []
        self.old_bbox_rois_list = []
        self.crop_trash = []
        self.old_crop_index = -1
        self.crop_index = -1
        self.save_in_wait = False

    def save_changes(self):
        self.save_in_wait = False

        if len(self.crop_trash) != 0:

            if self.old_crop_index != -1:
                self.crop_trash.append(self.old_crop_index)
                
            dcount = sum(1 if ct < self.crop_index else 0 for ct in self.crop_trash)
                
            for index in sorted(self.crop_trash[:-1], reverse=True):
                del self.bbox_rois_list[index]                

            self.crop_trash.clear()
            self.crop_index -= dcount

        self.old_crop_index = self.crop_index
        self.old_bbox_rois_list = self.bbox_rois_list.copy()

    def revert_changes(self):
        self.save_in_wait = False
        if self.crop_index >= len(self.old_bbox_rois_list):
            self.crop_index = self.old_crop_index

        self.bbox_rois_list = self.old_bbox_rois_list.copy()
        self.crop_trash.clear()

    def push_crop(self, points):
        self.save_in_wait = True

        self.crop_trash.append(len(self.bbox_rois_list))

        self.crop_index = len(self.bbox_rois_list)
        self.bbox_rois_list.append(points)

        if self.crop_index != -1:
            return True
        else:
            return False

    def push(self, points):
        self.save_in_wait = True
        self.bbox_rois_list.append(points)


class FolderDesc:
    def __init__(self, path):
        self.pure_handle = None
        self.handle = None
        self.open_handle = None
        self.crop_handle = None
        self.fhist = FolderHist()

        cap = cv2.VideoCapture(path)
        fframe = None
        while(cap.isOpened()):
      
            ret, frame = cap.read()
            fframe = frame
            break

        cap.release()

        self.pure_handle = fframe
        self.handle = self.pure_handle.copy()
        self.open_handle = self.pure_handle.copy()
        self.crop_handle = self.pure_handle.copy()

    def preview(self):
        if self.fhist.save_in_wait:
            self.revert_changes()

        prev = self.pure_handle.copy()

        i = 0
        for p1, p2 in self.fhist.bbox_rois_list:
            if i == self.fhist.crop_index:
                cv2.rectangle(prev, p1, p2, color=(0, 0, 255), thickness=1)
            else:
                cv2.rectangle(prev, p1, p2, color=(0, 255, 0), thickness=-1)

            i += 1

        cv2.imshow("META", prev)

    def save_config(self):
        self.fhist.save_changes()

        self.handle = self.open_handle.copy()

    def draw_rectangle(self, point1, point2, color=(0, 255, 0), fill=False, crop=False):
        if crop:
            revert_needed = self.fhist.push_crop((point1, point2))

            if revert_needed:
                self.revert_crop()
        else:
            self.fhist.push((point1, point2))

        if fill:
            fill = -1
        else:
            fill = 1

        cv2.rectangle(self.open_handle, point1, point2, color, thickness=fill)
        if not crop:
            cv2.rectangle(self.crop_handle, point1,
                          point2, color, thickness=fill)
        # cv2.imshow("CROP", self.crop_handle)

    def revert_crop(self):
        self.open_handle = self.crop_handle.copy()

    def revert_changes(self):
        self.fhist.revert_changes()

        self.open_handle = self.handle.copy()
        self.crop_handle = self.pure_handle.copy()

        i = 0
        for p1, p2 in self.fhist.bbox_rois_list:
            if i == self.fhist.crop_index:
                i += 1
                continue

            cv2.rectangle(self.crop_handle, p1, p2,
                          color=(0, 255, 0), thickness=-1)

            i += 1

    def draw(self):
        cv2.imshow("Metamorphose", self.open_handle)


path_dict = {}
spath = ""
wfolder = ""
wfile = ""
rect_bbox = None
rect_endpoint_tmp = None
handle_cpy = None
drawing = False
fcounter = 0       
quited = False        
paused = False

def write_green(img, iterable, icrop):
    will_delete = []
    for index, (xy1, xy2) in enumerate(iterable):
        if index == icrop:
            continue
        else:
            cv2.rectangle(img, xy1, xy2, color=(0, 255, 0), thickness=-1)
            will_delete.append(index)
        
    for index in sorted(will_delete, reverse=True):
        del iterable[index]

def green_file_not_exist(path, iterable, icrop):
    cap = cv2.VideoCapture(path)
    
    fframe = None
    frame_number = 0
    while(cap.isOpened()):
        ret, frame = cap.read()
        fframe = frame
                            
        write_green(fframe, iterable, icrop)
            
        frame_number += 1                            
            
    cv2.imwrite(path + ".jpeg", fframe)
            
    cap.release()   
    
def green_file_exist(path, iterable, icrop):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    
    write_green(img, iterable, icrop)
    
    cv2.imwrite(path, img)
    
def crop_the_image(path, points):
    xy1, xy2 = points
    
    x_min = min(xy1[0], xy2[0])
    x_max = max(xy1[0], xy2[0])
    y_min = min(xy1[1], xy2[1])
    y_max = max(xy1[1], xy2[1])
    
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    img = img[y_min:y_max, x_min:x_max]
    cv2.imwrite(path, img)
    
# True if bbox1 inside bbox2
def bbox_check_impl(bbox1, bbox2):
    p_xmin = min(bbox1[0][0], bbox1[1][0])
    p_xmax = max(bbox1[0][0], bbox1[1][0])
    p_ymin = min(bbox1[0][1], bbox1[1][1])
    p_ymax = max(bbox1[0][1], bbox1[1][1])
    
    h_xmin = min(bbox2[0][0], bbox2[1][0])
    h_xmax = max(bbox2[0][0], bbox2[1][0])
    h_ymin = min(bbox2[0][1], bbox2[1][1])
    h_ymax = max(bbox2[0][1], bbox2[1][1])
    
    p_corners = [
        (p_xmin, p_ymin),
        (p_xmin, p_ymax),
        (p_xmax, p_ymin),
        (p_xmax, p_ymax)
    ]
    
    b1 = {
        'x': h_xmin,
        'y': h_ymin,
        'height': h_xmax - h_xmin,
        'width': h_ymax - h_ymin
    }
    b2 = {
        'x': p_xmin,
        'y': p_ymin,
        'height': p_xmax - p_xmin,
        'width': p_ymax - p_ymin
    }

    if b1['x'] < b2['x'] and b1['y'] < b2['y']:
        if b2['x'] + b2['width'] < b1['x'] + b1['width'] and b2['y'] + b2['height'] < b1['y'] + b1['height']:
            return True
    
    return False

def bbox_check(bbox1, bbox2):
    bbox_left_inside = bbox_check_impl(bbox1, bbox2)
    bbox_right_inside = bbox_check_impl(bbox2, bbox1)
    
    if bbox_left_inside:
        return (True, -1)
    if bbox_right_inside:
        return (True, 1)
    
    p_xmin = min(bbox1[0][0], bbox1[1][0])
    p_xmax = max(bbox1[0][0], bbox1[1][0])
    p_ymin = min(bbox1[0][1], bbox1[1][1])
    p_ymax = max(bbox1[0][1], bbox1[1][1])
    
    h_xmin = min(bbox2[0][0], bbox2[1][0])
    h_xmax = max(bbox2[0][0], bbox2[1][0])
    h_ymin = min(bbox2[0][1], bbox2[1][1])
    h_ymax = max(bbox2[0][1], bbox2[1][1])
    
    x_min = min(p_xmin, h_xmin)
    x_max = max(p_xmax, h_xmax)
    y_min = min(p_ymin, h_ymin)
    y_max = max(p_ymax, h_ymax)
    
    return (False, ((x_min, y_min), (x_max, y_max)))

def export():
    global spath, path_dict
    
    output_dir_name = "class"
    output_trname = "Train"
    output_tename = "Test"
    
    included_extensions = ["mp4", "avi"]
    for key in path_dict:
        if not key.endswith(tuple(included_extensions)):
            if path_dict[key][1].fhist.save_in_wait:
                path_dict[key][1].revert_changes()
        else:
            if path_dict[key].fhist.save_in_wait:
                path_dict[key].revert_changes()
                
    #REMOVE ALL OUTPUTS FIRST IF THERE IS ANY
    dirrs = [x for x in os.walk(spath)][1:]

    for ent in dirrs:
        for filee in ent[2]:
            pathhh = os.path.join(ent[0], filee)
            if not pathhh.endswith(tuple(included_extensions)):
                os.remove(pathhh)
    
    export_dict = {k: (True if type(v) != FolderDesc else False) for k, v in path_dict.items()}   
    
    for k, v in export_dict.items():       
        handlee = None
        pathh = ""
        if v == True:
            handlee = path_dict[k][1]
        else:
            handlee = path_dict[k]
            
        pathh = k
        
        # ONLY GREEN
        
        if v == True:
            for path in [val for x in os.walk(pathh) for val in x[2] if val.endswith(tuple(included_extensions))]:
                if not os.path.isfile(os.path.join(pathh, path) + ".jpeg"):
                    green_file_not_exist(os.path.join(pathh, path), handlee.fhist.bbox_rois_list, handlee.fhist.crop_index)
                else:
                    green_file_exist(os.path.join(pathh, path) + ".jpeg", handlee.fhist.bbox_rois_list, handlee.fhist.crop_index)
        else:
            if not os.path.isfile(pathh + ".jpeg"):
                green_file_not_exist(pathh, handlee.fhist.bbox_rois_list, handlee.fhist.crop_index)
            else:
                green_file_exist(pathh + ".jpeg", handlee.fhist.bbox_rois_list, handlee.fhist.crop_index)
        
    for k, v in export_dict.items():
        handlee = None
        pathh = ""
        pathh_real = ""
        if v == True:
            handlee = path_dict[k][1]
            pathh_real = path_dict[k][0]
            pathh = k
        else:
            continue
            
        # CROP (RED)
        if len(handlee.fhist.bbox_rois_list) == 1:
            smallest_crop = handlee.fhist.bbox_rois_list[0]
            single_found = False
            for k_inner, v_inner in export_dict.items():
                if (v_inner == False) and (os.path.normpath(pathh) == os.path.dirname(os.path.normpath(k_inner))):
                    handleeinner = path_dict[k_inner]
                    
                    if len(handleeinner.fhist.bbox_rois_list) == 0:
                        continue
                    
                    inner_crop = handleeinner.fhist.bbox_rois_list[0]
                    
                    #BBOX CHECK
                    inner_inside = bbox_check(inner_crop, smallest_crop)
                    
                    if inner_inside[0] is True:                    
                        if inner_inside[1] == -1:
                            crop_the_image(k_inner + ".jpeg", inner_crop)
                        elif inner_inside[1] == 1:
                            crop_the_image(k_inner + ".jpeg", smallest_crop)
                        else:
                            raise RuntimeError
                    elif inner_inside[0] is False:
                        returned_crop = inner_inside[1]
                        crop_the_image(k_inner + ".jpeg", returned_crop)
                    else:
                        raise RuntimeError
                        
                    export_dict[k_inner] = None
                    single_found = True
                    
            if not single_found:
                crop_the_image(pathh_real + ".jpeg", smallest_crop)
                
    # CROP (RED) SINGLE ONES
    for k, v in export_dict.items():
        if (v is False) and (type(path_dict[k]) == FolderDesc) and (len(handleeinner.fhist.bbox_rois_list) != 0):
            handleeinner = path_dict[k]
            inner_crop = handleeinner.fhist.bbox_rois_list[0]
            crop_the_image(k + ".jpeg", inner_crop)
         
    path_dict.clear()
                     
def mouse_event(event, x, y, flags, param):
    global rect_bbox, rect_endpoint_tmp, drawing

    fldsc = param

    if event == cv2.EVENT_LBUTTONDOWN:
        rect_endpoint_tmp = None
        rect_bbox = (x, y)
        drawing = True
    elif event == cv2.EVENT_LBUTTONUP:
        rect_endpoint_tmp = (x, y)
        drawing = False

        if selectionrd.get() == 1:
            fldsc.draw_rectangle(rect_bbox, rect_endpoint_tmp,
                                 color=(0, 0, 255), crop=True)
        elif selectionrd.get() == 2:
            fldsc.draw_rectangle(rect_bbox, rect_endpoint_tmp,
                                 color=(0, 255, 0), fill=True)

        fldsc.draw()
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        rect_endpoint_tmp = (x, y)


def save_config():
    global spath, wfolder, wfile
        
    if spath == "":
        create_popup("Please first choose a working directory.")
        return
    
    if wfolder == "" and wfile == "":
        create_popup("You never opened an any video before.")
        return

    filee = ""
    if wfile == "":
        filee = files.get()[0]
    else:
        filee = wfile

    path = os.path.join(wfolder, filee)

    if wfile == "":
        if wfolder in path_dict:
            path_dict[wfolder][1].save_config()
        else:
            create_popup("You never configured for the whole folder before. There is nothing to save.")
    else:
        if path in path_dict:
            path_dict[path].save_config()
        else:
            create_popup("You never configured for this video before. There is nothing to save.")

def preview():
    global spath, wfolder
    
    if spath == "":
        create_popup("Please first choose a working directory.")
        return
    
    if wfolder in path_dict:
        path_dict[wfolder][1].preview()
    else:
        create_popup("You never started to configure for this folder.")
        
def preview_special():
    global spath, wfolder, wfile
    
    if spath == "":
        create_popup("Please first choose a working directory.")
        return

    filee = ""
    if wfile == "":
        filee = files.get()[0]
    else:
        filee = wfile

    path = os.path.join(wfolder, filee)
    
    if path in path_dict:
        path_dict[path].preview()
    else:
        create_popup("Video never started for editing.")

def save_cwd():
    global spath

    tk.Tk().withdraw()
    spath = filedialog.askdirectory()

    folders.set(tuple([x[0] for x in os.walk(spath)])[1:])    
    lbox.selection_set(0)
    lbox2.selection_set(0)
    
    btnpath["state"] = "disabled"
    
    lbox_onselect(None)

def start():
    global spath, wfolder, wfile
    
    if spath == "":
        create_popup("Please first choose a working directory.")
        return
    
    if selectionrd.get() == 2:
        create_popup("Why do you need to draw for the whole directory anyway?")
        return

    folderr = lbox.get(lbox.curselection()[0])
    filee = files.get()[0]

    path = os.path.join(folderr, filee)

    wfolder = folderr
    wfile = ""

    at_draw(path)


def start_special():
    global spath, wfolder, wfile
    
    if spath == "":
        create_popup("Please first choose a working directory.")
        return

    folderr = lbox.get(lbox.curselection()[0])
    fileecs = lbox2.curselection()
    
    if len(fileecs) == 0:
        create_popup("Please select a video.")
        return
    
    filee = lbox2.get(fileecs[0])
    

    path = os.path.join(folderr, filee)

    wfolder = folderr
    wfile = filee

    at_draw(path)

def lbox_onselect(event):
    global wfolder, wfile
    
    if len(folders.get()) == 0:
        return
    
    index = int(lbox.curselection()[0])
    value = lbox.get(index)

    included_extensions = ["mp4", "avi"]
 
    xx = [val for x in os.walk(value) for val in x[2] if val.endswith(tuple(included_extensions))]
    files.set(tuple(xx))
    
    if wfolder != value:
        lbox2.selection_set(0)
        wfile = files.get()[0]
        
    wfolder = value
    wfile = lbox2.get(lbox2.curselection()[0])
    
def rb_onselect():
    if selectionrd.get() == 2:
        btnstart["state"] = "disabled"
    elif selectionrd.get() == 1:
        btnstart["state"] = "enabled"
    else:
        raise RuntimeError
        
def process_video_action(key):
    global fcounter, quited, paused
    
    if key == ord('q'):
        quited = True
    elif key == ord('p'):
        paused = not paused
    elif key == ord('r'):
        

def at_draw(path):
    global rect_bbox, rect_endpoint_tmp, path_dict, handle_cpy, wfolder, wfile, drawing

    if path == "":
        return
    
    if wfile == "":
        if wfolder in path_dict:
            fldsc = path_dict[wfolder][1]
        else:
            fldsc = FolderDesc(path)
            path_dict[wfolder] = (path, fldsc)
    elif path in path_dict:
        fldsc = path_dict[path]
    elif not path in path_dict:
        fldsc = FolderDesc(path)
        path_dict[path] = fldsc
    else:
        return

    included_extensions = ["mp4", "avi"]
    for key in path_dict:
        if not key.endswith(tuple(included_extensions)):
            if path_dict[key][1].fhist.save_in_wait:
                path_dict[key][1].revert_changes()
        else:
            if path_dict[key].fhist.save_in_wait:
                path_dict[key].revert_changes()

    cv2.namedWindow('Metamorphose')
    cv2.setMouseCallback('Metamorphose', mouse_event, param=fldsc)

    while True:

        if not drawing:
            fldsc.draw()
        elif drawing and rect_endpoint_tmp:

            handle_cpy = fldsc.open_handle.copy()

            if selectionrd.get() == 1:
                cv2.rectangle(handle_cpy, rect_bbox,
                              rect_endpoint_tmp, (0, 0, 255), 1)
            elif selectionrd.get() == 2:
                cv2.rectangle(handle_cpy, rect_bbox,
                              rect_endpoint_tmp, (0, 255, 0), 1)

            cv2.imshow('Metamorphose', handle_cpy)

        key = cv2.waitKey(1) & 0xFF
        # if the 'c' key is pressed, break from the loop
        if key == ord('c'):
            break

    cv2.destroyAllWindows()
    
def at_draw_video(path):
    global rect_bbox, rect_endpoint_tmp, path_dict, handle_cpy, wfolder, wfile, drawing

    if path == "":
        return
    
    if wfile == "":
        if wfolder in path_dict:
            fldsc = path_dict[wfolder][1]
        else:
            fldsc = FolderDesc(path)
            path_dict[wfolder] = (path, fldsc)
    elif path in path_dict:
        fldsc = path_dict[path]
    elif not path in path_dict:
        fldsc = FolderDesc(path)
        path_dict[path] = fldsc
    else:
        return

    included_extensions = ["mp4", "avi"]
    for key in path_dict:
        if not key.endswith(tuple(included_extensions)):
            if path_dict[key][1].fhist.save_in_wait:
                path_dict[key][1].revert_changes()
        else:
            if path_dict[key].fhist.save_in_wait:
                path_dict[key].revert_changes()

    cv2.namedWindow('Metamorphose')
    cv2.setMouseCallback('Metamorphose', mouse_event, param=fldsc)


    
    cap = cv2.VideoCapture(path)
    while cap.isOpened():
        
        if quited:
            pass
        
        elif paused:
            pass

        else:
            ret, frame = cap.read()
            
            if not ret:
                break

            cv2.imshow("MetamophoseXXXX", frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            process_video_action(key)

    while True:

        if not drawing:
            fldsc.draw()
        elif drawing and rect_endpoint_tmp:

            handle_cpy = fldsc.open_handle.copy()

            if selectionrd.get() == 1:
                cv2.rectangle(handle_cpy, rect_bbox,
                              rect_endpoint_tmp, (0, 0, 255), 1)
            elif selectionrd.get() == 2:
                cv2.rectangle(handle_cpy, rect_bbox,
                              rect_endpoint_tmp, (0, 255, 0), 1)

            cv2.imshow('Metamorphose', handle_cpy)

        key = cv2.waitKey(1) & 0xFF
        # if the 'c' key is pressed, break from the loop
        if key == ord('c'):
            break

    cv2.destroyAllWindows()
    

window = tk.Tk()
window.geometry("800x600")

selectionrd = tk.IntVar()
values = {"Crop": 1,
          "Draw": 2, }
for (text, value) in values.items():
    tk.Radiobutton(window, text=text, variable=selectionrd,
                   value=value, indicator=0,
                   background="light blue", command=rb_onselect).pack()

btnstart = ttk.Button(window, text="Start For The All Folder",
                      command=lambda: start())
btnstart.pack()
btnstartspecial = ttk.Button(window, text="Start Only For This File",
                             command=lambda: start_special()).pack()
btnclear = ttk.Button(window, text="Save the Config",
                      command=lambda: save_config()).pack()
btnprvwspecial = ttk.Button(window, text="Preview Special",
                     command=lambda: preview_special()).pack()
btnprvw = ttk.Button(window, text="Preview",
                     command=lambda: preview()).pack()
btnpath = ttk.Button(window, text="Select Video Directory",
                     command=lambda: save_cwd())
btnpath.pack()
btnexpert = ttk.Button(window, text="Export All Changes",
                     command=lambda: export()).pack()

folders = tk.Variable()
lbox = tk.Listbox(window, height=10, listvariable=folders,
                  selectmode=tk.EXTENDED, exportselection=False)
lbox.bind('<<ListboxSelect>>', lbox_onselect)

files = tk.Variable()
lbox2 = tk.Listbox(window, height=10, listvariable=files,
                   selectmode=tk.EXTENDED, exportselection=False)
lbox2.bind('<<ListboxSelect>>', lbox_onselect)

lbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
lbox2.pack(expand=True, fill=tk.BOTH)

window.mainloop()