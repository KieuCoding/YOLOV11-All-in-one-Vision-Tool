from ultralytics import YOLO
import cv2, os, shutil, threading, random, sys, contextlib 
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageEnhance


# Augmentation backend fuction
class Augmentation:
    def __init__(self):
        pass

    # Augmentation Handler
    def augment(self, image_dir, label_dir, output, flip=False, brightness=False):
        print("Augmenting in progress...")

        # no folder or path exist then make them
        if not os.path.exists(output):
            os.makedirs(output)
        
        # folders are founded
        output_image_dir = os.path.join(output, "images")
        output_label_dir = os.path.join(output, "labels")

        os.makedirs(output_image_dir, exist_ok=True)
        os.makedirs(output_label_dir, exist_ok=True)

        image_files = [
            f for f in os.listdir(image_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        for image_file in image_files:
            image_path = os.path.join(image_dir, image_file)
            label_file = os.path.splitext(image_file)[0] + ".txt"
            label_path = os.path.join(label_dir, label_file)

            image = Image.open(image_path).convert("RGB")

            base_name = os.path.splitext(image_file)[0]
            ext = os.path.splitext(image_file)[1]

            # Save original image
            original_output_image = os.path.join(output_image_dir, image_file)
            image.save(original_output_image)

            # Save original label
            if os.path.exists(label_path):
                shutil.copy(label_path, os.path.join(output_label_dir, label_file))

            # Horizontal flip augmentation
            if flip:
                flipped_image = image.transpose(Image.FLIP_LEFT_RIGHT)

                flipped_image_name = base_name + "_hflip" + ext
                flipped_label_name = base_name + "_hflip.txt"

                flipped_image.save(os.path.join(output_image_dir, flipped_image_name))

                if os.path.exists(label_path):
                    self.flip_yolo_label_horizontal(
                        label_path,
                        os.path.join(output_label_dir, flipped_label_name)
                    )

            # Brightness augmentation
            if brightness:
                enhancer = ImageEnhance.Brightness(image)

                bright_image = enhancer.enhance(1.4)

                bright_image_name = base_name + "_bright" + ext
                bright_label_name = base_name + "_bright.txt"

                bright_image.save(os.path.join(output_image_dir, bright_image_name))

                if os.path.exists(label_path):
                    shutil.copy(
                        label_path,
                        os.path.join(output_label_dir, bright_label_name)
                    )

        print("Augmentation finished")

    # Horizontal flip YOLO bbox label
    def flip_yolo_label_horizontal(self, input_label, output_label):
        with open(input_label, "r") as f:
            lines = f.readlines()

        with open(output_label, "w") as f:
            for line in lines:
                parts = line.strip().split()

                if len(parts) < 5:
                    continue

                class_id = parts[0]
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])

                flipped_x = 1.0 - x_center

                f.write(f"{class_id} {flipped_x} {y_center} {width} {height}\n")
# Annotation backend function
class Annotation:
    def __init__(self):
        pass

    # Bounding box annotation function
    def bbox_anno(self, image_dir, label_dir, class_names):
        print("bbox annotator open")

        if len(class_names) == 0:
            messagebox.showerror("Class Error", "Please enter class names first.")
            return    

        if not os.path.exists(label_dir):
            os.makedirs(label_dir)

        # look at the images under jpg, jpeg, png format
        image_files = [
            f for f in os.listdir(image_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        # If no files found
        if len(image_files) == 0:
            print("No images found")
            return

        window = tk.Toplevel()
        window.title("Bounding Box Annotator")
        window.geometry("1000x750")

        # Scrollable annotation window
        annotation_canvas = tk.Canvas(window)
        annotation_canvas.pack(side="left", fill="both", expand=True)

        annotation_scrollbar = ttk.Scrollbar(window, orient="vertical", command=annotation_canvas.yview)
        annotation_scrollbar.pack(side="right", fill="y")

        annotation_canvas.configure(yscrollcommand=annotation_scrollbar.set)

        annotation_frame = ttk.Frame(annotation_canvas)
        annotation_canvas.create_window((0, 0), window=annotation_frame, anchor="nw")

        def update_annotation_scroll_region(event):
            annotation_canvas.configure(scrollregion=annotation_canvas.bbox("all"))

        def annotation_mousewheel_scroll(event):
            annotation_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        annotation_frame.bind("<Configure>", update_annotation_scroll_region)
        annotation_canvas.bind("<MouseWheel>", annotation_mousewheel_scroll)

        # initialize annotation
        canvas = tk.Canvas(annotation_frame, width=900, height=650, bg="gray")
        canvas.pack()

        current_index = tk.IntVar(value=0)
        selected_class = tk.IntVar(value=0)

        start_x = 0
        start_y = 0
        current_rect = None
        boxes = []

        class_box = ttk.Combobox(
            annotation_frame,
            values=class_names,
            state="readonly"
        )
        class_box.current(0)
        class_box.pack(pady=5)

        img_data = {
            "image": None,
            "tk_image": None,
            "scale_x": 1,
            "scale_y": 1,
            "display_w": 0,
            "display_h": 0
        }

        # load image and readjust it for annotation
        def load_image():
            nonlocal boxes

            boxes = []
            canvas.delete("all")

            image_path = os.path.join(image_dir, image_files[current_index.get()])
            img = Image.open(image_path).convert("RGB")

            original_w, original_h = img.size

            max_w = 900
            max_h = 650
            scale = min(max_w / original_w, max_h / original_h)

            display_w = int(original_w * scale)
            display_h = int(original_h * scale)

            resized = img.resize((display_w, display_h))

            img_data["image"] = img
            img_data["tk_image"] = ImageTk.PhotoImage(resized)
            img_data["scale_x"] = original_w / display_w
            img_data["scale_y"] = original_h / display_h
            img_data["display_w"] = display_w
            img_data["display_h"] = display_h

            canvas.create_image(0, 0, anchor="nw", image=img_data["tk_image"])
            window.title(f"Bounding Box Annotator - {image_files[current_index.get()]}")

        # The function to allow user to use mouse for annotation
        def mouse_down(event):
            nonlocal start_x, start_y, current_rect

            start_x = event.x
            start_y = event.y

            current_rect = canvas.create_rectangle(
                start_x,
                start_y,
                start_x,
                start_y,
                outline="red",
                width=2
            )

        # when mouse dragging shape
        def mouse_drag(event):
            if current_rect is not None:
                canvas.coords(current_rect, start_x, start_y, event.x, event.y)
        
        # when mouse is done
        def mouse_up(event):
            nonlocal current_rect

            end_x = event.x
            end_y = event.y

            x1 = min(start_x, end_x)
            y1 = min(start_y, end_y)
            x2 = max(start_x, end_x)
            y2 = max(start_y, end_y)

            if x2 - x1 < 5 or y2 - y1 < 5:
                canvas.delete(current_rect)
                current_rect = None
                return

            class_id = class_box.current()

            boxes.append((class_id, x1, y1, x2, y2))
            current_rect = None

        def save_labels():
            image_name = image_files[current_index.get()]
            label_name = os.path.splitext(image_name)[0] + ".txt"
            label_path = os.path.join(label_dir, label_name)

            original_w, original_h = img_data["image"].size

            with open(label_path, "w") as f:
                for box in boxes:
                    class_id, x1, y1, x2, y2 = box

                    real_x1 = x1 * img_data["scale_x"]
                    real_y1 = y1 * img_data["scale_y"]
                    real_x2 = x2 * img_data["scale_x"]
                    real_y2 = y2 * img_data["scale_y"]

                    box_w = real_x2 - real_x1
                    box_h = real_y2 - real_y1

                    center_x = real_x1 + box_w / 2
                    center_y = real_y1 + box_h / 2

                    yolo_x = center_x / original_w
                    yolo_y = center_y / original_h
                    yolo_w = box_w / original_w
                    yolo_h = box_h / original_h

                    f.write(f"{class_id} {yolo_x} {yolo_y} {yolo_w} {yolo_h}\n")

            print("Saved:", label_path)

        # go to next image in folder to annotate
        def next_image():
            save_labels()

            if current_index.get() < len(image_files) - 1:
                current_index.set(current_index.get() + 1)
                load_image()
            else:
                print("Finished all images")
        
        # Allow user to undo mistake
        def undo_box():
            if len(boxes) > 0:
                boxes.pop()
                load_image()
        
        # Mouse function integration to GUI
        canvas.bind("<ButtonPress-1>", mouse_down)
        canvas.bind("<B1-Motion>", mouse_drag)
        canvas.bind("<ButtonRelease-1>", mouse_up)

        # Annotation buttons after mouse actions
        ttk.Button(annotation_frame, text="Undo Last Box", command=undo_box).pack(pady=5)
        ttk.Button(annotation_frame, text="Save / Next Image", command=next_image).pack(pady=5)

        load_image()

    # Segmentation annotation function, follows similar logic to bbox
    def seg_anno(self, image_dir, label_dir, class_names):
        print("segmentation annotator open")

        if len(class_names) == 0:
            messagebox.showerror("Class Error", "Please enter class names first.")
            return

        if not os.path.exists(label_dir):
            os.makedirs(label_dir)

        image_files = [
            f for f in os.listdir(image_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        if len(image_files) == 0:
            print("No images found")
            return

        window = tk.Toplevel()
        window.title("Segmentation Annotator")
        window.geometry("1000x750")

        # Scrollable annotation window
        annotation_canvas = tk.Canvas(window)
        annotation_canvas.pack(side="left", fill="both", expand=True)

        annotation_scrollbar = ttk.Scrollbar(window, orient="vertical", command=annotation_canvas.yview)
        annotation_scrollbar.pack(side="right", fill="y")

        annotation_canvas.configure(yscrollcommand=annotation_scrollbar.set)

        annotation_frame = ttk.Frame(annotation_canvas)
        annotation_canvas.create_window((0, 0), window=annotation_frame, anchor="nw")

        def update_annotation_scroll_region(event):
            annotation_canvas.configure(scrollregion=annotation_canvas.bbox("all"))

        def annotation_mousewheel_scroll(event):
            annotation_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        annotation_frame.bind("<Configure>", update_annotation_scroll_region)
        annotation_canvas.bind("<MouseWheel>", annotation_mousewheel_scroll)

        canvas = tk.Canvas(annotation_frame, width=900, height=650, bg="gray")
        canvas.pack()

        current_index = tk.IntVar(value=0)
        polygons = []
        current_points = []

        class_box = ttk.Combobox(annotation_frame, values=class_names, state="readonly")
        class_box.current(0)
        class_box.pack(pady=5)

        img_data = {
            "image": None,
            "tk_image": None,
            "scale_x": 1,
            "scale_y": 1,
            "display_w": 0,
            "display_h": 0
        }

        def load_image():
            nonlocal polygons, current_points

            polygons = []
            current_points = []
            canvas.delete("all")

            image_path = os.path.join(image_dir, image_files[current_index.get()])
            img = Image.open(image_path).convert("RGB")

            original_w, original_h = img.size

            max_w = 900
            max_h = 650
            scale = min(max_w / original_w, max_h / original_h)

            display_w = int(original_w * scale)
            display_h = int(original_h * scale)

            resized = img.resize((display_w, display_h))

            img_data["image"] = img
            img_data["tk_image"] = ImageTk.PhotoImage(resized)
            img_data["scale_x"] = original_w / display_w
            img_data["scale_y"] = original_h / display_h
            img_data["display_w"] = display_w
            img_data["display_h"] = display_h

            canvas.create_image(0, 0, anchor="nw", image=img_data["tk_image"])
            window.title(f"Segmentation Annotator - {image_files[current_index.get()]}")

        def add_point(event):
            x = event.x
            y = event.y

            if x < 0 or y < 0 or x > img_data["display_w"] or y > img_data["display_h"]:
                return

            current_points.append((x, y))

            r = 3
            canvas.create_oval(x - r, y - r, x + r, y + r, fill="red")

            if len(current_points) > 1:
                x1, y1 = current_points[-2]
                x2, y2 = current_points[-1]
                canvas.create_line(x1, y1, x2, y2, fill="red", width=2)

        def finish_polygon():
            nonlocal current_points

            if len(current_points) < 3:
                print("Need at least 3 points for segmentation")
                return

            class_id = class_box.current()

            polygons.append((class_id, current_points.copy()))

            first_x, first_y = current_points[0]
            last_x, last_y = current_points[-1]
            canvas.create_line(last_x, last_y, first_x, first_y, fill="red", width=2)

            current_points = []

        def save_labels():
            image_name = image_files[current_index.get()]
            label_name = os.path.splitext(image_name)[0] + ".txt"
            label_path = os.path.join(label_dir, label_name)

            original_w, original_h = img_data["image"].size

            with open(label_path, "w") as f:
                for polygon in polygons:
                    class_id, points = polygon

                    line = str(class_id)

                    for x, y in points:
                        real_x = x * img_data["scale_x"]
                        real_y = y * img_data["scale_y"]

                        yolo_x = real_x / original_w
                        yolo_y = real_y / original_h

                        line += f" {yolo_x} {yolo_y}"

                    f.write(line + "\n")

            print("Saved:", label_path)

        def next_image():
            save_labels()

            if current_index.get() < len(image_files) - 1:
                current_index.set(current_index.get() + 1)
                load_image()
            else:
                print("Finished all images")

        def undo_point():
            if len(current_points) > 0:
                current_points.pop()
                redraw_canvas()

        def undo_polygon():
            if len(polygons) > 0:
                polygons.pop()
                redraw_canvas()

        def redraw_canvas():
            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=img_data["tk_image"])

            for polygon in polygons:
                class_id, points = polygon

                for i, point in enumerate(points):
                    x, y = point
                    r = 3
                    canvas.create_oval(x - r, y - r, x + r, y + r, fill="red")

                    if i > 0:
                        x1, y1 = points[i - 1]
                        canvas.create_line(x1, y1, x, y, fill="red", width=2)

                first_x, first_y = points[0]
                last_x, last_y = points[-1]
                canvas.create_line(last_x, last_y, first_x, first_y, fill="red", width=2)

            for i, point in enumerate(current_points):
                x, y = point
                r = 3
                canvas.create_oval(x - r, y - r, x + r, y + r, fill="blue")

                if i > 0:
                    x1, y1 = current_points[i - 1]
                    canvas.create_line(x1, y1, x, y, fill="blue", width=2)

        canvas.bind("<ButtonPress-1>", add_point)

        ttk.Button(annotation_frame, text="Finish Polygon", command=finish_polygon).pack(pady=5)
        ttk.Button(annotation_frame, text="Undo Point", command=undo_point).pack(pady=5)
        ttk.Button(annotation_frame, text="Undo Polygon", command=undo_polygon).pack(pady=5)
        ttk.Button(annotation_frame, text="Save / Next Image", command=next_image).pack(pady=5)

        load_image()

    # Yaml file creator
    def yaml(self, dataset_path, class_names):
        yaml_path = f"{dataset_path}/dataset.yaml"
        with open(yaml_path, "w") as f:
            f.write(f"path: {dataset_path}\n")
            f.write("train: images/train\n")
            f.write("val: images/val\n")
            f.write("names:\n")
            for i, name in enumerate(class_names):
                f.write(f"  {i}: {name}\n")
        return yaml_path

    # Prepare YOLO dataset folder structure
    def prepare_dataset(self, image_dir, label_dir, output_dataset_path, class_names, train_split=0.8):
        image_files = [
            f for f in os.listdir(image_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        random.shuffle(image_files)

        split_index = int(len(image_files) * train_split)

        train_images = image_files[:split_index]
        val_images = image_files[split_index:]

        folders = [
            "images/train",
            "images/val",
            "labels/train",
            "labels/val"
        ]

        for folder in folders:
            os.makedirs(os.path.join(output_dataset_path, folder), exist_ok=True)

        def copy_files(file_list, split_name):
            for image_file in file_list:
                image_path = os.path.join(image_dir, image_file)

                label_file = os.path.splitext(image_file)[0] + ".txt"
                label_path = os.path.join(label_dir, label_file)

                output_image_path = os.path.join(output_dataset_path, "images", split_name, image_file)
                output_label_path = os.path.join(output_dataset_path, "labels", split_name, label_file)

                shutil.copy(image_path, output_image_path)

                if os.path.exists(label_path):
                    shutil.copy(label_path, output_label_path)
                else:
                    with open(output_label_path, "w") as f:
                        pass

        copy_files(train_images, "train")
        copy_files(val_images, "val")

        yaml_path = self.yaml(output_dataset_path, class_names)

        return yaml_path

# YOLOV11 training backend
class Train:
    def __init__(self):
        pass
    
    # Model training function
    def training(self, model_name, dataset_yaml, epochs, imgsz=640):
        model = YOLO(model_name)
        results = model.train(data=dataset_yaml, epochs=epochs, imgsz=imgsz)
        return results

# Model deployment using CV2
class Deployment:
    def __init__(self):
        self.model = None

    # Loading in trained model
    def load(self, model_path):
        self.model = YOLO(model_path)

    # Still jpg or png inferencing
    def image_infer(self, image_path, confidence=0.25):
        results = self.model(image_path, conf=confidence)
        results[0].show()

    # Live camerafeed inferencing
    def camer_infer(self, camera_index=0, confidence=0.25):
        # initiate available camera port
        cap = cv2.VideoCapture(camera_index)
        
        while True:
            ret, frame = cap.read()

            if not ret:
                print("camera not found")
                break

            results = self.model(frame, conf=confidence)
            annotated = results[0].plot()

            # Live inference exit instruction
            cv2.putText(
                annotated,
                "Press Q to quit live inferencing",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.imshow("Live Vision Detection", annotated)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()


# GUI console redirector for training logs
class ConsoleRedirector:
    def __init__(self, log_function):
        self.log_function = log_function
        self.buffer = ""

    def write(self, text):
        if text is None:
            return

        self.buffer += str(text)

        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)

            if line.strip() != "":
                self.log_function(line)

    def flush(self):
        if self.buffer.strip() != "":
            self.log_function(self.buffer.strip())
            self.buffer = ""

# Frontend GUI
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Vision Tool")
        self.root.geometry("700x600")
        self.class_names = []
        self.class_count = tk.IntVar(value=1)

        # create objects for each class
        self.augmentation = Augmentation()
        self.annotation = Annotation()
        self.training = Train()
        self.deployment = Deployment()

        # Augmentation options toggle
        self.flip = tk.BooleanVar(value=True)
        self.brightness = tk.BooleanVar(value=True)

        # Default inputs
        self.dataset_yaml = tk.StringVar()
        self.model_choice = tk.StringVar(value="yolo11n.pt")
        self.epochs = tk.IntVar(value=100)
        self.pt_model_path = tk.StringVar()
        self.imgsz = tk.IntVar(value=640)
        self.camera_index = tk.IntVar(value=0)
        self.confidence = tk.DoubleVar(value=0.25)
        self.train_split = tk.DoubleVar(value=0.8)

        self.status_box = None
        self.epoch_label = None
        self.train_split_label = None
        self.confidence_label = None

        #create the APP
        self.build_ui()

    # APP handler
    def build_ui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.show_main_menu()

    # Clear current window widgets
    def clear_screen(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        self.status_box = None

    # Main menu page
    def show_main_menu(self):
        self.clear_screen()

        ttk.Label(self.main_frame, text="Vision Tool", font=("Arial", 24)).pack(pady=30)
        ttk.Label(self.main_frame, text="Choose a workflow section").pack(pady=10)

        ttk.Button(self.main_frame, text="Augmentation", command=self.show_augmentation_menu, width=35).pack(pady=10)
        ttk.Button(self.main_frame, text="Annotation", command=self.show_annotation_menu, width=35).pack(pady=10)
        ttk.Button(self.main_frame, text="Training", command=self.show_training_menu, width=35).pack(pady=10)
        ttk.Button(self.main_frame, text="Deployment", command=self.show_deployment_menu, width=35).pack(pady=10)

    # Reusable page header
    def page_header(self, title):
        self.clear_screen()

        ttk.Button(self.main_frame, text="Go Back", command=self.show_main_menu).pack(anchor="w", padx=10, pady=10)
        ttk.Label(self.main_frame, text=title, font=("Arial", 20)).pack(pady=10)

    # Reusable status log box
    def add_status_box(self):
        ttk.Label(self.main_frame, text="Status Log").pack(pady=5)

        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(pady=5, fill="both", expand=True)

        self.status_box = tk.Text(status_frame, height=10, width=75, wrap="word")
        self.status_box.pack(side="left", fill="both", expand=True)

        status_scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_box.yview)
        status_scrollbar.pack(side="right", fill="y")

        self.status_box.configure(yscrollcommand=status_scrollbar.set)

    # Augmentation menu page
    def show_augmentation_menu(self):
        self.page_header("Augmentation")

        # Augmentation related buttons
        ttk.Label(self.main_frame, text="Augmentation Options").pack(pady=5)
        ttk.Checkbutton(self.main_frame,text="Horizontal Flip",variable=self.flip).pack()
        ttk.Checkbutton(self.main_frame,text="Brightness",variable=self.brightness).pack()

        ttk.Button(self.main_frame, text="Augment Dataset", command=self.run_augmentation, width=35).pack(pady=15)

        self.add_status_box()

    # Annotation menu page
    def show_annotation_menu(self):
        self.page_header("Annotation")

        # Class amount input for annotation
        ttk.Label(self.main_frame, text="Number of Classes").pack(pady=5)
        ttk.Entry(self.main_frame, textvariable=self.class_count).pack(pady=5)
        ttk.Button(self.main_frame, text="Enter Class Names", command=self.enter_class_names, width=35).pack(pady=5)

        ttk.Button(self.main_frame, text="Annotate Bounding Boxes", command=self.run_bbox_annotation, width=35).pack(pady=10)
        ttk.Button(self.main_frame, text="Annotate Segmentation", command=self.run_segmentation_annotation, width=35).pack(pady=10)

        self.add_status_box()

    # Training menu page
    def show_training_menu(self):
        self.page_header("Training")

        # YOLO model type options
        ttk.Label(self.main_frame, text="Choose model type").pack()
        ttk.Combobox(
            self.main_frame,
            textvariable=self.model_choice,
            values=[
                "yolo11n.pt",
                "yolo11s.pt",
                "yolo11m.pt",
                "yolo11l.pt",
                "yolo11x.pt",
                "yolo11n-seg.pt",
                "yolo11s-seg.pt",
                "yolo11m-seg.pt"
            ],
            state="readonly"
        ).pack(pady=5)

        # Epoch tuning
        self.epoch_label = ttk.Label(self.main_frame, text=f"Epochs: {self.epochs.get()}")
        self.epoch_label.pack()
        ttk.Scale(self.main_frame, from_=1, to=300, variable=self.epochs, orient="horizontal", command=self.update_epoch_label).pack(pady=5)

        # Image size tuning
        ttk.Label(self.main_frame, text="Image Size").pack()
        ttk.Combobox(self.main_frame,textvariable=self.imgsz,values=[416, 512, 640, 832, 1024],state="readonly").pack(pady=5)

        # Dataset preparation split
        self.train_split_label = ttk.Label(self.main_frame, text=f"Train/Val Split: {float(self.train_split.get()):.2f} / {1.0 - float(self.train_split.get()):.2f}")
        self.train_split_label.pack()
        ttk.Scale(self.main_frame,from_=0.5,to=0.95,variable=self.train_split,orient="horizontal", command=self.update_train_split_label).pack(pady=5)

        ttk.Button(self.main_frame, text="Prepare YOLO Dataset", command=self.prepare_yolo_dataset, width=35).pack(pady=5)
        ttk.Button(self.main_frame, text="Select dataset.yaml", command=self.select_yaml, width=35).pack(pady=5)
        ttk.Button(self.main_frame, text="Create dataset.yaml", command=self.create_yaml_file, width=35).pack(pady=5)
        ttk.Button(self.main_frame, text="Train Model", command=self.run_training, width=35).pack(pady=15)

        self.add_status_box()

    # Deployment menu page
    def show_deployment_menu(self):
        self.page_header("Deployment")

        # CV2 camera port selector
        ttk.Label(self.main_frame, text="Camera Index").pack()
        ttk.Combobox(self.main_frame,textvariable=self.camera_index,values=[0, 1, 2, 3],state="readonly").pack(pady=5)

        # Confidence threshold tuning
        self.confidence_label = ttk.Label(self.main_frame, text=f"Confidence Threshold: {float(self.confidence.get()):.2f}")
        self.confidence_label.pack()
        ttk.Scale(self.main_frame,from_=0.05,to=1.0,variable=self.confidence,orient="horizontal", command=self.update_confidence_label).pack(pady=5)

        ttk.Button(self.main_frame, text="Select .pt Model", command=self.select_pt_model, width=35).pack(pady=5)
        ttk.Button(self.main_frame, text="Run Image Inference", command=self.run_image_inference, width=35).pack(pady=5)
        ttk.Button(self.main_frame, text="Run Live Camera Inference", command=self.run_live_inference, width=35).pack(pady=5)

        ttk.Label(self.main_frame, text="Live inferencing mode: press Q inside the camera window to exit.").pack(pady=10)

        self.add_status_box()

    # Epoch slider label update
    def update_epoch_label(self, value):
        if self.epoch_label is not None:
            self.epoch_label.config(text=f"Epochs: {int(float(value))}")

    # Train split slider label update
    def update_train_split_label(self, value):
        train_ratio = float(value)
        val_ratio = 1.0 - train_ratio

        if self.train_split_label is not None:
            self.train_split_label.config(text=f"Train/Val Split: {train_ratio:.2f} / {val_ratio:.2f}")

    # Confidence slider label update
    def update_confidence_label(self, value):
        if self.confidence_label is not None:
            self.confidence_label.config(text=f"Confidence Threshold: {float(value):.2f}")

    # yaml selection function
    def select_yaml(self):
        path = filedialog.askopenfilename(filetypes=[("YAML files", "*.yaml")])

        if path == "":
            return

        self.dataset_yaml.set(path)
        self.log_status(f"Dataset YAML loaded: {path}")

    # YOLO pytorch model select function
    def select_pt_model(self):
        path = filedialog.askopenfilename(filetypes=[("PyTorch model", "*.pt")])

        if path == "":
            return

        self.pt_model_path.set(path)
        self.deployment.load(path)

        self.log_status(f"Loaded model: {path}")

    # User selects dataset folder, label folders, output folder
    def run_augmentation(self):
        image_dir = filedialog.askdirectory(title="Select image folder")
        label_dir = filedialog.askdirectory(title="Select label folder")
        output = filedialog.askdirectory(title="Select output folder")

        if image_dir == "" or label_dir == "" or output == "":
            return

        self.log_status("Starting augmentation...")

        self.augmentation.augment(
            image_dir,
            label_dir,
            output,
            flip=self.flip.get(),
            brightness=self.brightness.get()
        )

        self.log_status("Augmentation finished.")

    # When user runs bounding box function
    def run_bbox_annotation(self):
        image_dir = filedialog.askdirectory(title="Select image folder")
        label_dir = filedialog.askdirectory(title="Select label folder")
        self.annotation.bbox_anno(image_dir, label_dir, self.class_names)

    #  When user runs segmentation function
    def run_segmentation_annotation(self):
        image_dir = filedialog.askdirectory(title="Select image folder")
        label_dir = filedialog.askdirectory(title="Select label folder")
        self.annotation.seg_anno(image_dir, label_dir, self.class_names)

    # When users runs training
    def run_training(self):
        if self.dataset_yaml.get() == "":
            messagebox.showerror("Training Error", "Please select or create a dataset.yaml file first.")
            return

        train_thread = threading.Thread(target=self.training_thread)
        train_thread.daemon = True
        train_thread.start()

    # When users runs still single image detection
    def run_image_inference(self):
        if self.deployment.model is None:
            messagebox.showerror("Model Error", "Please select a .pt model first.")
            return

        image_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])

        if image_path == "":
            return

        self.deployment.image_infer(
            image_path,
            confidence=float(self.confidence.get())
        )

    # User enters custom class names for annotation
    def enter_class_names(self):
        class_window = tk.Toplevel(self.root)
        class_window.title("Enter Class Names")
        class_window.geometry("350x400")

        # Scrollable class name window
        class_canvas = tk.Canvas(class_window)
        class_canvas.pack(side="left", fill="both", expand=True)

        class_scrollbar = ttk.Scrollbar(class_window, orient="vertical", command=class_canvas.yview)
        class_scrollbar.pack(side="right", fill="y")

        class_canvas.configure(yscrollcommand=class_scrollbar.set)

        class_frame = ttk.Frame(class_canvas)
        class_canvas.create_window((0, 0), window=class_frame, anchor="nw")

        def update_class_scroll_region(event):
            class_canvas.configure(scrollregion=class_canvas.bbox("all"))

        def class_mousewheel_scroll(event):
            class_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        class_frame.bind("<Configure>", update_class_scroll_region)
        class_canvas.bind("<MouseWheel>", class_mousewheel_scroll)

        entries = []

        for i in range(self.class_count.get()):
            ttk.Label(class_frame, text=f"Class {i} Name").pack()
            entry = ttk.Entry(class_frame)
            entry.pack(pady=5)
            entries.append(entry)

        def save_classes():
            self.class_names = []

            for entry in entries:
                name = entry.get()

                if name != "":
                    self.class_names.append(name)

            print("Classes saved:", self.class_names)
            self.log_status(f"Classes saved: {self.class_names}")
            class_window.destroy()

        ttk.Button(class_frame, text="Save Classes", command=save_classes).pack(pady=10)

    # Create YOLO dataset yaml file
    def create_yaml_file(self):
        dataset_path = filedialog.askdirectory(title="Select dataset root folder")

        if dataset_path == "":
            return

        if len(self.class_names) == 0:
            messagebox.showerror("Class Error", "Please enter class names first.")
            return

        yaml_path = self.annotation.yaml(dataset_path, self.class_names)
        self.dataset_yaml.set(yaml_path)

        self.log_status(f"dataset.yaml created: {yaml_path}")
        messagebox.showinfo("YAML Created", f"dataset.yaml created at:\n{yaml_path}")

    # Prepare dataset folder for YOLO training
    def prepare_yolo_dataset(self):
        if len(self.class_names) == 0:
            messagebox.showerror("Class Error", "Please enter class names first.")
            return

        image_dir = filedialog.askdirectory(title="Select annotated image folder")
        label_dir = filedialog.askdirectory(title="Select annotation label folder")
        output_dataset_path = filedialog.askdirectory(title="Select output YOLO dataset folder")

        if image_dir == "" or label_dir == "" or output_dataset_path == "":
            return

        self.log_status("Preparing YOLO dataset...")

        yaml_path = self.annotation.prepare_dataset(
            image_dir,
            label_dir,
            output_dataset_path,
            self.class_names,
            train_split=float(self.train_split.get())
        )

        self.dataset_yaml.set(yaml_path)

        self.log_status(f"YOLO dataset prepared: {yaml_path}")
        messagebox.showinfo("Dataset Ready", f"Dataset prepared successfully:\n{yaml_path}")

    # Status log handler
    def log_status(self, message):
        self.root.after(0, self._log_status_safe, message)

    # Thread safe status log handler
    def _log_status_safe(self, message):
        if self.status_box is not None:
            self.status_box.insert(tk.END, message + "\n")
            self.status_box.see(tk.END)
        else:
            print(message)

    # Training thread handler
    def training_thread(self):
        self.log_status("Training started...")
        self.log_status(f"Training YAML: {self.dataset_yaml.get()}")
        self.log_status(f"Model: {self.model_choice.get()}")
        self.log_status(f"Epochs: {int(self.epochs.get())}")
        self.log_status(f"Image Size: {int(self.imgsz.get())}")

        try:
            console_redirector = ConsoleRedirector(self.log_status)

            with contextlib.redirect_stdout(console_redirector), contextlib.redirect_stderr(console_redirector):
                self.training.training(
                    model_name=self.model_choice.get(),
                    dataset_yaml=self.dataset_yaml.get(),
                    epochs=int(self.epochs.get()),
                    imgsz=int(self.imgsz.get())
                )

            console_redirector.flush()
            self.log_status("Training finished.")

        except Exception as error:
            self.log_status(f"Training error: {error}")
            messagebox.showerror("Training Error", str(error))

    # When users runs live camera detection
    def run_live_inference(self):
        if self.deployment.model is None:
            messagebox.showerror("Model Error", "Please select a .pt model first.")
            return

        messagebox.showinfo("Live Camera Inference", "The camera window will open now.\n\nPress Q inside the camera window to exit live inferencing mode.")

        live_thread = threading.Thread(target=self.live_inference_thread)
        live_thread.daemon = True
        live_thread.start()

    # Live inference thread handler
    def live_inference_thread(self):
        self.log_status("Live camera inference started. Press Q inside the camera window to exit.")
        self.deployment.camer_infer(camera_index=int(self.camera_index.get()),confidence=float(self.confidence.get()))

        self.log_status("Live camera inference closed.")


# run the main loop to launch Program
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
