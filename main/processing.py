import traceback

from . import models
import time
from django.utils.text import slugify
import json
import os
import multiprocessing


class NewProcess:
    max_active_tasks = 5

    def __init__(self, parameters, user, files):
        self.user = user
        self.username = str(user).split("@")[0]
        self.parameters = {}
        for key in parameters:
            self.parameters[key] = parameters.getlist(key)
        self.files = files

    def new_dataset(self):
        try:
            raw_data_folder = self.save_raw_data()
            self.start_background_process(self.task_after_upload, raw_data_folder)
        except Exception as e:
            print('error saving files:', str(e))

    @staticmethod
    def start_background_process(func, param):
        pool = multiprocessing.Pool(processes=1)
        pool.apply_async(func, args=(param,))

    def task_after_upload(self, raw_data_folder):
        task = self.submit_task()
        try:
            wait = True
            while wait:
                time.sleep(1)
                wait = self.check_task_status(task)

            next_task = self.determine_next_task()
            processed_data_folder = next_task(raw_data_folder)
            print(processed_data_folder)
            self.update_task_status(task, 'finished', '')
        except Exception as e:
            print('error', str(e))
            traceback.print_exc()
            self.update_task_status(task, 'error', str(e))

    def submit_task(self):
        try:
            task = models.Task(
                name=slugify(self.parameters['new_dataset_name']),
                created_by=self.user
             )
            task.save()
        except Exception as e:
            print('submit_task exception', str(e))
            traceback.print_exc()
        return task

    @staticmethod
    def update_task_status(task, status, message):
        task.status = status
        task.message = message
        task.save()
        return task

    def check_task_status(self, task):
        no_of_active_tasks = len(models.Task.objects.filter(status = 'running'))
        if no_of_active_tasks <= self.max_active_tasks:
            if task.id == models.Task.objects.filter(status = 'waiting').first().id:
                task.status = 'running'
                task.save()
                return False
        return True

    def determine_next_task(self):
        print('determine_next_task', self.parameters['new_dataset_focus'])
        if self.parameters['new_dataset_focus'] == 'needs_debarcoding':
            return self.debarcode_and_counts_fa
        else:
            return self.create_counts_fa

    def save_raw_data(self):
        folder = self.create_raw_data_folders()
        for file in self.files:
            filename = str(file)
            with open(folder + '/' + filename, 'wb+') as destination:
                print('saving', folder + '/' + filename)
                for chunk in file.chunks():
                    destination.write(chunk)
        #self.parameters['noDebarcoding_sampleName'] = self.parameters.getlist('noDebarcoding_sampleName')
        with open(folder + '/dataset_annotation.json', 'w') as f:
            json.dump(self.parameters, f)
        return folder

    def create_raw_data_folders(self):
        try:
            #print(os.getcwd(), os.listdir('./'))
            #os.makedirs('static/upload/')
            #os.makedirs('static/upload/raw/')
            #os.makedirs('static/upload/raw/' + self.username )
            os.makedirs('static/upload/raw/' + self.username + '/' + slugify(self.parameters['new_dataset_name']))
        except Exception as e:
            print('create raw folder:', str(e))
        return 'static/upload/raw/' + self.username + '/' + slugify(self.parameters['new_dataset_name'])

    def create_processed_data_folders(self, keyword):
        #print(os.getcwd(), os.listdir('./'))
        try:
            #print(os.getcwd(), os.listdir('./'))
            #os.makedirs('static/data/')
            #os.makedirs('static/data/' + self.username)
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
