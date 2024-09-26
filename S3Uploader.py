import os
import boto3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
#from JsonBuilder import JsonBuilder

class S3UploadQueue:
    def __init__(self, region_name="ap-south-1"):
        load_dotenv()  # Load environment variables before accessing them
        self.s3_queue = []
        self.lock = threading.Lock()
        #self.json_info = JsonBuilder()
        self.s3_bucket_name = "eonpod-data"

        # Retrieve credentials from environment variables
        aws_access_key_id = os.getenv('S3_KEY')
        aws_secret_access_key = os.getenv('S3_SECRET')

        # Check if credentials are loaded
        if not aws_access_key_id or not aws_secret_access_key:
            raise ValueError("AWS credentials not found. Please check your .env file.")

        # AWS session setup
        self.session = boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self.s3_resource = self.session.resource("s3")
        self.s3_client = self.session.client("s3")
        self.processing_thread = threading.Thread(target=self.process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def create_folder_in_s3(self, folder_name):
        # Ensure the folder name ends with a trailing slash
        folder_key = folder_name if folder_name.endswith('/') else folder_name + '/'

        # Use the existing s3_client to put an empty object representing the folder
        try:
            self.s3_client.put_object(Bucket=self.s3_bucket_name, Key=folder_key)
            print(f"Folder '{folder_name}' created successfully in bucket '{self.s3_bucket_name}'")
        except Exception as e:
            print(f"Error: {e}")

    def add_to_queue(self, school, subject, local_directory):
        # Expects a folderpath where we have all the files inplace
        # if True:
        print("added to queue")
        with self.lock:
            self.s3_queue.append({
                "local_directory": local_directory,
                "school": school,
                "subject": subject,
            })
        print(f"Added to queue: {local_directory} for {subject}")

    def upload_file(self, local_file_path, school, subject, timestamp):
        # Get the base name (filename) from the local file path
        file_name = os.path.basename(local_file_path)

        # Construct the S3 object key using the school, subject, and the file name

        s3_object_key = f"{school}/{subject}/{timestamp}/{file_name}"
        timestamp = os.path.basename(os.path.dirname(local_file_path))
        date = timestamp.split("_")[0]
        try:
            # Use the s3_client to upload the file
            self.s3_client.upload_file(Filename=local_file_path, Bucket=self.s3_bucket_name, Key=s3_object_key)
            print(f"Uploaded {local_file_path} to s3://{self.s3_bucket_name}/{s3_object_key}")
            #self.json_info.update_s3(timestamp=timestamp, s3_path=s3_object_key, date = date)
        except Exception as e:
            print(f"Error uploading file {local_file_path}: {e}")

    def count_files_and_upload(self, local_directory, school, subject):
        timestamp = os.path.basename(local_directory)
        self.create_folder_in_s3(folder_name=f"{school}/{subject}/{timestamp}")

        for root, _, files in os.walk(local_directory):
            for file in files:
                local_file_path = os.path.join(root, file)
                self.upload_file(local_file_path, school, subject, timestamp)


    def process_queue(self):

        while True:
            with self.lock:
                if not self.s3_queue:
                    time.sleep(10)  # Sleep for a while if the queue is empty
                    continue

                current_task = self.s3_queue.pop(0)

            try:
                print("added to queue")
                local_directory = current_task["local_directory"]
                school= current_task["school"]
                subject= current_task["subject"]
                print(f"Starting S3 upload for {local_directory}")
                self.count_files_and_upload(local_directory, school, subject)
                print("Finished Uploading Files")

            except Exception as e:
                print(f"Error processing S3 upload for {current_task['local_directory']}: {str(e)}")

            time.sleep(20)  # Sleep for a short while before processing the next item

