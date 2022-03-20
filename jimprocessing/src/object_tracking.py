#!/usr/bin/env python
# References:
# ROS cv_bridge sample code
# https://github.com/trunc8/ball-tracking-opencv-and-ros
# https://www.instructables.com/Automatic-Vision-Object-Tracking/
# OpenCV Contour Features Documentation -- also cite OpenCV
# taredevarsh and opencv tutorial on z distance

from __future__ import print_function
import roslib
import sys
import rospy
import cv2
from std_msgs.msg import String, Int32
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import CompressedImage
import numpy as np
import imutils

class image_converter:

    def __init__(self):
        #self.image_pub = rospy.Publisher("image_topic_2", Image)
        self.gripper_pub = rospy.Publisher("gripper_angle", Int32)
        self.elbow_pub = rospy.Publisher("elbow_angle", Int32)
        self.bridge = CvBridge()
        self.image_sub = rospy.Subscriber(
            "/raspicam_node/image/compressed", CompressedImage, self.callback)
        print("<< Subscribed to topic /raspicam_node/image")


    def callback(self, data):
        try:
            cv_image = self.bridge.compressed_imgmsg_to_cv2(data, "bgr8")
            cv_image = cv2.flip(cv_image, 0)
        except CvBridgeError as e:
            print(e)

        mask_img = self.getMaskedImage(cv_image)
        rectangle=None
        imwidth = None
        box_width = 4.5 # cm
        focal_length = 360 
        contours, hierarchy = cv2.findContours(mask_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        center = None
        closeConfirmed = False
        gripper_open_angle = 180
        gripper_close_angle = 130
        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            ((xc,yc), radius) = cv2.minEnclosingCircle(c)
            if radius > 10:
                rectangle = cv2.minAreaRect(c)
                x,y,w,h = cv2.boundingRect(c)
                cv2.rectangle(cv_image,(x,y),(x+w,y+h),(0,255,0),2)
                centerx, centery = x+(w//2), y+(h//2)
                center = (centerx, centery)
                cv2.circle(cv_image, center, 3, (0, 0, 255), -1)
                imwidth = abs(rectangle[1][0])#px
                area=round(rectangle[1][0]*rectangle[1][1])
                dist = round((box_width*focal_length/rectangle[1][0])*0.8,1)
                coords = (x,y,dist)
                text = str(coords) + " A = " + str(area)#'Distance from camera in cm:'+
                cv2.putText(cv_image, text,(30,20),cv2.FONT_HERSHEY_SIMPLEX, .3,(0,0,255),1,cv2.LINE_AA)
                if dist < 30 and dist > 10 and closeConfirmed == False:
                    cv2.putText(cv_image, "Open gripper",(30,50),cv2.FONT_HERSHEY_SIMPLEX, .3,(0,0,255),1,cv2.LINE_AA)
                    self.gripper_pub.publish(gripper_open_angle)
                    self.elbow_pub.publish(0)

                elif dist <= 10:
                    cv2.putText(cv_image, "Close gripper",(30,50),cv2.FONT_HERSHEY_SIMPLEX, .3,(0,0,255),1,cv2.LINE_AA)
                    # and do not allow gripper to open again bc we confirmed a close distance
                    closeConfirmed = True
                    self.gripper_pub.publish(gripper_close_angle)
                    self.elbow_pub.publish(180)
            # Sometimes when the object is too close the image recognition fails; so close gripper in these instances 
            else: # object not detected but other contours detected
                cv2.putText(cv_image, "Close gripper",(30,50),cv2.FONT_HERSHEY_SIMPLEX, .3,(0,0,255),1,cv2.LINE_AA)
                self.gripper_pub.publish(gripper_close_angle)

                
        else: # no contours detected
            cv2.putText(cv_image, "Close gripper",(30,50),cv2.FONT_HERSHEY_SIMPLEX, .3,(0,0,255),1,cv2.LINE_AA)
            #self.gripper_pub.publish(gripper_close_angle)
	# Show video stream of blue box with circle around it
        imS = cv2.resize(cv_image, (400, 400))  		     
        cv2.imshow("blue box live feed", imS)
        cv2.waitKey(3)
        # try:
        #     self.image_pub.publish(self.bridge.cv2_to_imgmsg(cv_image, "bgr8"))
        # except CvBridgeError as e:
        #     print(e)
#        self.gripper_pub.publish(gripper_open_angle)        

    def getMaskedImage(self, cv_image):
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        colorLower = (94, 100, 100)
        colorUpper = (114, 255, 255)
        mask = cv2.inRange(hsv, colorLower, colorUpper)
        return mask
    
def main(args):
    rospy.init_node('image_converter', anonymous=True)
    
    rate = rospy.Rate(150)
    ic = image_converter()
    try:
        rospy.spin()
    except KeyboardInterrupt:
        print("Shutting down")
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main(sys.argv)