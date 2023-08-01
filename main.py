import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk
import glob
import os

class FolderDesc:
    def __init__(self, path):        
        self.pure_handle = None
        self.handle = None
        self.open_handle = None
        self.crop_handle = None
        #self.is_crop_in_wait = False
        self.save_in_wait = False
        self.old_crop_index = -1
        self.crop_index = -1
        self.old_hist_index = 0
        self.hist_index = 0
        
        self.bbox_rois_list = []
        self.bbox_roi_crop = None
        
        self.pure_handle = cv2.imread(path, cv2.IMREAD_COLOR)
        self.handle = self.pure_handle.copy()
        self.open_handle = self.pure_handle.copy()
        self.crop_handle = self.pure_handle.copy()
        
    def open(self):
        self.hist_index = len(self.bbox_rois_list)
        
    def save_config(self):
        self.old_hist_index = self.hist_index
        self.old_crop_index = self.crop_index
        self.handle = self.open_handle.copy()
        self.save_in_wait = False
        print("---AT SAVE CONFIG---")
        print(self.bbox_rois_list)
        print("crop", self.crop_index) 
        print("oldhist", self.old_hist_index) 
        print("hist", self.hist_index)               
                
    def draw_rectangle(self, point1, point2, color=(0, 255, 0), fill=False, crop=False):
        print("---AT draw_rectangle BEGUNNING---")
        print("crop", self.crop_index) 
        print("oldhist", self.old_hist_index) 
        print("hist", self.hist_index) 
        if crop:
            if self.crop_index != -1: 
                self.revert_crop()              
                self.bbox_rois_list.pop(self.crop_index)
                
                # if self.crop_index < self.old_hist_index - 1:
                #     self.old_hist_index -= 1 
                if self.crop_index < self.hist_index:
                    self.hist_index -= 1 
              
            self.crop_index = len(self.bbox_rois_list)
                                    
        self.bbox_rois_list.append((point1, point2))
        
        if fill:
            fill = -1
        else:
            fill = 1     
            
        self.hist_index += 1
        self.save_in_wait = True 
        
        print("---AT draw_rectangle ENDDDDDDDD---")
        print("crop", self.crop_index) 
        print("oldhist", self.old_hist_index) 
        print("hist", self.hist_index)           
            
        cv2.rectangle(self.open_handle, point1, point2, color, thickness=fill)
        if not crop:
            cv2.rectangle(self.crop_handle, point1, point2, color, thickness=fill)        
                
    def revert_crop(self):
        self.open_handle = self.crop_handle.copy()
        
    def revert_changes(self):
        self.save_in_wait = False
        print("---AT REVERT CHANGES BEGUNNING---")
        print("crop", self.crop_index) 
        print("oldhist", self.old_hist_index) 
        print("hist", self.hist_index) 
        print("LEEEEEEEEEEEEEEEEEEEEEEN") 
        print(len(self.bbox_rois_list)) 
        print("LEEEEEEEEEEEEEEEEEEEEEEN")
        if self.crop_index >= self.old_hist_index and self.crop_index < self.hist_index:
            self.crop_index = self.old_crop_index
            
        
        del self.bbox_rois_list[self.old_hist_index:self.hist_index]
        
        self.open_handle = self.handle.copy()
        self.crop_handle = self.pure_handle.copy()
        for i in range(self.old_hist_index):
            if i == self.crop_index:
                continue
            
            (p1, p2) = self.bbox_rois_list[i]
            cv2.rectangle(self.crop_handle, p1, p2, color=(0, 255, 0), thickness=-1)
            
        self.hist_index = self.old_hist_index
        print("---AT REVERT CHANGES---")
        print(self.bbox_rois_list)
        print("crop", self.crop_index) 
        print("oldhist", self.old_hist_index) 
        print("hist", self.hist_index) 
        
    def draw(self):        
        cv2.imshow("Metamorphose", self.open_handle)
        
path_dict = {}
path = ""
rect_bbox = None
rect_endpoint_tmp = None
bbox_list_rois = []
bbox_list_roi_crop = None
handle = None
handle_cpy = None
drawing = False

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
            fldsc.draw_rectangle(rect_bbox, rect_endpoint_tmp, color=(0, 0, 255), crop=True)  
        elif selectionrd.get() == 2:
            fldsc.draw_rectangle(rect_bbox, rect_endpoint_tmp, color=(0, 255, 0), fill=True)
                
        fldsc.draw()
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        rect_endpoint_tmp = (x, y)
        
def save_config(fpath):
    path = fpath.get()  
    path_dict[path].save_config()
    
def at_draw(fpath):
        global rect_bbox, rect_endpoint_tmp, path_dict, handle_cpy, drawing
    
        path = fpath.get()
    
        if path != "" and path in path_dict:
            fldsc = path_dict[path]           
        elif path != "" and not path in path_dict:
            fldsc = FolderDesc(path)            
            path_dict[path] = fldsc            
        else:
            return
        
        fldsc.open()
        for key in path_dict:
            if path_dict[key].save_in_wait: 
                path_dict[key].revert_changes()
            
        cv2.namedWindow('Metamorphose')
        cv2.setMouseCallback('Metamorphose', mouse_event, param=fldsc)
        

        while True:                
    
            if not drawing:
                fldsc.draw()
            elif drawing and rect_endpoint_tmp:                           
                
                handle_cpy = fldsc.open_handle.copy()
                
                if selectionrd.get() == 1:
                    cv2.rectangle(handle_cpy, rect_bbox, rect_endpoint_tmp, (0, 0, 255), 1)
                elif selectionrd.get() == 2:
                    cv2.rectangle(handle_cpy, rect_bbox, rect_endpoint_tmp, (0, 255, 0), 1)
                
                cv2.imshow('Metamorphose', handle_cpy)

            key = cv2.waitKey(1) & 0xFF
            # if the 'c' key is pressed, break from the loop
            if key == ord('c'):
                break
            
        cv2.destroyAllWindows()        
        
        
path_dict = {}
bbox_list_rois = []
bbox_list_roi_crop = None

included_extensions = ['jpg','jpeg', 'bmp', 'png', "mp4", "avi"]

window = tk.Tk()

selectioncmb = tk.StringVar()
cmbbox = ttk.Combobox(window, textvariable=selectioncmb)

cmbbox["values"] = [fn for fn in os.listdir(".")
                    if any(fn.endswith(ext) for ext in included_extensions)]

selectionrd = tk.IntVar()
values = {"Crop" : 1,
          "Draw" : 2,}
for (text, value) in values.items():
    tk.Radiobutton(window, text = text, variable = selectionrd,
                   value = value, indicator = 0,
                   background = "light blue").pack()

btnstart = ttk.Button(window, text="Start",
                      command=lambda: at_draw(selectioncmb)).pack()
btnclear = ttk.Button(window, text="Save the Config",
                      command=lambda: save_config(selectioncmb)).pack()

cmbbox.pack()

window.mainloop()