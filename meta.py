import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import glob
import os
from pathlib import Path
import shutil
import sys
from PIL import Image
import imagehash

LIES = 0
ERRORS = 1

path_dict = {}
spath = ""
wfolder = ""
wfile = ""
rect_bbox = None
rect_endpoint_tmp = None
handle_cpy = None
drawing = False
fcounter = 0       
fslice_start = -1
fslice_end = -1
vslice_start = -1
vslice_end = -1
quited = False
paused = False

def create_popup(textt):
    top= tk.Toplevel(window)
    top.title("ERROR")
    root_x = window.winfo_rootx()
    root_y = window.winfo_rooty()    
    win_x = root_x + 300
    win_y = root_y + 100
    top.geometry(f'+{win_x}+{win_y}')
    tk.Label(top, text=textt).pack()


class FrameInfo:
    def __init__(self, points, frame_number, drtype):
        self.points = points
        self.frame_number = frame_number
        self.drtype = drtype

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
                
            for index in sorted(self.crop_trash)[:-1]:
                del self.bbox_rois_list[index]                

            self.crop_trash.clear()
            self.crop_index -= dcount

        self.old_crop_index = self.crop_index
        self.old_bbox_rois_list = self.bbox_rois_list.copy()
        
    def save_changes_slice(self, start, end, drtype):      
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
        
        rstart = min(start, end)
        rend = max(start, end)
        
        temp_set = set(self.old_bbox_rois_list)
        temp_diff = [x for x in self.bbox_rois_list if x not in temp_set]
        
        self.bbox_rois_list = self.old_bbox_rois_list.copy()
        
        for i in range(rstart, rend + 1):
            for temp in temp_diff:
                points = temp.points
                self.bbox_rois_list.append(FrameInfo(points, i, drtype))
        
        self.old_bbox_rois_list = self.bbox_rois_list.copy()

    def revert_changes(self):
        self.save_in_wait = False
        if self.crop_index >= len(self.old_bbox_rois_list):
            self.crop_index = self.old_crop_index

        self.bbox_rois_list = self.old_bbox_rois_list.copy()
        self.crop_trash.clear()

    def push_crop(self, points, cslice):
        self.save_in_wait = True

        self.crop_trash.append(len(self.bbox_rois_list))

        self.crop_index = len(self.bbox_rois_list)
        self.bbox_rois_list.append((points, cslice))

        if self.crop_index != -1:
            return True
        else:
            return False

    def push(self, points):
        self.save_in_wait = True
        self.bbox_rois_list.append(points)
        
    def push_video(self, points, fnumber):
        self.save_in_wait = True
        self.bbox_rois_list.append(FrameInfo(points, *fnumber))


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
        
    def save_config_slice(self, start, end, drtype):
        self.fhist.save_changes_slice(start, end, drtype)

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
            
    def draw_rectangle_video(self, point1, point2, fnumber, color=(0, 255, 0), fill=False, crop=False):
        if crop:
            revert_needed = self.fhist.push_crop((point1, point2), fnumber)

            if revert_needed:
                self.revert_crop()
        else:
            self.fhist.push_video((point1, point2), fnumber)

        if fill:
            fill = -1
        else:
            fill = 1
        
        cv2.rectangle(self.open_handle, point1, point2, color, thickness=fill)
        if not crop:
            cv2.rectangle(self.crop_handle, point1,
                          point2, color, thickness=fill)

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
    
    def revert_changes_video(self):
        self.fhist.revert_changes()

    def draw(self):
        cv2.imshow("Metamorphose", self.open_handle)

def roll_the_dice():
    val = np.random.choice(3, 1, p=[0.75, 0.15, 0.10])[0]
    if val == 0:
        return "Train"
    elif val == 1:
        return "Val"
    elif val == 2:
        return "Test"

def export_new():
    global spath, path_dict
    
    output_dir_name = "class"
    output_trname = "Train"
    output_valname = "Val"
    output_tename = "Test"
    
    for k, v in path_dict.items():
        cap = cv2.VideoCapture(k)
        
        
        ofile_name = Path(k).stem
        odir_path = os.path.dirname(os.path.normpath(k)) + "\\" + output_dir_name + ofile_name + "\\"
        
        if os.path.isdir(odir_path + output_trname):
            shutil.rmtree(odir_path + output_trname)
            os.makedirs(odir_path + output_trname)
            os.makedirs(odir_path + output_trname + "\\" + "Label")
        else:
            os.makedirs(odir_path + output_trname)
            os.makedirs(odir_path + output_trname + "\\" + "Label")
        
        if os.path.isdir(odir_path + output_valname):
            shutil.rmtree(odir_path + output_valname)
            os.makedirs(odir_path + output_valname)
            os.makedirs(odir_path + output_valname + "\\" + "Label")   
        else:
            os.makedirs(odir_path + output_valname)
            os.makedirs(odir_path + output_valname + "\\" + "Label") 
            
        if os.path.isdir(odir_path + output_tename):
            shutil.rmtree(odir_path + output_tename)
            os.makedirs(odir_path + output_tename)
            os.makedirs(odir_path + output_tename + "\\" + "Label")   
        else:
            os.makedirs(odir_path + output_tename)
            os.makedirs(odir_path + output_tename + "\\" + "Label")
            
        
        
        
        frame_export_num = 0
        
        points_found = False
        r_start = -1
        r_end = sys.maxsize
        if v.fhist.crop_index != -1:
            points_found = True
            (xy1, xy2), se_slice = v.fhist.bbox_rois_list[v.fhist.crop_index]
            r_start = min(se_slice[0], se_slice[1])
            r_end = max(se_slice[0], se_slice[1])
            
            x_min = min(xy1[0], xy2[0])
            x_max = max(xy1[0], xy2[0])
            y_min = min(xy1[1], xy2[1])
            y_max = max(xy1[1], xy2[1])
            
            del v.fhist.bbox_rois_list[v.fhist.crop_index]
        
        temp_frame = np.asarray([[[0]]])
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        sample_rate = 0.0
        counter_bfchanged = 0.1
        counter_scale_change = 0.05
        error_set = {fi.frame_number for fi in v.fhist.bbox_rois_list if fi.drtype == ERRORS}
        lie_set = {fi.frame_number for fi in v.fhist.bbox_rois_list if fi.drtype == LIES}

        while cap.isOpened():
            ret, frame = cap.read()

            hash0 = imagehash.phash(Image.fromarray(frame))

            if frame_export_num != 0:
                hash1 = imagehash.phash(Image.fromarray(temp_frame))
                cutoff = 3

                if hash0 - hash1 < cutoff:                    
                    counter_bfchanged += counter_scale_change
                    sample_rate += counter_bfchanged / fps
                    counter_scale_change *= 2
                else:
                    sample_rate += 1.0

            temp_frame = frame.copy()

            if frame_export_num in error_set:
                sample_rate += 1.0
            elif frame_export_num in lie_set:
                sample_rate += 0.05

            if sample_rate < 1.0:                
                frame_export_num += 1
                continue
            else:
                sample_rate = 0.0
                counter_bfchanged = 0.1
                counter_scale_change = 0.05
            
            if frame_export_num > r_end:
                break
            
            if frame_export_num < r_start:
                frame_export_num += 1
                continue
            
            if not ret:
                break
                        
            frame_found = False
            lie_found = False
            error_found = False
            will_delete = []
            for index, fi in enumerate(v.fhist.bbox_rois_list):
                if not frame_found and fi.frame_number == frame_export_num:
                    frame_found = True
                    a = np.empty(frame.shape)
                    a[:, :] = (0, 0, 0)
                    frame[:, :] = a

                    if fi.drtype == LIES:
                        lie_found = True
                        cv2.rectangle(frame, fi.points[0], fi.points[1], color=(255, 255, 255), thickness=-1)
                    elif fi.drtype == ERRORS:
                        error_found = True
                        cv2.rectangle(frame, fi.points[0], fi.points[1], color=(255, 0, 0), thickness=-1)
                    
                    will_delete.append(index)
                elif frame_found and fi.frame_number == frame_export_num:
                    if fi.drtype == LIES:
                        lie_found = True
                        cv2.rectangle(frame, fi.points[0], fi.points[1], color=(255, 255, 255), thickness=-1)
                    elif fi.drtype == ERRORS:
                        error_found = True
                        cv2.rectangle(frame, fi.points[0], fi.points[1], color=(255, 0, 0), thickness=-1)
                    
                    will_delete.append(index)
                    
            
            for i in sorted(will_delete, reverse=True):
                del v.fhist.bbox_rois_list[i]
                 
            
            otraindir_path = odir_path + output_trname + "\\" + str(frame_export_num) + ".jpeg"
            otraindir_both_label_path = odir_path + output_trname + "\\" + "Label\\" + str(frame_export_num) + ".jpeg"
            otraindir_lie_label_path = odir_path + output_trname + "\\" + "Label\\" + str(frame_export_num) + "l.jpeg"
            otraindir_error_label_path = odir_path + output_trname + "\\" + "Label\\" + str(frame_export_num) + "e.jpeg"
            ovaldir_path = odir_path + output_valname + "\\" + str(frame_export_num) + ".jpeg"
            ovaldir_label_path = odir_path + output_valname + "\\" + "Label\\" + str(frame_export_num) + ".jpeg"
            otestdir_path = odir_path + output_tename + "\\" + str(frame_export_num) + ".jpeg"
            otestdir_label_path = odir_path + output_tename + "\\" + "Label\\" + str(frame_export_num) + ".jpeg"
            
            
            if points_found:
                frame = frame[y_min:y_max, x_min:x_max]
            
            
            wtype = roll_the_dice()
            wtype = "Train" #-----------------------------

            if wtype == "Train":
                if not frame_found:
                    cv2.imwrite(otraindir_path, frame)
                else:
                    cv2.imwrite(otraindir_path, temp_frame)
                    if error_found and lie_found:
                        cv2.imwrite(otraindir_both_label_path, frame)
                    elif error_found:
                        cv2.imwrite(otraindir_error_label_path, frame)
                    elif lie_found:
                        cv2.imwrite(otraindir_lie_label_path, frame)
            elif wtype == "Val":   
                if not frame_found:
                    cv2.imwrite(ovaldir_path, frame)
                else:
                    cv2.imwrite(ovaldir_path, temp_frame)
                    cv2.imwrite(ovaldir_label_path, frame)             
            elif wtype == "Test":                
                if not frame_found:
                    cv2.imwrite(otestdir_path, frame)
                else:
                    cv2.imwrite(otestdir_path, temp_frame)
                    cv2.imwrite(otestdir_label_path, frame)
            
                
            frame_export_num += 1

        cap.release()

def mouse_event_video(event, x, y, flags, param):
    global rect_bbox, rect_endpoint_tmp, drawing, fcounter, vslice_start, vslice_end

    fldsc = param

    if event == cv2.EVENT_LBUTTONDOWN:
        rect_endpoint_tmp = None
        rect_bbox = (x, y)
        drawing = True
    elif event == cv2.EVENT_LBUTTONUP:
        rect_endpoint_tmp = (x, y)
        drawing = False

        if selectionrd.get() == 1:
            fldsc.draw_rectangle_video(rect_bbox, rect_endpoint_tmp, (vslice_start, vslice_end),
                                 color=(0, 0, 255), crop=True)
        elif selectionrd.get() == 2:
            fldsc.draw_rectangle_video(rect_bbox, rect_endpoint_tmp, (fcounter, LIES),
                                 color=(0, 255, 0), fill=True)
        elif selectionrd.get() == 3:
            fldsc.draw_rectangle_video(rect_bbox, rect_endpoint_tmp, (fcounter, ERRORS),
                                 color=(255, 0, 0), fill=True)

        fldsc.draw()
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        rect_endpoint_tmp = (x, y)

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

    at_draw_video(path)
    
def save_cwd():
    global spath

    tk.Tk().withdraw()
    spath = filedialog.askdirectory()

    folders.set(tuple([x[0] for x in os.walk(spath)])[1:])    
    lbox.selection_set(0)
    lbox2.selection_set(0)
    
    btnpath["state"] = "disabled"
    
    lbox_onselect(None)

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

def process_video_action(key, frame, handle):
    global fcounter, quited, paused
    
    if key == ord('q'):
        quited = True
    elif key == ord('p'):
        paused = not paused
    elif key == 116: #t
        paused = True
        fcounter -= 500
        handle = frame.copy()
    elif key == 103: #g
        paused = True
        fcounter += 500
        handle = frame.copy()
    elif key == 82: #shift+r
        paused = True
        fcounter -= 25
        handle = frame.copy()
    elif key == 70: #shift+f
        paused = True
        fcounter += 25
        handle = frame.copy()
    elif key == 18: #ctrl+r
        paused = True
        fcounter -= 5
        handle = frame.copy()
    elif key == 6: #ctrl+f
        paused = True
        fcounter += 5
        handle = frame.copy()
    elif key == ord('r'):
        paused = True
        fcounter -= 1
        handle = frame.copy()
    elif key == ord('f'):
        paused = True
        fcounter += 1
        handle = frame.copy()

def at_draw_video(path):    
    global rect_bbox, rect_endpoint_tmp, path_dict, handle_cpy, wfolder, wfile, drawing, fcounter, quited, paused, \
           fslice_start, fslice_end, vslice_start, vslice_end


    def video_info(handle):
        cv2.putText(handle, "Video fps: " + str(fps), (10, 30), font, 0.75, (255, 0, 0), 2)
        cv2.putText(handle, str(fcounter) + "/" + str(int(total_nframes)) + " frames", (10, 60), font, 0.75, (255, 0, 0), 2)
        cv2.putText(handle, "Slice -> " + str(fslice_start) + ":" + str(fslice_end), (10, 90), font, 0.75, (255, 0, 0), 2)
        cv2.putText(handle, "Video crop -> " + str(vslice_start) + ":" + str(vslice_end), (10, 120), font, 0.75, (255, 0, 0), 2)

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

    fcounter = 0
    quited = False
    paused = False
    fslice_start = -1
    fslice_end = -1
    vslice_start = -1
    vslice_end = -1

    cv2.namedWindow('Metamorphose')    
    cv2.setMouseCallback('Metamorphose', mouse_event_video, param=fldsc)

    cap = cv2.VideoCapture(path)
    
    while cap.isOpened():
        
        if not paused:
            if fldsc.fhist.save_in_wait:
                fldsc.revert_changes_video()
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_nframes = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        
        font = cv2.FONT_HERSHEY_SIMPLEX                                
        
        if quited:
            break
        elif paused:
            fcounter -= 1
            
        ret, frame = cap.read()
        
        if fcounter < 0:
            fcounter = 0
        elif fcounter >= total_nframes:
            fcounter = 0    
          
        if not drawing and paused:
            temph = fldsc.open_handle.copy()
                        
            video_info(fldsc.open_handle)
            fldsc.draw()
            
            fldsc.open_handle = temph.copy()
            
            if key == 11:
                fldsc.save_config()
            if key == 12:
                if selectionrd.get() == 2:
                    fldsc.save_config_slice(fslice_start, fslice_end, LIES)
                elif selectionrd.get() == 3:
                    fldsc.save_config_slice(fslice_start, fslice_end, ERRORS)
        elif not drawing and not paused:
            fldsc.open_handle = frame.copy()    
                                
            temph = fldsc.open_handle.copy()            
            
            video_info(fldsc.open_handle)
            fldsc.draw()
            
            fldsc.open_handle = temph.copy()
        elif drawing and rect_endpoint_tmp and paused:     
            handle_cpy = fldsc.open_handle.copy()

            if selectionrd.get() == 1:
                cv2.rectangle(handle_cpy, rect_bbox,
                              rect_endpoint_tmp, (0, 0, 255), 1)
            elif selectionrd.get() == 2:
                cv2.rectangle(handle_cpy, rect_bbox,
                              rect_endpoint_tmp, (0, 255, 0), 1)
            elif selectionrd.get() == 3:
                cv2.rectangle(handle_cpy, rect_bbox,
                              rect_endpoint_tmp, (255, 0, 0), 1)

            video_info(handle_cpy)
            
            cv2.imshow('Metamorphose', handle_cpy)            
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, fcounter)
                
        if not ret:
            break
        
        key = cv2.waitKey(1) & 0xFF
        process_video_action(key, frame, fldsc.open_handle)
        
        if key == 82 or key == 70 or key == 18 or key == 6 or key == ord('r') or key == ord('f'):       
            fldsc.open_handle = frame.copy()
        
        if key == 22:
            fslice_start = fcounter
            
        if key == 2:
            fslice_end = fcounter
            
        if key == 14:
            vslice_start = fcounter
            
        if key == 13:
            vslice_end = fcounter
                    
        fcounter += 1                
        
    cap.release()
    cv2.destroyAllWindows()

window = tk.Tk()
window.geometry("800x600")

selectionrd = tk.IntVar()
values = {"Crop": 1,
          "Draw_Lies": 2,
          "Draw_Errors": 3}
for (text, value) in values.items():
    tk.Radiobutton(window, text=text, variable=selectionrd,
                   value=value, indicator=0,
                   background="light blue").pack()

btnstartspecial = ttk.Button(window, text="Start",
                             command=lambda: start_special()).pack()
btnpath = ttk.Button(window, text="Select Video Directory",
                     command=lambda: save_cwd())
btnpath.pack()
btnexpert = ttk.Button(window, text="Export All Changes",
                     command=lambda: export_new()).pack()

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