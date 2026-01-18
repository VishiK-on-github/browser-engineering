import threading


class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args

    
    def run(self):
        """
        run the task
        """

        self.task_code(*self.args)
        self.task_code = None
        self.args = None


    def __str__(self) -> str:
        return f"Task(task={self.task_code}, args={self.args})"


class TaskRunner:
    def __init__(self, tab) -> None:
        self.condition = threading.Condition()

        self.tab = tab
        self.tasks = []

        self.main_thread = threading.Thread(
            target=self.run,
            name="Main Thread")
        
        self.needs_quit = False
        

    def start_thread(self):
        """
        creates a new thread on the OS level
        """

        self.main_thread.start()


    def schedule_task(self, task):
        """
        adding a task to the task queue
        """

        self.condition.acquire(blocking=True)
        self.tasks.append(task)

        # wakes up all threads waiting on lock
        self.condition.notify_all()

        # removes the lock
        self.condition.release()


    def set_needs_quit(self):
        """
        setting needs quit on task runner level
        """

        self.condition.acquire(blocking=True)
        self.needs_quit = True
        self.condition.notify_all()
        self.condition.release()

    
    def run(self):
        """
        running of scheduled tasks in task queue
        """

        while True:

            # to prevent two threads from picking up the same task
            self.condition.acquire(blocking=True)
            needs_quit = self.needs_quit
            self.condition.release()

            # checking to see if needs quit is set to stop
            # execution of tasks in the task queue
            if needs_quit: 
                self.handle_quit()
                return

            task = None
            self.condition.acquire(blocking=True)

            # check to see if we have enough tasks in task queue
            if len(self.tasks) > 0:
                task = self.tasks.pop(0)

            self.condition.release()
            
            # execute task
            if task:
                task.run()
            
            self.condition.acquire(blocking=True)

            # while instead if to prevent spurious wakeup
            # this is to put threads to sleep since there are no 
            # tasks in the queue which need to be executed
            while len(self.tasks) == 0 and not self.needs_quit:

                # removes lock and sleeps until notified
                # it reacquires lock when it wakes u
                self.condition.wait()

            self.condition.release()


    def handle_quit(self):
        pass


    def clear_pending_tasks(self):
        """
        remove tasks from the task runner queue
        """

        self.condition.acquire(blocking=True)
        self.tasks.clear()
        self.condition.release()


    def __str__(self) -> str:
        return f"TaskRunner(tasks={self.tasks})"
