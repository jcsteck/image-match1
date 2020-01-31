# Compare an image with every frame of a video to find the best match
import PySimpleGUI as sg
import os
import operator
import time
import datetime
import warnings
import cv2
import pdb
from datetime import date




from sys import stdout


from skimage import color
from skimage import measure


#record start time
start = time.process_time()

#ignore non-contiguous skimage warning
warnings.filterwarnings("ignore", module="skimage")
     
window = sg.Window('title', [[sg.Text('Screenshot')], [sg.Input(key='_imgfile_'), sg.FileBrowse()], [sg.Text('Video')], [sg.Input(key='_vidfile_'), sg.FileBrowse()], [sg.Text('All video in folder')], [sg.Input(key='_folderpath_'), sg.FolderBrowse()], [sg.Text('Save results to')], [sg.Input(key='_resultspath_'), sg.FolderBrowse()],[sg.Text('Matches')], [sg.Slider(range=(1, 10), orientation='h', size=(34, 20), default_value=1, key=('_matchesn_'))], [sg.CButton('Ok'), sg.CButton('Cancel')],  ])
event, values = window.read()
print(values['_imgfile_'])
imagefile= values['_imgfile_']
videofile= values['_vidfile_']
videodir= values['_folderpath_']
resultPath= values['_resultspath_']
matchesnumber= int(values['_matchesn_'])
print(imagefile + ' ' + videofile)

def get_filename_datetime():
    # Use current date to get a text file name.
    return "Frame Search results-" + str(date.today()) + ".txt"
name = get_filename_datetime()
print("NAME", name)

path = resultPath + "/" + name
print("PATH", path)

def prepare_image(filename):
    #open still image as rgb
    img = cv2.imread(filename, cv2.IMREAD_COLOR)
    #shrink
    img = cv2.resize(img, (10, 10))
    #convert to b&w
    img = color.rgb2gray(img)
    return img


def best_match(similarities):
    d = max(similarities, key=lambda x:x['similarity'])
    best_frame_number = d['frame']
    best_similarity = d['similarity']
    return best_frame_number, best_similarity


def parse_video(image, video, n_matches, break_point=False, verbose=False):
    #iterate through video frames
    
    similarities = [{'frame': 0, 'similarity': 0}]
    frame_count = 0
    
    #get current time
    fps_time = time.process_time()

    cap = cv2.VideoCapture(video)
    while(cap.isOpened()):

        ret, frame = cap.read()

        #break at EOF
        if (type(frame) == type(None)):
            break

        #increment frame counter
        frame_count += 1
        

        #resize current video frame
        small_frame = cv2.resize(frame, (10, 10))
        #convert to greyscale
        small_frame_bw = color.rgb2gray(small_frame)

        #compare current frame to source image
        similarity = measure.compare_ssim(image, small_frame_bw)

        #remember current frame details
        similarities.append({'frame'      : frame_count,
                             'similarity' : similarity,
                             'image'      : frame})

        #find best match overall
        best_frame_number, best_similarity = best_match(similarities)
        
        #sort similarities list
        similarities = sorted(similarities, key=operator.itemgetter('similarity'), reverse=True)
        #remove surplus entries
        similarities = similarities[:n_matches]

        #calculate fps
        fps = frame_count / (time.process_time() - fps_time)

        #feedback to cli
        stdout.write('\r@ %d [%sfps] | best: %d (%s)  \r'
            % (frame_count, int(round(fps)), best_frame_number, round(best_similarity, 4), ))
        stdout.flush()

        #handle break_point
        if break_point:
            if similarity >= break_point:
                return similarities

    cap.release()
    return similarities



def sort_results(results, output=False):
    #sort results
    print('\n')
    sorted_results = sorted(results, key=operator.itemgetter('similarity'), reverse=True)
    n = 0
    print('\n--results:')
    for res in sorted_results:
        n += 1
        print('#%s\t%s\t%s\t: %s' % (n, res['filename'], res['frame'], res['similarity']))

        #save matched frames
        if output:
            save_frame(output, n, res['image'])


def save_frame(filename, n, image):
    fn, ext = filename.split('.')
    fn = '%s_%s.%s' % (fn, n, ext)
    cv2.imwrite(fn, image)


def walk(source_image, directory, number=1, break_point=False):
    results = []
    extentions = ['mp4', 'avi', 'mov', 'mkv', 'm4v']
    for root, dirs, files in os.walk(directory):
        for file in files:
            for ext in extentions:
                if file.endswith(ext):
                    video_fn = (os.path.join(root, file))
                    print(video_fn)
                    similarities = parse_video(source_image,
                                               video_fn,
                                               n_matches=number,
                                               break_point=break_point)
                     
                    #flatten results
                    for d in similarities:
                        results.append({'filename'   : video_fn,
                                        'frame'      : d['frame'],
                                        'similarity' : d['similarity'],
                                        'image'      : d['image']})

                        #stop walk if break point achieved
                        if break_point:
                            if d['similarity'] >= break_point:
                                return results

    return results

def main():
    import argparse

    #define cli arguments
    parser = argparse.ArgumentParser(description='''
        Compare an image with every frame of a video
        to find the best match.

        ============================================
        Edward Anderson
        --------------------------------------------
        v0.1 | 2016
        ''', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--image', help='source image')
    parser.add_argument('-v', '--video', help='video to search inside')
    parser.add_argument('-n', '--number', help='number of best matches to return', type=int, default=1)
    parser.add_argument('-b', '--break_point', help='stop searching when frame with [break_point] accuracy found; a number between 0 and 1', type=float, default=0.95)
    parser.add_argument('-o', '--output', help='filename.ext for best match; saved files are appended with "_n.ext"')
    parser.add_argument('-d', '--directory', help='directory of videos', default=videodir)
    args = parser.parse_args()

    #check source and destination provided


    #prepare image
    source_image = prepare_image(imagefile)
    if resultPath == "":
        sg.Popup('Error', 'Did you pick a folder for to save the report?')
        exit()
    #either walk directory or hande single file
    if args.directory:
        #scan directory and process each video file
        print('\n--reading videos:')
        results = walk(source_image, args.directory, matchesnumber, args.break_point)
        s_results = sort_results(results, args.output)
        
        
    else:
        #process single video file
        print('\n--reading video:')
        similarities = parse_video(source_image,
                                   videofile,
                                   n_matches=matchesnumber,
                                   break_point=args.break_point)

        print('\n\n--results:')
        #results to cli
        n = 0
        with open(path, "w+") as dateLog:
            dateLog.write(str(date.today()))
        for d in similarities:
            n += 1
            print('#%s\t%s\t: %s' % (n, d['frame'], d['similarity']))
            with open(path, "a") as resultsLog:
                # Write data to file.
                resultsLog.write('\n' + str(videofile) + '\n' + ('#%s\t%s\t: %s' % (n, d['frame'], d['similarity'])))
            matchExport = str(d['frame']) + ".jpg"

            
            #save matched frames
            save_frame(resultPath + "/" + matchExport, n, d['image'])

    seconds_taken = time.process_time() - start
    time_taken = str(datetime.timedelta(seconds=seconds_taken))
    print('\n--time taken: \n%s\n' % time_taken)

print("NAME", name)
print("PATH", path)
if __name__ == '__main__':
    main()