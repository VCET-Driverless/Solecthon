import cv2
import numpy as np
import math

path = "http://192.168.43.156:4747/video"
cap = cv2.VideoCapture('video.mp4')

# Laptop camera 
pt = [(0,100), (-600,416), (416,100), (1016,416)]

LIMIT_CONE = 230+30-30

mid_c = 80-5
# intel camera 
#pt = [(0,225), (-1500,500), (600,225), (2100,500)]

car_coor = (208,450-5)

def angle(p1, p2):
    x, y = p1
    p, q = p2
    try:
        slope = (q - y)/(p - x)
    except:
        slope = 99999
    angle = np.arctan(slope)*180/math.pi
    if(angle > 0):
        return -1*(90 - angle)
    return (90 + angle)

def coneDetect(frame):
    frame = cv2.resize(frame, (416, 416))
    img_HSV = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    img_thresh_low = cv2.inRange(img_HSV, np.array([0, 135, 135]),np.array([15, 255, 255]))  # everything that is included in the "left red"

    img_thresh_high = cv2.inRange(img_HSV, np.array([159, 135, 135]), np.array([179, 255, 255]))  # everything that is included in the "right red"
                                 
    img_thresh_mid = cv2.inRange(img_HSV, np.array([100, 150, 0]),np.array([140, 255, 255]))  # everything that is included in the "right red"
                                 
    img_thresh = cv2.bitwise_or(img_thresh_low, img_thresh_mid)  # combine the resulting image
    img_thresh = cv2.bitwise_or(img_thresh, img_thresh_high)
    kernel = np.ones((5, 5))
    img_thresh_opened = cv2.morphologyEx(img_thresh, cv2.MORPH_OPEN, kernel)
    img_thresh_blurred = cv2.medianBlur(img_thresh_opened, 5)
    img_edges = cv2.Canny(img_thresh_blurred, 80, 160)
    contours, _ = cv2.findContours(np.array(img_edges), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_contours = np.zeros_like(img_edges)
    cv2.drawContours(img_contours, contours, -1, (255, 255, 255), 2)
    approx_contours = []

    for c in contours:
        approx = cv2.approxPolyDP(c, 10, closed=True)
        approx_contours.append(approx)
    img_approx_contours = np.zeros_like(img_edges)
    cv2.drawContours(img_approx_contours, approx_contours, -1, (255, 255, 255), 1)
    all_convex_hulls = []
    for ac in approx_contours:
        all_convex_hulls.append(cv2.convexHull(ac))
    img_all_convex_hulls = np.zeros_like(img_edges)
    cv2.drawContours(img_all_convex_hulls, all_convex_hulls, -1, (255, 255, 255), 2)
    convex_hulls_3to10 = []
    for ch in all_convex_hulls:
        if 3 <= len(ch) <= 10:
            convex_hulls_3to10.append(cv2.convexHull(ch))
    img_convex_hulls_3to10 = np.zeros_like(img_edges)
    cv2.drawContours(img_convex_hulls_3to10, convex_hulls_3to10, -1, (255, 255, 255), 2)


    def convex_hull_pointing_up(ch):
        '''Determines if the path is directed up.
        If so, then this is a cone. '''

        # contour points above center and below

        points_above_center, points_below_center = [], []

        x, y, w, h = cv2.boundingRect(ch)  # coordinates of the upper left corner of the describing rectangle, width and height
        aspect_ratio = w / h  # ratio of rectangle width to height

        # if the rectangle is narrow, continue the definition. If not, the circuit is not suitable
        if aspect_ratio < 0.8:
	# We classify each point of the contour as lying above or below the center	
            vertical_center = y + h / 2

            for point in ch:
                if point[0][
                    1] < vertical_center:  # if the y coordinate of the point is above the center, then add this point to the list of points above the center
                    points_above_center.append(point)
                elif point[0][1] >= vertical_center:
                    points_below_center.append(point)

            # determine the x coordinates of the extreme points below the center
            left_x = points_below_center[0][0][0]
            right_x = points_below_center[0][0][0]
            for point in points_below_center:
                if point[0][0] < left_x:
                    left_x = point[0][0]
                if point[0][0] > right_x:
                    right_x = point[0][0]

            # check if the upper points of the contour lie outside the "base". If yes, then the circuit does not fit
            for point in points_above_center:
                if (point[0][0] < left_x) or (point[0][0] > right_x):
                    return False
        else:
            return False

        return True


    cones = []
    bounding_rects = []
    for ch in convex_hulls_3to10:
        if convex_hull_pointing_up(ch):
            cones.append(ch)
            rect = cv2.boundingRect(ch)
            bounding_rects.append(rect)
    img_res = frame.copy()
    cv2.drawContours(img_res, cones, -1, (255, 255, 255), 2)
    transf = np.zeros([450, 600, 3])

    for rect in bounding_rects:
        #print('previous', rect[0], rect[1], rect[2], rect[3])
        cv2.rectangle(img_res, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (1, 255, 1), 6)
        cv2.circle(img_res,(rect[0], rect[1]), 5, (0,200,255), -1)
        cv2.circle(img_res,(rect[0] + rect[2], rect[1] + rect[3]), 5, (0,200,255), -1)
        cv2.circle(img_res,(rect[0] + rect[2]//2, rect[1] + rect[3]), 5, (255,255,255), -1)

    return bounding_rects, img_res

def inv_map(frame):
    pts1 = np.float32([pt[0],pt[1],pt[2],pt[3]])
    pts2 = np.float32([[0,0],[0,416],[416,0],[416,416]])
    M = cv2.getPerspectiveTransform(pts1,pts2)
    image = cv2.warpPerspective(frame,M,(416,416), flags=cv2.INTER_LINEAR)
    #cv2.imshow('itshouldlookfine!', image)
    return image, M

def inv_coor(bounding_rects, M, image):
    mybox = []
    for detection in bounding_rects:

        xmax = detection[0]
        xmin = detection[1]
        ymax = detection[2]
        ymin = detection[3]
        #print( ((xmax+xmin)//2), (ymax) )
        pt1 = (int(xmin), int(ymin))
        pt2 = (int(xmax), int(ymax))
        cv2.circle(image,pt1, 5, (255,255,255), -1)
        cv2.circle(image,pt2, 5, (255,255,255), -1)
    #for rect in bounding_rects:
        a = np.array([[( (xmax+xmin)//2 ), (ymax//1)]], dtype='float32')
        a = np.array([a])
        pointsOut = cv2.perspectiveTransform(a, M)
        box = pointsOut[0][0][0], pointsOut[0][0][1]
        mybox.append(box)
        #print(pointsOut)
    #mybox = sorted(mybox, key=lambda k:(k[1], k[0])).copy()
    #mybox.reverse()
    #abc = sorted(mybox, key=last)
    print('boxall', mybox)
    return mybox , image

def st_line( a, b, c, x, y ):
    if( a*x + b*y + c < 0 ):
        return True# True means left side for left turn
    return False

def pathplan(mybox, str_ang):
    left_box = []
    right_box = []
    left_count = 5
    right_count = 5

    for i in range(len(mybox)):
        x, y = mybox[i]
        if( str_ang == '3' or str_ang == '4' or  str_ang == '5' ):
            if(x < 208):
                if(left_count > 0):
                    left_box.append(mybox[i])
                    left_count = left_count - 1

            else:
                if(right_count > 0):
                    right_box.append(mybox[i])
                    right_count = right_count - 1

        elif( str_ang == '0' or str_ang == '1' or str_ang == '2'):
            lim_coor = 104
            if( x < ((y + 416)/4) ):
                if(left_count > 0):
                    left_box.append(mybox[i])
                    left_count = left_count - 1
            else:
                if(right_count > 0):
                    right_box.append(mybox[i])
                    right_count = right_count - 1

        elif( str_ang == '6' or str_ang == '7' or str_ang == '8' ):
            if( x > ((1248 - y)/4) ):
                if(right_count > 0):
                    right_box.append(mybox[i])
                    right_count = right_count - 1

            else:
                if(left_count > 0):
                    left_box.append(mybox[i])
                    left_count = left_count - 1


	
    #############################################################################
    left_box.sort(reverse = True)
    right_box.sort(reverse = True)

    left_box =  sorted(left_box, key=lambda k:(k[1], k[0])).copy()
    right_box = sorted(right_box, key=lambda l:(l[1], l[0])).copy()
    '''left_box.sort()
    right_box.sort()'''
    #############################################################################
    ############################### path planning ###############################
    #############################################################################
    try:
        if(left_box[-1][1] < LIMIT_CONE):
            left_box.clear()
    except:
        print('Left Exception in pathplan function.............')
            
    try:
        if(right_box[-1][1] < LIMIT_CONE):
            right_box.clear()
    except:
        print('Right Exception in pathplan function.............')
    #############################################################################
    
    lines = []
    lines.append(car_coor)


    if( len(left_box) == 0 and len(right_box) == 0 ):
        lines.append((208,350))
         
    elif( len(left_box) == 0 and len(right_box) != 0 ):
        for i in range(len(right_box)):
            #print( 'test1' )
            x, y = right_box[i]
            x = x - mid_c
            lines.append( (int(x), int(y)) )
        
    elif( len(left_box) != 0 and len(right_box) == 0 ):
        for i in range(len(left_box)):
            #print( 'test2' )
            x, y = left_box[i]
            x = x + mid_c
            lines.append( (int(x), int(y)) )
        
    elif( len(left_box) != 0 and len(right_box) != 0 ):

        small_len  = 0
        left_box = left_box[::-1].copy()
        right_box = right_box[::-1].copy()
        if(len(left_box) > len(right_box)):
            small_len = len(right_box)
        else:
            small_len = len(left_box)
        
        for i in reversed(range(small_len)):
                #print( 'test3' )
                x, y = tuple(np.add((right_box[i]), (left_box[i])))
                x = x//2
                y = y//2
                #cv2.circle(transf,(int(x), int(y)), 5, (255,0,255), -1) 	# Filled
                lines.append( (int(x), int(y)) )

        left_box = left_box[::-1].copy()
        right_box = right_box[::-1].copy()

    lines = sorted(lines, key=lambda m:(m[1], m[0])).copy()
    #print(len(left_box), len(right_box))
    
    return left_box[::-1], right_box[::-1], lines[::-1]

def pathbana(lines, inv_image):
    for i in range(len(lines) - 1):
        cv2.circle(inv_image,lines[i], 5, (0,0,0), -1) 	# Filled
        #print( 'test4' )
        inv_image = cv2.line(inv_image,lines[i],lines[i+1],(255,255,0),4)
    '''if(angle(lines[0], lines[1]) > 75 or angle(lines[0], lines[1]) < -75):
        lines.remove(1)'''
	
    #print( lines[0], lines[1] , angle(lines[0], lines[1]) )

    return inv_image