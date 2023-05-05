# SuperFastPython.com
# example of using the queue with processes
from time import sleep
from random import random
from multiprocessing import Process
from multiprocessing import Queue
from multiprocessing.pool import Pool
from queue import Empty

def github_worker(in_queue, out_queue):
    print("start github worker")
    while(True):
        try:
            item = in_queue.get(block=True, timeout=1)
            print("github-worker received event: " + item)
            match item:
                case "STOP":
                    print("exiting github_worker", flush=True)
                    break
                case "POST":
                    print("posting back to github", flush=True)
        except Empty:
            with open('github.txt') as f:
                for line in f.readlines():
                    github_data = line.strip()
                    print("from github: " + github_data)
                    out_queue.put(github_data)

            with open('github.txt', 'w') as f:
                f.write("")
    print('Producer: Done', flush=True)

# jenkings job executed in a worker thread
def run_jenkins_job(stop_queue, out_queue):
    print(f'Starting a jenkins job')
    for i in range(10):
        print("jenkins_job is running: " + i)
        item = stop_queue.get(block=False)
        if item == "STOP":
            print("stopping jenkins_job", flush=True)
            break
        sleep(1)
    # report a message
    print(f'Task done')
    out_queue.put("JENKINS_JOB_DONE")

def jenkins_spawner(in_queue, out_queue):
    print("start jenkins_spawner")
    pool = Pool(processes=4)
    job_stop_queue = Queue()
    stopped = False
    while(True):
        try:
            item = in_queue.get(block=True, timeout=1)
            print("jenkins_spawner received event: " + item)
            match item:
                case "STOP":
                    print("exiting jenkins_spawner", flush=True)
                    job_stop_queue.put("STOP")
                    stopped = True
                    break
                case "RUN":
                    pool.apply_async(run_jenkins_job, args=(job_stop_queue, out_queue))
                    print("creating jenkins job", flush=True)
                case _:
                    print("unknown command: " + item)

        except Empty:
            with open('jenkins.txt') as f:
                for line in f.readlines():
                    jenkins_data = line.strip()
                    print("from jenkins: " + jenkins_data)
                    out_queue.put(jenkins_data)
            with open('jenkins.txt', 'w') as f:
                f.write("")
    print('waiting for jenkins jobs to finish', flush=True)
    pool.join()
    print('jenkins_spawner: Done', flush=True)

def service(queue):
    github_process_queue = Queue()
    github_process = Process(target=github_worker, args=(github_process_queue, queue))
    github_process.start()

    jenkins_process_queue = Queue()
    jenkins_process = Process(target=jenkins_spawner, args=(jenkins_process_queue, queue))
    jenkins_process.start()

    while True:
        item = queue.get()
        match item:
            case "STOP":
                print("service: exiting service", flush=True)
                github_process_queue.put("STOP")
                jenkins_process_queue.put("STOP")
                github_process.join()
                jenkins_process.join()
                break
            case "RUN":
                print("service: starting jenkins job", flush=True)
                jenkins_process_queue.put("RUN")
            case "RESULT":
                jenkins_process_queue.put("RESULT")
            case _:
                print("service: unknown event: " + item)
    # all done
    print('Consumer: Done', flush=True)

# entry point
if __name__ == '__main__':
    queue = Queue()
    service_process = Process(target=service, args=(queue,))
    service_process.start()
    service_process.join()
