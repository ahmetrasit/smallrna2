from . import models
import time
from django.utils.text import slugify
import json
import os


class NewProcess:
    max_active_tasks = 3

    def __init__(self, parameters, user):
        self.user = user
        self.username = user.username
        self.parameters = parameters

    def new_dataset(self):
        task = self.submit_task()
        try:
            raw_data_folder = self.save_raw_data()

            allowed = True
            while not allowed:
                time.sleep(12)
                allowed = self.check_task_status(task)

            next_task = self.determine_next_task()
            processed_data_folder = next_task(raw_data_folder)
            self.update_task_status(task, 'finished', '')
        except Exception as e:
            self.update_task_status(task, 'error', str(e))

    def submit_task(self):
        task = models.Task(
            name=slugify(self.parameters['dataset_name']),
            created_by=self.user
         )
        task.save()
        return task

    def update_task_status(self, task, status, message):
        task.status = status
        task.message = message
        task.save()
        return task

    def check_task_status(self, task):
        no_of_active_tasks = models.Task.objects.filter('status'=='running')
        if no_of_active_tasks <= self.max_active_tasks:
            if task.id == models.Task.objects.filter('status' == 'waiting').first().id:
                task.status = 'running'
                return True
        return False

    def determine_next_task(self):
        print('determine_next_task', self.parameters['new_dataset_focus'])
        if self.parameters['new_dataset_focus'] == 'needs_debarcoding':
            return self.debarcode_and_counts_fa
        else:
            return self.create_counts_fa

    def save_raw_data(self):
        folder = self.create_raw_data_folders()
        print('save_raw_data', folder)
        for file in self.parameters['files']:
            filename = str(file)
            with open(folder + '/' + filename, 'wb+') as destination:
                print('saving', folder + '/' + filename)
                for chunk in file.chunks():
                    destination.write(chunk)
        with open(folder + '/dataset_annotation.json', 'w') as f:
            json.dump(self.parameters, f)
        return folder

    def create_raw_data_folders(self):
        print(os.getcwd(), os.listdir('./'))
        try:
            print(os.getcwd(), os.listdir('./'))
            os.makedirs('static/upload/')
            os.makedirs('static/upload/raw/')
            os.makedirs('static/upload/raw/' + self.username )
            os.makedirs('static/upload/raw/' + self.username + '/' + slugify(self.parameters['dataset_name']))
        except:
            pass
        return 'static/upload/raw/' + self.username + '/' + slugify(self.parameters['dataset_name'])

    def create_processed_data_folders(self, keyword):
        print(os.getcwd(), os.listdir('./'))
        try:
            print(os.getcwd(), os.listdir('./'))
            os.makedirs('static/data/')
            os.makedirs('static/data/' + self.username)
            os.makedirs('static/data/' + self.username + '/' + slugify(keyword))
        except:
            pass
        return 'static/data/' + self.username + '/' + slugify(keyword)

    def create_counts_fa(self, raw_data_folder):
        folder = self.create_processed_data_folders('counts_fa')
        for file in [file for file in os.listdir(raw_data_folder) if file.endswith('.fastq.gz')]:
            pass
        return folder

    def debarcode_and_counts_fa(self, raw_data_folder):
        #cat files in raw_data_folder
        #remove adapters if selected
        #split file into 200K lines
        #debarcode in threadpool inside raw_data
        #merge files with the same adapter sequence and feed counts_fa
        folder = self.create_processed_data_folders('counts_fa')
        #create counts.fa files
        #remove split files
        return folder
