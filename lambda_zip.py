import zipfile
import os
import argparse

def create_zip(zip_file_name):
    current_path = os.path.dirname(os.path.realpath(__file__))
    destination_zip = os.path.join(current_path, zip_file_name)
    print('Creating zip file:', zip_file_name)
    zip_file = zipfile.ZipFile(destination_zip, 'w')
    root = os.listdir(current_path)
    for item in root:
        if os.path.isfile(os.path.join(current_path, item)) and item.endswith('.py'):
            print('Compressing:', item)
            zip_file.write(item, compress_type=zipfile.ZIP_DEFLATED)

    for folder_path, subfolders, files in os.walk(current_path):
        if os.path.basename(folder_path) == 'site-packages':
            site_packages = subfolders
            for package in site_packages:
                print('Compressing package:', package)
                package_path = os.path.join(folder_path, package)
                zip_dir(package_path, folder_path, zip_file)

    return zip_file

def zip_dir(path, parent_path, zip_file):
    for folder_path, subfolders, files in os.walk(path):
        for file in files:
            absolute_path = os.path.join(folder_path, file)
            relative_path = os.path.relpath(absolute_path, parent_path)
            zip_file.write(absolute_path, relative_path, compress_type=zipfile.ZIP_DEFLATED)
    return zip_file

def delete_zip(zip_file_name):
    current_path = os.path.dirname(os.path.realpath(__file__))
    zip_file_path = os.path.join(current_path, zip_file_name)
    if os.path.isfile(zip_file_path):
        print('Removing existing file:', zip_file_name)
        os.remove(zip_file_path)

# Command-line functions
def main():
    args = parse_args()
    delete_zip(args.filename)
    if args.delete:
        return True
    zip_file = create_zip(args.filename)
    zip_file.close()
    return True

def parse_args():
    parser = argparse.ArgumentParser(
        description='create or delete the lambda handler zip file')
    parser.add_argument(
        '-f', '--filename',
        metavar='FILENAME',
        type=str,
        default='lambda_handler.zip',
        help='The name of the zip file'
    )
    parser.add_argument(
        '-d', '--delete',
        action='store_true',
        help='Delete the zip file'
    )
    return parser.parse_args()

if __name__ == "__main__":
    main()
