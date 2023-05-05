from time import sleep
from random import random
from multiprocessing import Manager, Process
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
                case "JENKINS_JOB_DONE":
                    print("posting back to github", flush=True)
        except Empty:
            poll_github(out_queue)
    print('Producer: Done', flush=True)

# jenkins job executed in a worker thread
def run_jenkins_job(stop_queue, out_queue):
    try:
        print(f'Starting a jenkins job')
        for i in range(10):
            print("jenkins_job is running {}".format(i))
            try:
                item = stop_queue.get(block=False)
                if item == "STOP":
                    print("stopping jenkins_job", flush=True)
                    break
            except Empty:
                print()
            sleep(1)
            if poll_jenkins(out_queue):
                break
        print(f'Task done')
    except Exception as e:
        print(e)

def jenkins_spawner(in_queue, out_queue, job_stop_queue):
    print("start jenkins_spawner")
    pool = Pool(processes=4)
    stopped = False
    while(True):
        try:
            item = in_queue.get(block=True)
            print("jenkins_spawner received event: " + item)
            match item:
                case "STOP":
                    print("exiting jenkins_spawner", flush=True)
                    # inform all running jenkins jobs that we were stopped
                    job_stop_queue.put("STOP")
                    stopped = True
                    break
                case "RUN":
                    if not stopped:
                        print("creating jenkins job", flush=True)
                        try:
                            pool.apply_async(run_jenkins_job, args=(job_stop_queue, out_queue))
                        except Exception as e:
                            print(e)
                    else:
                        print("jenkins_spawner was already stopped")
                case _:
                    print("unknown command: " + item)

        except Empty:
            print("cannot happen")
    print('waiting for jenkins jobs to finish', flush=True)
    # clean up pool and wait for outstanding jobs
    pool.close()
    pool.join()
    print('jenkins_spawner: Done', flush=True)

def service():
    m = Manager()
    queue = m.Queue()

    github_process_queue = m.Queue()
    github_process = Process(target=github_worker, args=(github_process_queue, queue))
    github_process.start()

    job_stop_queue = m.Queue()
    jenkins_process_queue = m.Queue()
    jenkins_process = Process(target=jenkins_spawner, args=(jenkins_process_queue, queue, job_stop_queue))
    jenkins_process.start()

    while True:
        item = queue.get()
        print("Service, processing " + item)
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
            case "JENKINS_JOB_DONE":
                github_process_queue.put("JENKINS_JOB_DONE")
            case _:
                print("service: unknown event: " + item)
    # all done
    print('Consumer: Done', flush=True)

# entry point
if __name__ == '__main__':
    service_process = Process(target=service)
    service_process.start()
    service_process.join()

def poll_jenkins(out_queue):
    results_ready = False
    # simulates polling jenkins by reading from local file
    with open('jenkins.txt') as f:
        for line in f.readlines():
            jenkins_data = line.strip()
            print("from jenkins: " + jenkins_data)
            results_ready = True
            out_queue.put(jenkins_data)
    with open('jenkins.txt', 'w') as f:
        f.write("")
    return results_ready

def poll_github(out_queue):
    results_ready = False
    # simulate polling github API by reading from local file
    with open('github.txt') as f:
        for line in f.readlines():
            github_data = line.strip()
            print("from github: " + github_data)
            results_ready = True
            out_queue.put(github_data)
    with open('github.txt', 'w') as f:
        f.write("")
    return results_ready