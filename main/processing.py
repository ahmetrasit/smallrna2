import traceback

from . import models
import time
from django.utils.text import slugify
import json
import os
import multiprocessing
import subprocess
import gzip


class NewProcess:
    max_active_tasks = 1
    max_cpu = 4
    ref_folder = '../../../../reference/'
    pairs = {'AGNCT'[i]: 'AGNCT'[4 - i] for i in range(5)}

    def revComp(self, seq):
        return ''.join([self.pairs[nt] for nt in seq][::-1])

    def __init__(self, parameters, user, files):
        self.user = user
        self.username = str(user).split("@")[0]
        self.parameters = {}
        for key in parameters:
            self.parameters[key] = parameters.getlist(key)
        self.files = files
        self.parameters['uploaded_file_names'] = [str(file) for file in files]
        print('P>', self.parameters)

    def new_dataset(self):
        try:
            raw_data_folder = self.save_raw_data()
            self.start_background_process(self.task_after_upload, raw_data_folder, self.max_active_tasks)
        except Exception as e:
            print('error saving files:', str(e))

    @staticmethod
    def start_background_process(func, param, n):
        try:
            print('start_background_process')
            #pool = multiprocessing.Pool(processes=n)
            #pool.apply_async(func, args=(param,), callback=lambda: print('callback works'))
            p = multiprocessing.Process(target=func, args=(param,))
            p.start()
            print('start_background_process2')
            #func(param)
        except Exception as e:
            print('something wrong with the sbp')

    def task_after_upload(self, raw_data_folder):
        print('>task_after_upload')
        task = self.submit_task()
        try:
            wait = True
            while wait:
                time.sleep(1)
                wait = self.check_task_status(task)
                print('in while')
            next_task = self.determine_next_task()
            processed_data_folder = next_task(raw_data_folder)
            print('>Aligning data')
            self.align_samples(processed_data_folder)
            print('>Prepare for JBrowse')
            self.prepare_for_JBrowse(processed_data_folder)
            print(processed_data_folder)
            self.update_task_status(task, 'finished', '')
        except Exception as e:
            print('error', str(e))
            traceback.print_exc()
            self.update_task_status(task, 'error', str(e))

    def align_samples(self, folder):
        self.align2(folder, 'all.fa', 'genome')
        self.align2(folder, 'counts.fa', 'genome')
        self.align2(folder, 'counts.fa', 'metagenes')
        self.align2(folder, 'counts.fa', 'structural')

    def align2(self, folder, file_type, reference):
        reference2index = {'genome':'ws270hisat2', 'metagenes':'ws268metagenome', 'structural':'ws268struc_metagenome'}
        print(file_type, reference)
        curr_directory = os.getcwd()
        print(curr_directory)
        #os.chdir(folder)
        if file_type == 'counts.fa':
            bash_command = ' '.join(['for sample in sample___*{};'.format(file_type),
                                     'do echo $sample; hisat2 --dta-cufflinks -f -a -p {} -x {}{} -U $sample -S $sample.{}.sam;'.format(self.max_cpu, self.ref_folder, reference2index[reference], reference),
                                     'done'])
        else:
            print('jbrowse-required files')
            bash_command = ' '.join(['for sample in sample___*{};'.format(file_type),
                                'do echo $sample; hisat2 --dta-cufflinks --quiet -f -a -p {} -x {}{} -U $sample -S $sample.{}.sam;'.format(self.max_cpu, self.ref_folder, reference2index[reference], reference),
                                'cat $sample.{}.sam | samtools view -@ {} -Shub - | samtools sort -@ {} - -o $sample.{}.bam; samtools index $sample.{}.bam;'.format(reference, self.max_cpu, self.max_cpu, reference, reference),
                                'dep =$(samtools view -c -F 260 $sample.{}.bam; ratio =$(echo "scale=3; 1000000/$dep" | bc);'.format(reference),
                                'genomeCoverageBed -split -bg -scale $ratio -g {}ws270.sizes.genome -ibam $sample.{}.bam > $sample.{}.bedgraph;'.format(self.ref_folder, reference, reference),
                                '{}ucsc-tools/wigToBigWig -clip $sample.{}.bedgraph {}ws270.sizes.genome $sample.{}.bw;'.format(self.ref_folder, reference, self.ref_folder, reference),
                                'done'])
        print('H2>', bash_command)
        hisat2_cmd = subprocess.Popen(bash_command, shell=True)
        hisat2_cmd.wait()



    def prepare_for_JBrowse(self, folder):
        pass

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
        return False

    def determine_next_task(self):
        print('determine_next_task', self.parameters['new_dataset_focus'][0])
        print()
        if self.parameters['new_dataset_focus'][0] == 'needs debarcoding':
            print('debarcode_and_counts_fa')
            return self.debarcode_and_counts_fa
        else:
            print('create_counts_fa')
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
            json.dump(self.parameters,f , indent=4)
        return folder

    def create_raw_data_folders(self):
        try:
            os.makedirs('static/upload/raw/' + self.username + '/' + slugify(self.parameters['new_dataset_name']))
        except Exception as e:
            print('create raw folder:', str(e))
        return 'static/upload/raw/' + self.username + '/' + slugify(self.parameters['new_dataset_name'])

    def create_processed_data_folders(self, keyword):
        try:
            os.makedirs('static/data/' + self.username + '/' + slugify(keyword))
        except:
            pass
        return 'static/data/' + self.username + '/' + slugify(keyword)

    def create_counts_fa(self, raw_data_folder):
        folder = self.create_processed_data_folders('counts_fa')

        curr_directory = os.getcwd()
        os.chdir(raw_data_folder)

        sample_names = self.parameters['noDebarcoding_sampleName']
        file_names = self.parameters['uploaded_file_names']
        file2sample = {}
        for file, sample in list(zip(file_names, sample_names)):
            print(file, sample)
            try:
                rename_files_cmd = subprocess.Popen('mv {} sample___{}.fastq.gz'.format(file, sample), shell=True)
                file2sample['sample___{}.fastq.gz'.format(sample)] = sample
                rename_files_cmd.wait()
            except Exception as e:
                print('!Error renaming files', e)

        renamed_filenames = [file for file in os.listdir('./') if file.startswith('sample___') and file.endswith('fastq.gz')]

        # remove adapter
        if 'remove_adapter' in self.parameters:
            adapter = self.parameters['adapter_sequence'][0].strip()
            for file in renamed_filenames:
                bash_command = ' '.join(
                    ['cutadapt -m 10', '-a', adapter, '-j', str(self.max_cpu), '-o', '{}.trimmed.fastq.gz'.format(file),
                     '{}'.format(file),
                     '; mv', '{}.trimmed.fastq.gz'.format(file), '{}'.format(file)])
                cutadapt_cmd = subprocess.Popen(bash_command, shell=True, stdout=subprocess.PIPE)
                stdout = str(cutadapt_cmd.communicate()[0], 'utf-8').split('\n')
                with open('{}.cutadapt_report'.format(file), 'w') as f:
                    f.write('\n'.join(stdout))
                cutadapt_cmd.wait()
                print('adapters removed')

        #registering reads
        sample2raw_read_counts = {}
        umi_len = int(self.parameters['umi_length_noDebarcoding'][0]) if 'has_umi_noDebarcoding' in self.parameters else 0
        for file in renamed_filenames:
            with gzip.open('{}'.format(file), 'rt') as f:
                read_counts = {}
                seq_list = []
                read = []
                line_number = 0
                for line in f:
                    line_number += 1
                    read.append(line)
                    if line_number % 4 == 0:
                        seq = read[1]
                        seq_list.append(seq.strip())
                        read = []

                if umi_len:
                    for read in set(seq_list):
                        try:
                            read_counts[read[umi_len:]] += 1
                        except:
                            read_counts[read[umi_len:]] = 1
                else:
                    for read in seq_list:
                        try:
                            read_counts[read] += 1
                        except:
                            read_counts[read] = 1

                sample2raw_read_counts[file2sample[file]] = sum([read_counts[curr] for curr in read_counts])

                with open('sample___{}.counts.fa'.format(file2sample[file]), 'w') as f:
                    f.write('\n'.join(['>{}:{}\n{}'.format(seq, read_counts[seq], seq) for seq in read_counts]))

                all_fa = []
                for seq in read_counts:
                    for i in range(read_counts[seq]):
                        all_fa.append('>{}_{}\n{}'.format(seq, i + 1, seq))

                with open('sample___{}.all.fa'.format(file2sample[file]), 'w') as f:
                    f.write('\n'.join(all_fa))

        print({'read_counts': sample2raw_read_counts})
        return raw_data_folder


    def debarcode_and_counts_fa(self, raw_data_folder):
        files = [file for file in os.listdir(raw_data_folder) if file.endswith('fastq.gz')]
        print(files)

        os.makedirs(raw_data_folder + '/' + 'temp')
        curr_directory = os.getcwd()
        os.chdir(raw_data_folder)
        print(curr_directory, os.getcwd())

        #merge files
        cat_cmd = subprocess.Popen(' '.join(['ls; echo hey;', 'cat', ' '.join(files), '>', './temp/merged.fastq.gz']), shell=True)
        cat_cmd.wait()

        print('files merged')

        #remove adapter
        print('parameters', self.parameters)
        if 'remove_adapter' in self.parameters:
            adapter = self.parameters['adapter_sequence'][0].strip()
            bash_command = ' '.join(['cutadapt -m 10', '-a', adapter, '-j', str(self.max_cpu), '-o', './temp/trimmed.fastq.gz', './temp/merged.fastq.gz', '; mv', './temp/trimmed.fastq.gz', './temp/merged.fastq.gz'])
            cutadapt_cmd = subprocess.Popen(bash_command, shell=True, stdout=subprocess.PIPE)
            stdout = str(cutadapt_cmd.communicate()[0], 'utf-8').split('\n')
            with open('cutadapt_report.txt', 'w') as f:
                f.write('\n'.join(stdout))
            cutadapt_cmd.wait()
            print('adapters removed')

        try:
            debarcode_summary = self.debarcodeFile('./temp/merged.fastq.gz', self.parameters)
            print(debarcode_summary)
        except Exception as e:
            print('problem:', e)

        #folder = self.create_processed_data_folders('counts_fa')
        return raw_data_folder

    def processRead(self, read, barcode2sample, rev_barcode2sample):
        header, seq, plus, _ = read
        if plus == '+':
            barcode = header.split(':')[-1]
            if barcode in barcode2sample:
                return barcode2sample[barcode], seq.strip(), 0
            elif barcode in rev_barcode2sample:
                return rev_barcode2sample[barcode], seq.strip(), 1
            else:
                return barcode, None, 0
        else:
            return None, None, None

    def debarcodeFile(self, file, parameters):
        barcode2sample_template = {bar : sam for bar, sam in zip(parameters['new_barcode'], parameters['new_sample'])}
        barcode2sample = {}
        rev_barcode2sample = {}
        for seq in barcode2sample_template:
            barcode2sample[seq] = barcode2sample_template[seq]
            barcode2sample[seq[2:]] = barcode2sample_template[seq]
            barcode2sample[seq[:-2]] = barcode2sample_template[seq]
            rev_barcode2sample[self.revComp(seq)] = barcode2sample_template[seq]
            rev_barcode2sample[self.revComp(seq[2:])] = barcode2sample_template[seq]
            rev_barcode2sample[self.revComp(seq[:-2])] = barcode2sample_template[seq]
        print(barcode2sample, rev_barcode2sample)

        sample2reads = {sample:[] for sample in parameters['new_sample']}
        rest_barcodes = {}
        error_count = 0
        line_number = 0
        reverse_barcode_count = 0

        print('reading merged file')
        with gzip.open(file, 'rt') as f:
            read = []
            for line in f:
                line_number += 1
                read.append(line.strip())
                if line_number % 4 == 0:
                    sample, seq, reverse = self.processRead(read, barcode2sample, rev_barcode2sample)
                    read = []
                    if seq:
                        sample2reads[sample].append(seq)
                        reverse_barcode_count += reverse
                    elif sample:
                        try:
                            rest_barcodes[sample] += 1
                        except:
                            rest_barcodes[sample] = 1
                    else:
                        error_count += 1

        umi_len = int(parameters['umi_length_needsDebarcoding'][0]) if 'has_umi_needsDebarcoding' in parameters else 0

        print('create counts.fa and all.fa')
        sample2raw_read_counts = {}
        for sample in parameters['new_sample']:
            print('>sample', sample)
            read_counts = {}
            if umi_len:
                for read in set([read for read in sample2reads[sample]]):
                    try:
                        read_counts[read[umi_len:]] += 1
                    except:
                        read_counts[read[umi_len:]] = 1
            else:
                for read in sample2reads[sample]:
                    try:
                        read_counts[read] += 1
                    except:
                        read_counts[read] = 1

            sample2raw_read_counts[sample] = sum([read_counts[curr] for curr in read_counts])

            with open('sample___{}.counts.fa'.format(sample), 'w') as f:
                f.write('\n'.join(['>{}:{}\n{}'.format(seq, read_counts[seq], seq) for seq in read_counts]))

            all_fa = []
            for seq in read_counts:
                for i in range(read_counts[seq]):
                    all_fa.append('>{}_{}\n{}'.format(seq, i+1, seq))

            with open('sample___{}.all.fa'.format(sample), 'w') as f:
                f.write('\n'.join(all_fa))

        return {'read_counts':sample2raw_read_counts, 'reverse_barcodes':reverse_barcode_count, 'other_barcodes':{curr for curr in rest_barcodes if rest_barcodes[curr] > 100000}, 'read_errors':error_count}




        '''
        #split file into smaller chunks, preparing for parallel debarcoding
        split_cmd = subprocess.Popen(''.join(['split -l 200000 ', './temp/merged.fastq.gz', 'chunk']), shell=True)
        split_cmd.wait()
        split_files = [file for file in os.listdir('./temp') if file.startswith('chunk')]
        print('split_files', split_files)


        #start parallel debarcoding
        m = multiprocessing.Manager()
        start_q = m.Queue()
        end_q = m.Queue()
        jobs = []
        pool = multiprocessing.Pool(processes=self.max_cpu)
        for file in split_files:
            jobs.append(pool.apply_async(self.debarcodeFile, args=([file, start_q, end_q],)))

        cont = True
        while cont:
            if end_q.qsize() == len(split_files):
                cont = False
                break
            time.sleep(2)

        '''