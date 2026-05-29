This program creates a GUI (General user interface) that combines all the pipeline processes of computer vision development into one application

This program lets users Augment datasets (limited augmentation options in this version), Annotate dataset images with either bounding boxes or segmentation, prepare training,
validation, and labels for the user, available YOLOv11 models training with epochs toggle, and trained model deployment testing environment.

The main purpose behind this project is create a practical prototype app that can assist people with the whole computer vision development process with no coding needed.
It beats opening up your IDE, or opening a 3rd party annotation tool URL, when you can do everythin in one place.

If you have some backend understanding of YOLO or computer vision development then you shouldn't have too much problem operating this software, also I publish my source
code for this entire project so feel free to read or modiffy it to your liking. If you dont understand how the pipeline works, google or youtube should have plenty of
sources to help give you an understanding

FOR PROGRAMMERS:
The program is broken into 6 classes:
1.) Augmentation
2.) Annotation
3.) Training
4.) Deployment
5.) GUI Logging
6.) Application

The main loop simply just calls upom these classes when using application class as an object
