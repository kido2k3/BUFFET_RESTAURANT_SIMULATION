import simpy
import random
import numpy

TIME_INTERVAL = [30 / 60, 100 / 60, 30 / 60, 15 / 60, 2 / 60]
# --> the lambda of exponential distribution
TIME_CAN_WAIT = 8 / 60
RANDOM_SEED = 42
RATE_TAKING_FOOD = [0.9, 0.8, 0.99, 0.85]
# currently only used for ticket queue-  maximum number of customers in ALL of the ticket queue
MAX_QUEUE_SIZE = 10

random.seed(223)


def erase_log():
    with open('log_ticket.txt', 'w'):
        pass
    with open('log_main_course.txt', 'w'):
        pass
    with open('log_drinks.txt', 'w'):
        pass
    with open('log_dessert.txt', 'w'):
        pass
    with open('log_appetizer.txt', 'w'):
        pass
    with open('log_seat.txt', 'w'):
        pass
    with open('log_waiting_time.txt', 'w'):
        pass
    with open('log_generate.txt', 'w'):
        pass
    with open('log_seat_eat.txt', 'w'):
        pass


def print_log(file_name, str):
    with open(file_name, 'a') as f:
        f.write(str)


"""
brief:  
    Variable:    
        id --> name of customers
        arrival_time --> the time when customers arrived at each queue
        waiting_time --> the period of time when customers waited in each queue
        rating --> The rate star of customers to the restaurant
        left_time --> the time when customers left the restaurant
        take_food -->   list of food will be taken (drink, appetizer, main course, dessert respectively)
                        1: will be taken
                        0: were taken and no longer be taken
    Function:
        set_waiting_time: set the waiting time in current queue, and update the rate if waiting too long
        reset_waiting_time: reset the waiting time before each queue
        classify: classify a customer whether he/she will take particular food following the probability
"""


class Customer:
    def __init__(self, id, arrival_time=0):
        self.id = id
        self.arrival_time = arrival_time
        self.waiting_time = 0
        self.rating = 5
        self.left_time = 0
        self.taking_food = [1, 1, 1, 1]
        self.not_want_to_get_food = 1
        self.arrival_time_res = 0
        self.left_ticket_time = 0

    def classify(self):
        for i in range(4):
            rate = RATE_TAKING_FOOD[i]
            self.taking_food[i] = numpy.random.choice(
                a=[0, 1], p=[1 - rate, rate])

            if self.taking_food[i] == 1:
                self.not_want_to_get_food = 0

    def set_waiting_time(self, waiting_time, place=''):
        self.waiting_time = waiting_time
        # update rating
        if waiting_time > TIME_CAN_WAIT:
            decrease = (self.waiting_time // TIME_CAN_WAIT) * 0.5
            print_log('log_waiting_time.txt',
                      f"Customer {self.id} waited for {self.waiting_time:7f}{place} and decreased the rating by {decrease}\n")
            self.rating = self.rating - decrease
            return True
        return False

    def pick_food_to_queue(self):
        indices_with_one = [
            index for index, value in enumerate(self.taking_food) if value == 1
        ]
        if not indices_with_one:
            return -1
        # Pick a random index with uniform rate
        random_index = random.choice(indices_with_one)
        return random_index

    def is_full_desired_dish(self):
        if self.not_want_to_get_food == 1:
            return 0
        for i in range(4):
            if self.taking_food[i] == 1:
                return 0
        return 1

    def is_not_want_to_eat(self):
        return self.not_want_to_get_food


"""
brief:  
    Variable:    
        NUMBER_OF_TICKET_SERVERS
        TIME_TICKET_SERVICE --> the lambda of exponential distribution
        server_ticket
    Function:
        serve_ticket: serve customers in ticket desks
"""


class Restaurant:
    def __init__(self, env):
        self.NUMBER_OF_TICKET_SERVERS = 2
        self.TIME_TICKET_SERVICE = 10
        self.NUMBER_OF_DRINKS_SERVICE = 1
        self.TIME_DRINKS_SERVICE = 20
        self.NUMBER_OF_APPETIZER_SERVICE = 2
        self.TIME_OF_APPETIZER_SERVICE = 15
        self.NUMBER_OF_MAINCOURSE_SERVICE = 3
        self.TIME_OF_MAINCOURSE_SERVICE = 12
        self.NUMBER_OF_DESSERTS_SERVICE = 1
        self.TIME_DESSERTS_SERVICE = 12
        self.TIME_SEAT = 0.05
        self.NUMBER_OF_SEATS = 50

        self.ticket_queue_size = 0
        self.num_cus_in = 0
        self.num_cus_wait_long = 0
        self.num_Cus_leave_ticketFull = 0
        self.num_Cus_leave_resFull = 0

        self.server_ticket = simpy.Resource(env, self.NUMBER_OF_TICKET_SERVERS)
        self.server_mainCourses = simpy.Resource(
            env, self.NUMBER_OF_MAINCOURSE_SERVICE)
        self.server_appetizer = simpy.Resource(
            env, self.NUMBER_OF_APPETIZER_SERVICE)
        self.server_drinks = simpy.Resource(env, self.NUMBER_OF_DRINKS_SERVICE)
        self.server_desserts = simpy.Resource(
            env, self.NUMBER_OF_DESSERTS_SERVICE)
        self.server_Seat_eat = simpy.Resource(env, self.NUMBER_OF_SEATS)
        self.event_full = simpy.Event(env)

        # Output, for debugging or testing
        self.num_use_ticket = 0
        self.num_use_mainCourses = 0
        self.num_use_appetizer = 0
        self.num_use_drinks = 0
        self.num_use_desserts = 0
        self.num_time_seat = 0
        self.num_rated = 0  # number of times use a service

        self.sum_serve_time_ticket = 0
        self.sum_serve_time_mainCourses = 0
        self.sum_serve_time_appetizer = 0
        self.sum_serve_time_drinks = 0
        self.sum_serve_time_desserts = 0  # for calculating average value
        self.sum_time_seat_eat = 0
        self.sum_rated = 0
        self.sum_rated_no_neg = 0  # rating (< 0) = 0

        self.num_ticket_wait_long = 0
        self.num_drinks_wait_long = 0
        self.num_appetizer_wait_long = 0
        self.num_mainCourses_wait_long = 0
        self.num_desserts_wait_long = 0

    def serve_ticket(self, env, consumer, arrival_time):
        consumer.arrival_time = arrival_time

        if self.ticket_queue_size >= MAX_QUEUE_SIZE:  #
            self.num_Cus_leave_ticketFull += 1
            print_log('log_ticket.txt',
                      f"Ticket queue is full, Customer {consumer.id} left\n")
            return
        else:
            self.ticket_queue_size += 1

        local_event_full = (
            self.event_full
        )  # assign event_full to a local variable to make sure that it still trigger if somehow event_full get untriggered at the same time it triggered
        # entering_Ticket_queue

        with self.server_ticket.request() as req:
            # wakeup if any queue is available for serving or the restaurant is full
            yield req | local_event_full
            if local_event_full.triggered:
                print_log(
                    'log_ticket.txt', f"The restaurant is full so customer {consumer.id} left the ticket queue #####################################################################\n")
                self.num_Cus_leave_resFull += 1
                self.ticket_queue_size = 0
                return

            print_log(
                'log_ticket.txt', f"Customer {consumer.id:3} was getting serve at ticket at {env.now:7.3f}\n")
            serve_time = random.expovariate(self.TIME_TICKET_SERVICE)
            yield env.timeout(
                serve_time
            ) | local_event_full  # wakeup if the currently customer has been served or the restaurant is full,
            # this means if there are more than 2 queue, when the 50th customer bought their ticket
            # all other customers were getting served in others ticket queue have to leave

            if local_event_full.triggered:
                print_log(
                    'log_ticket.txt', f"The restaurant is full so customer {consumer.id} has left the ticket queue #####################################################################")
                self.num_Cus_leave_resFull += 1
                self.ticket_queue_size = 0
                return

            self.ticket_queue_size -= 1
            self.num_cus_in += 1
            self.num_use_ticket += 1
            self.sum_serve_time_ticket += serve_time

            if (
                self.num_cus_in >= self.NUMBER_OF_SEATS
            ):  # check if the restaurant is full after adding this customer
                self.event_full.succeed()

            if consumer.set_waiting_time(env.now - consumer.arrival_time, ' in ticket'):
                self.num_cus_wait_long += 1
                self.num_ticket_wait_long += 1
            consumer.left_ticket_time = env.now
            print_log('log_ticket.txt',
                      f"Customer {consumer.id:3} left ticket at {env.now:7.3f}, the restaurant has {self.num_cus_in} customers\n")
            self.choose_food(env, consumer)

    def choose_food(self, env, customer):
        chosen_food = customer.pick_food_to_queue()
        if chosen_food == 0:
            env.process(self.serve_drinks(env, customer))
        elif chosen_food == 1:
            env.process(self.serve_appetizer(env, customer))
        elif chosen_food == 2:
            env.process(self.serve_mainCourses(env, customer))
        elif chosen_food == 3:
            env.process(self.serve_desserts(env, customer))
        elif customer.is_full_desired_dish():
            env.process(self.serve_seat_eat(env, customer))
        elif customer.is_not_want_to_eat():
            self.leave_n_rate(env, customer)
        else:
            print("Something went wrong!")

    def serve_drinks(self, env, consumer):
        consumer.arrival_time = env.now
        print_log('log_drinks.txt',
                  f"Customer {consumer.id:3} entered drinks queue at {env.now:7.3f}\n")
        with self.server_drinks.request() as req:
            yield req
            print_log(
                'log_drinks.txt', f"Customer {consumer.id:3} was getting served at drinks at {env.now:7.3f}\n")
            serve_time = random.expovariate(self.TIME_DRINKS_SERVICE)
            yield env.timeout(serve_time)

            self.num_use_drinks += 1
            self.sum_serve_time_drinks += serve_time

            if consumer.set_waiting_time(env.now - consumer.arrival_time, ' in drinks'):
                self.num_cus_wait_long += 1
                self.num_drinks_wait_long += 1

            consumer.taking_food[0] = 0
            print_log(
                'log_drinks.txt', f"Customer {consumer.id:3} left drinks at {env.now:7.3f}\n")
            self.choose_food(env, consumer)

    def serve_appetizer(self, env, consumer):
        consumer.arrival_time = env.now
        print_log('log_appetizer.txt',
                  f"Customer {consumer.id:3} entered appetizer queue at {env.now:7.3f}\n")
        with self.server_appetizer.request() as req:
            yield req
            print_log('log_appetizer.txt',
                      f"Customer {consumer.id:3} was getting served at appetizer at {env.now:7.3f}\n")
            serve_time = random.expovariate(self.TIME_OF_APPETIZER_SERVICE)
            yield env.timeout(serve_time)

            self.num_use_appetizer += 1
            self.sum_serve_time_appetizer += serve_time

            if consumer.set_waiting_time(env.now - consumer.arrival_time, ' in appetizer'):
                self.num_cus_wait_long += 1
                self.num_appetizer_wait_long += 1

            consumer.taking_food[1] = 0
            print_log('log_appetizer.txt',
                      f"Customer {consumer.id:3} left appetizer at {env.now:7.3f}\n")
            self.choose_food(env, consumer)

    def serve_mainCourses(self, env, consumer):
        consumer.arrival_time = env.now
        print_log('log_main_course.txt',
                  f"Customer {consumer.id:3} entered mainCourse queue at {env.now:7.3f}\n")
        with self.server_mainCourses.request() as req:
            yield req
            print_log('log_main_course.txt',
                      f"Customer {consumer.id:3} was getting served at mainCourse at {env.now:7.3f}\n")
            serve_time = random.expovariate(self.TIME_OF_MAINCOURSE_SERVICE)
            yield env.timeout(serve_time)

            self.num_use_mainCourses += 1
            self.sum_serve_time_mainCourses += serve_time

            if consumer.set_waiting_time(env.now - consumer.arrival_time, ' in main course'):
                self.num_cus_wait_long += 1
                self.num_mainCourses_wait_long += 1

            consumer.taking_food[2] = 0
            print_log('log_main_course.txt',
                      f"Customer {consumer.id:3} left mainCourse at {env.now:7.3f}\n")
            self.choose_food(env, consumer)

    def serve_desserts(self, env, consumer):
        consumer.arrival_time = env.now
        print_log('log_dessert.txt',
                  f"Customer {consumer.id:3} entered desserts queue at {env.now:7.3f}\n")
        with self.server_desserts.request() as req:
            yield req
            print_log('log_dessert.txt',
                      f"Customer {consumer.id:3} was getting served at desserts at {env.now:7.3f}\n")
            serve_time = random.expovariate(self.TIME_DESSERTS_SERVICE)
            yield env.timeout(serve_time)

            self.num_use_desserts += 1
            self.sum_serve_time_desserts += serve_time

            if consumer.set_waiting_time(env.now - consumer.arrival_time, ' in desserts'):
                self.num_cus_wait_long += 1
                self.num_desserts_wait_long += 1

            consumer.taking_food[3] = 0
            print_log('log_dessert.txt',
                      f"Customer {consumer.id:3} left desserts at {env.now:7.3f}\n")
            self.choose_food(env, consumer)

    def serve_seat_eat(self, env, consumer):
        with self.server_Seat_eat.request() as req:
            yield req
            print_log('log_seat_eat.txt',
                      f"Customer {consumer.id:3} entered a seat to eat at {env.now:7.3f}\n")
            serve_time = random.expovariate(self.TIME_SEAT)
            yield env.timeout(serve_time)
            self.num_time_seat += 1
            self.sum_time_seat_eat += serve_time
            print_log('log_seat_eat.txt',
                      f"Customer {consumer.id:3} has finished their dinner at {env.now:7.3f}\n")
            self.leave_n_rate(env, consumer)

    def leave_n_rate(self, env, consumer):
        self.num_cus_in -= 1
        self.num_rated += 1
        self.sum_rated += consumer.rating

        if consumer.rating > 0:
            self.sum_rated_no_neg += consumer.rating

        if (
            self.event_full.triggered
        ):  # if the restaurant was full before, untriggered this because a customer is leaving
            self.event_full = simpy.Event(env)

        print_log('log_seat_eat.txt',
                  f"Customer {consumer.id:3} left the restaurant at {env.now:7.3f} and rated {consumer.rating} stars, the restaurant has {self.num_cus_in} customers\n")


def generate(env, TIME_INTERVAL, server_generator, restaurant):
    with server_generator.request() as req:
        yield req
        i = 0
        while True:
            consumer = Customer(i, arrival_time=env.now)
            consumer.arrival_time_res = env.now
            consumer.classify()
            print_log('log_generate.txt',
                      f"Customer {consumer.id:3} arrived at {consumer.arrival_time:7.3f} and entered ticket queue (cus_in:{restaurant.num_cus_in})\n")
            env.process(restaurant.serve_ticket(
                env, consumer, consumer.arrival_time))
            if env.now < 60:  # 5h-6h
                arrival_between = random.expovariate(TIME_INTERVAL[0])
            elif env.now < 120:  # 6h-7h
                arrival_between = random.expovariate(TIME_INTERVAL[1])
            elif env.now < 180:  # 7h-8h
                arrival_between = random.expovariate(TIME_INTERVAL[2])
            elif env.now < 240:  # 8h-9h
                arrival_between = random.expovariate(TIME_INTERVAL[3])
            elif env.now < 300:  # 9h-10h
                arrival_between = random.expovariate(TIME_INTERVAL[4])
            else:
                yield env.timeout(arrival_between)
                break
            i += 1
            yield env.timeout(arrival_between)


# main
erase_log()
env = simpy.Environment()
restaurant = Restaurant(env)
server_generator = simpy.Resource(env, 1)
env.process(generate(env, TIME_INTERVAL, server_generator, restaurant))

env.run(until=60 * 5)

print(f"Time can wait: {TIME_CAN_WAIT}")
print(
    f"Ticket -  Uses: {restaurant.num_use_ticket}     AverageServe: {restaurant.sum_serve_time_ticket/restaurant.num_use_ticket:7.3f}     WaitLong: {restaurant.num_ticket_wait_long}"
)
print(
    f"Drinks -  Uses: {restaurant.num_use_drinks}     AverageServe: {restaurant.sum_serve_time_drinks/restaurant.num_use_drinks:7.3f}     WaitLong: {restaurant.num_drinks_wait_long}"
)
print(
    f"Appetizer -  Uses: {restaurant.num_use_appetizer}     AverageServe: {restaurant.sum_serve_time_appetizer/restaurant.num_use_appetizer:7.3f}     WaitLong: {restaurant.num_appetizer_wait_long}"
)
print(
    f"mainCourses -  Uses: {restaurant.num_use_mainCourses}     AverageServe: {restaurant.sum_serve_time_mainCourses/restaurant.num_use_mainCourses:7.3f}     WaitLong: {restaurant.num_mainCourses_wait_long}"
)
print(
    f"Desserts -  Uses: {restaurant.num_use_desserts}     AverageServe: {restaurant.sum_serve_time_desserts/restaurant.num_use_desserts:7.3f}     WaitLong: {restaurant.num_desserts_wait_long}"
)
print(
    f"Average time that customers spent eating at the table: {restaurant.sum_time_seat_eat/restaurant.num_time_seat:7.3f}"
)
print(
    f"Number of rating: {restaurant.num_rated}    AverageRating: {restaurant.sum_rated/restaurant.num_rated}   AverageRating_MinZero: {restaurant.sum_rated_no_neg/restaurant.num_rated}"
)
print(
    f"There were {restaurant.num_Cus_leave_ticketFull} times that customers left the restaurant because the ticket queue was full"
)
print(
    f"There were {restaurant.num_Cus_leave_resFull} times that customers left the restaurant because the restaurant was full"
)
print(
    f"There were {restaurant.num_cus_wait_long} times that customers had to wait too long ({restaurant.num_ticket_wait_long + restaurant.num_drinks_wait_long + restaurant.num_appetizer_wait_long + restaurant.num_mainCourses_wait_long + restaurant.num_desserts_wait_long})"
)
