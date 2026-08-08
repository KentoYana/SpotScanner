# This is a Python script of the SpotScanner,  written by Kento Yanagisawa.
# Import libraries
import argparse
import csv
import datetime
import glob
import os
import os.path
import shutil
import subprocess
import sys
from pathlib import Path
from . import __version__

BIBTEX_ENTRY = (
    "@Manual{spotscanner,\n"
    "  title  = {SpotScanner: A tool to recognize and analyze images of spot-test plates in fungal genetics},\n"
    "  author = {Kento Yanagisawa},\n"
    "  year   = {2025},\n"
    f"  note   = {{version {__version__}}},\n"
    "  url    = {https://github.com/KentoYana/spotscanner},\n"
	"  abstract  = {SpotScanner is a command-line tool for quantitative analysis of fungal spot-test plates. It detects a printed marker on the plate, segments the image into a fixed grid, and measures colony growth in each spot, outputting results as CSV files and diagnostic images. The tool is designed for use in fungal genetics experiments (e.g., \\textit{Neurospora} spot tests) with either multi-channel replicators or manual pipetting.},\n"
    "}\n"
)

def _resource_root():
    """Return the root containing marker/ and template/ resources.

    Environment variables retain the 7.x portable-layout override. Installed
    8.x packages use resources shipped inside the Python package.
    """
    env_root = os.environ.get("SPOTSCANNER_ROOT") or os.environ.get("SPOTSCANNER")
    if env_root:
        return Path(env_root).expanduser().resolve()

    packaged_root = Path(__file__).resolve().parent / "resources"
    if packaged_root.is_dir():
        return packaged_root

    # Compatibility fallback for running an unbuilt 7.x-style source tree.
    return Path(__file__).resolve().parent.parent


bin_dir = str(_resource_root())

# Function definition
def SpotScaner_single(plate_img, threshold10, main_dir, input_time, analyze_mode):
    import cv2
    import numpy as np

    file = glob.glob(plate_img)
    if len(file) == 0:
        print('Error: could not find the specified image in this directory.')
        print('')
        sys.exit()
    threshold = threshold10 / 10
    img_dir = os.path.dirname(plate_img)
    os.chdir(img_dir)
    img_name = os.path.splitext(os.path.basename(plate_img))[0]
    img_name2 = os.path.basename(plate_img)
    output_message = '> Analyzing ' + img_name2
    print(output_message)
    marker_dir = os.path.join(main_dir, 'marker')
    img_raw = cv2.imread(plate_img)  # Import an experimental result
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
    mkr_list = [
        'Marker16.png',
		'Marker15.png',
        'Marker14.png',
        'Marker13.png',
        'Marker12.png',
        'Marker11.png',
		'Marker10.png',
        'Marker9.png',
        'Marker8.png',
        'Marker7.png',
        'Marker6.png',
        'Marker5.png',
        'Marker4.png',
        'Marker3.png',
        'Marker2.png',
        'Marker1.png',
        'Nothing'
    ]
    for try_mkr in mkr_list:
        if try_mkr == 'Nothing':
            print('---> Error: could not find any markers in the image.')
            print('---------------------')
            return img_name2
        else:
            try:
                mkr_path = os.path.join(marker_dir, try_mkr)
                mkr = cv2.imread(mkr_path, 0)  # Import a marker image
                res = cv2.matchTemplate(img, mkr, cv2.TM_CCOEFF_NORMED)  # Get coordinate of marker in the result
                loc = np.where(res >= threshold)  # Trim coordinates less than threshold
                mark_area = {}
                mark_area['top_x'] = min(loc[1])  # Get x-coordinate of the north-west
                mark_area['top_y'] = min(loc[0])  # Get y-coordinate of the north-west
                mark_area['bottom_x'] = max(loc[1])  # Get x-coordinate of south-east
                mark_area['bottom_y'] = max(loc[0])  # Get y-coordinate of south-east
                img = img[mark_area['top_y']:mark_area['bottom_y'], mark_area['top_x']:mark_area['bottom_x']]
            except ValueError:
                pass
            else:
                output_message = '---> ' + os.path.splitext(os.path.basename(try_mkr))[0] + ' Match!!!'
                print(output_message)
                break
    res, img = cv2.threshold(img, 50, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Convert the image to black and white image with 50 as threshold
    res_name = img_name + '_converted.png'
    try:
        # Invert the converted image for print
        img_inverted = cv2.bitwise_not(img)
        cv2.imwrite(res_name, img_inverted)  # Output Converted image after Inverted
    except cv2.error:
        print('---> Error: could not crop the image.')
        print('---------------------')
        return img_name2
    else:
        output_message = '---> Output' + ' ' + res_name
        print(output_message)
    if analyze_mode == 'replicator':  # Spot-test with Replicator (8*12 matrix)
        n_col = 12  # Number of spots per column
        n_row = 8  # Number of spots per row
    if analyze_mode == 'pipette':  # Spot-test with Pipette (4*6 matrix)
        n_col = 6  # Number of spots per column
        n_row = 4  # Number of spots per row
    margin_top = 1  # Number for north-west marker's row
    n_row = n_row + margin_top  # Number of spots per row + north-west marker's row
    img = cv2.resize(img, (n_col * 100, n_row * 100))  # Resize based on the number of matrices
    csv_name_time = img_name + '_results.csv'  # Make CSV file for data collection
    result_csv = os.path.join(img_dir, csv_name_time)
    with open(result_csv, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Time', 'Image', 'Threshold', 'row', 'column', 'Colony'])
    csv_raw = []
    for row in range(margin_top, n_row):  # Analyze in order from the top row
        # col_1 = 12 * (row - 1)
        for col in range(n_col):  # Analyze in order from the leftmost column
            colony_position = col + 1
            tmp_img = img[row * 100:(row + 1) * 100, col * 100:(col + 1) * 100]  # Cut out one spot area
            whole_area = tmp_img.size  # Get the number of pixels in the entire cropped spot area
            white_area = cv2.countNonZero(tmp_img) / whole_area * 100
            # Get the number of pixels in the white area that the area covered by the colony
            csv_raw.append([input_time.strftime('%Y-%m-%d %H:%M:%S'),
                            img_name,
                            threshold10,
                            row,
                            colony_position,
                            round(white_area, 2)
                            ])
    with open(result_csv, 'a') as f:
        writer = csv.writer(f)
        writer.writerows(csv_raw)
    csv_path, csv_name = os.path.split(result_csv)
    output_message = '---> Summarize results & Output ' + csv_name
    print(output_message)
    print('---------------------')

def SpotScaner_multi(plate_dir, threshold, main_dir, input_time, analyze_mode):
    img_ext = ['*.jpg', '*.JPG', '*.jpeg']
    files = []
    for ext in img_ext:
        path = os.path.join(plate_dir, ext)
        files.extend(glob.glob(path))
    if len(files) == 0:
        print('Error: could not find any images (*.jpg / *.JPG / *.jpeg) in this directory.')
        print('')
        sys.exit()
    for file in files:
        SpotScaner_single(file, threshold, main_dir, input_time, analyze_mode)
    converted_path = os.path.join(plate_dir, 'converted_' + input_time.strftime('%Y-%m-%d_%H-%M-%S'))
    os.mkdir(converted_path)
    move_img_list = glob.glob('./*_converted.png')
    for item in move_img_list:
        item = item.replace('./', '')
        moved_file_path = os.path.join(converted_path, item)
        shutil.move(item, moved_file_path)
    csv_path = os.path.join(plate_dir, 'results_' + input_time.strftime('%Y-%m-%d_%H-%M-%S'))
    os.mkdir(csv_path)
    move_csv_list = glob.glob('./*_results.csv')
    for item in move_csv_list:
        item = item.replace('./', '')
        moved_file_path = os.path.join(csv_path, item)
        shutil.move(item, moved_file_path)

# Command line setting
def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="spotscanner",
        epilog='For more detailed documentation, run "spotscanner --readme".'
    )
    mode = parser.add_mutually_exclusive_group()
    image = parser.add_mutually_exclusive_group()
    parser.add_argument('-v', '--version', 
                        action='store_true',
                        help="Show version information and citation, then exit."
                        )
    parser.add_argument('-e', '--example', 
                        action='store_true',
                        help="Show usage examples and exit."
                        )
    parser.add_argument('-r', '--readme',
                        action='store_true',
                        help='View the SpotScanner manual.'
                        )
    parser.add_argument('-o', '--output', 
                        choices=['manual', 'marker-pdf', 'marker-tex', 'citation'],
                        help=(
                            'Output auxiliary resources: '
                            '"manual" prints the text manual; '
                            '"marker-pdf" opens the PDF file for the marker (marker.pdf); '
                            '"marker-tex" writes the LaTeX source for the marker (marker.tex); '
                            '"citation" writes a BibTeX entry (spotscanner.bib).'
                            )
                        )
    mode.add_argument('-a', '--analyze', 
                        choices=['pipette', 'replicator'],
                        help='Choose analysis mode (pipette: 4×6 matrix, replicator: 8×12 matrix).'
                        )
    image.add_argument('-s', '--single',
                        help='Analyze only the specified image.'
                        )
    image.add_argument('-m', '--multi', 
                        action='store_true',
                        help='Analyze all images in the current directory.'
                        )
    parser.add_argument('-t', '--threshold', 
                        type=int, 
                        choices=range(1, 11),
                        help='Threshold for marker recognition (default: 7).'
                        )
    
    args = parser.parse_args(argv)
    pwd = os.getcwd()
    # bin_dir = os.path.dirname(__file__)
    initial_time = datetime.datetime.now()
    
    if args.version:
        print(f'SpotScanner v{__version__}')
        print(
            "Citation: Kento Yanagisawa. "
            "SpotScanner: A tool to recognize and analyze images of spot-test plates in fungal genetics. "
            f"2025, version {__version__}."
        )
        sys.exit()
    if args.example:
        print('')
        print('Usage:')
        print('   spotscanner [-a {pipette,replicator}] [-s SINGLE | -m] [-t {1,2,3,4,5,6,7,8,9,10}]')
        print('Examples:')
        print('   spotscanner -a pipette -m')
        print('   spotscanner -a pipette -m -t 6')
        print('   spotscanner -a pipette -s spot-test.jpg')
        print('   spotscanner -a pipette -s spot-test.jpg -t 6')
        print('')
        sys.exit()
    if args.readme:
        manual_path = os.path.join(bin_dir, 'template', 'spotscanner.1')
        if not os.path.exists(manual_path):
            print(f"Error: manual file not found: {manual_path}")
            sys.exit(1)
        try:
            subprocess.run(['less', manual_path])
        except FileNotFoundError:
            try:
                with open(manual_path, "r", encoding="utf-8") as f:
                    print(f.read())
            except OSError as e:
                print(f"Error: could not read manual file {manual_path}: {e}")
                sys.exit(1)
        sys.exit()
    if args.output:
        if args.output == 'manual':
            manual_path = os.path.join(bin_dir, 'template', 'spotscanner.1')
            try:
                with open(manual_path, "r", encoding="utf-8") as f:
                    print(f.read(), end="")
            except OSError as e:
                print(f"Error: could not read manual file {manual_path}: {e}")
                sys.exit(1)
            sys.exit()
        elif args.output == 'marker-pdf':
            open_path = os.path.join(bin_dir, 'template', 'marker.pdf')
            if not os.path.exists(open_path):
                print(f"Error: marker PDF not found: {open_path}")
                sys.exit(1)
            if sys.platform == 'darwin':
                open_command = ['open', open_path]
            elif os.name == 'nt':
                open_command = ['cmd', '/c', 'start', '', open_path]
            else:
                open_command = ['xdg-open', open_path]
            try:
                subprocess.run(open_command, check=False)
            except FileNotFoundError:
                print(f"Error: no system file opener is available for {open_path}")
                sys.exit(1)
            sys.exit()
        elif args.output == 'marker-tex':
            marker_tex_path = os.path.join(bin_dir, 'template', 'marker.tex')
            if not os.path.exists(marker_tex_path):
                print(f"Error: marker TeX source not found: {marker_tex_path}")
                sys.exit(1)
            try:
                with open(marker_tex_path, "r", encoding="utf-8") as f:
                    marker_tex_src = f.read()
            except OSError as e:
                print(f"Error: could not read marker TeX source from {marker_tex_path}: {e}")
                sys.exit(1)
            out_path = os.path.join(os.getcwd(), "marker.tex")
            try:
                with open(out_path, "w", encoding="utf-8") as out:
                    out.write(marker_tex_src)
                print(f"Marker TeX source written to {out_path}")
                print("You can run `lualatex marker.tex` in this directory to generate marker.pdf.")
            except OSError as e:
                print(f"Error: could not write marker TeX file to {out_path}: {e}")
                sys.exit(1)
            sys.exit()
        elif args.output == 'citation':
            #print(BIBTEX_ENTRY)
            out_path = os.path.join(os.getcwd(), "spotscanner.bib")
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(BIBTEX_ENTRY)
                print(f"BibTeX entry written to {out_path}")
            except OSError as e:
                print(f"Error: could not write BibTeX file to {out_path}: {e}")
            sys.exit()
    if args.analyze:
        if args.analyze == 'replicator':
            print('')
            print('Analysis of spot test using a replicator (8×12 matrix)')
            print('')
            print('---------------------')
        elif args.analyze == 'pipette':
            print('')
            print('Analysis of spot test using a pipette (4×6 matrix)')
            print('')
            print('---------------------')
        if args.threshold:
            input_threshold = args.threshold
        else:
            input_threshold = 7
        if args.single:
            SpotScaner_single(os.path.join(pwd, args.single), input_threshold, bin_dir, initial_time, args.analyze)
        elif args.multi:
            SpotScaner_multi(pwd, input_threshold, bin_dir, initial_time, args.analyze)
        print('')
        print('Please check the *_converted.png images to confirm that the correct regions were detected.')
    else:
        print('')
        print(f'This is SpotScanner v{__version__}, developed by Kento Yanagisawa.')
        print('> Take a photo of spot test plate with the printed marker,')
        print('> then run this command to obtain a results.csv file.')
        parser.print_usage()
        print('')

if __name__ == "__main__":
    main()
