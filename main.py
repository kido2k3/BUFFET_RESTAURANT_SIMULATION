import simpy
import random
import numpy
import queue

TIME_INTERVAL = [30/60, 100/60, 30/60, 15/60, 5/60]
# --> the lambda of exponential distribution
TIME_CAN_WAIT = 8/60
RANDOM_SEED = 42
RATE_TAKING_FOOD = [0.9, 0.8, 0.99, 0.85]
# random.seed(RANDOM_SEED)

'''
brief:  
    Variable:    
        id --> name of customers
        arrival_time --> the time when customers arrived at the restaurant
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
'''


class Customer:
    def __init__(self, id, arrival_time=0):
        self.id = id
        self.arrival_time = arrival_time
        self.waiting_time = 0
        self.rating = 5
        self.left_time = 0
        self.taking_food = [1, 1, 1, 1]
        self.doesnt_want_to_buy_food = 1

    def classify(self):
        for i in range(4):
            rate = RATE_TAKING_FOOD[i]
            self.taking_food[i] = numpy.random.choice(
                a=[0, 1], p=[1-rate, rate])
            # print(self.taking_food[i])
            if self.taking_food[i] == 1:
                self.doesnt_want_to_buy_food = 0


    def set_waiting_time(self, waiting_time):
        self.waiting_time = waiting_time
        # update rating
        if waiting_time > TIME_CAN_WAIT:
            decrease = (self.waiting_time//TIME_CAN_WAIT)*0.5
            print(f"Customer {self.id} waited for {self.waiting_time:7f} and decreased the rating by {decrease}")    
            self.rating = self.rating - decrease

    def reset_waiting_time(self):
        self.waiting_time = 0

    def pick_food_to_queue(self):
        indices_with_one = [index for index, value in enumerate(self.taking_food) if value == 1]
        if not indices_with_one:
            return -1
        # Pick a random index with uniform rate
        random_index = random.choice(indices_with_one)
        return random_index
    
    def is_full_desired_dish(self):
        if self.doesnt_want_to_buy_food == 1:
            return 0
        for i in range(4):
            if self.taking_food[i] == 1:
                return 0
        return 1
    
    def is_not_want_to_eat(self):
        return self.doesnt_want_to_buy_food


'''
brief:  
    Variable:    
        NUMBER_OF_TICKET_SERVERS
        TIME_TICKET_SERVICE --> the lambda of exponential distribution
        server_ticket
    Function:
        serve_ticket: serve customers in ticket desks
'''


class Restaurant:
    def __init__(self, env):
        self.NUMBER_OF_TICKET_SERVERS = 2
        self.TIME_TICKET_SERVICE = 5
        self.NUMBER_OF_DRINKS_SERVICE = 2
        self.TIME_DRINKS_SERVICE = 5
        self.NUMBER_OF_APPETIZER_SERVICE = 2
        self.TIME_OF_APPETIZER_SERVICE = 5
        self.NUMBER_OF_MAINCOURSE_SERVICE = 2
        self.TIME_OF_MAINCOURSE_SERVICE = 5
        self.NUMBER_OF_DESSERTS_SERVICE = 2    
        self.TIME_DESSERTS_SERVICE = 5
        self.TIME_SEAT = 2
        self.NUMBER_OF_SEATS= 99
        self.server_ticket = simpy.Resource(env, self.NUMBER_OF_TICKET_SERVERS)
        self.server_mainCourses = simpy.Resource(env, self.NUMBER_OF_MAINCOURSE_SERVICE)
        self.server_appetizer = simpy.Resource(env, self.NUMBER_OF_APPETIZER_SERVICE)
        self.server_drinks = simpy.Resource(env, self.NUMBER_OF_DRINKS_SERVICE)
        self.server_desserts = simpy.Resource(env, self.NUMBER_OF_DESSERTS_SERVICE)
        self.server_Seat_eat = simpy.Resource(env, self.NUMBER_OF_SEATS)
        self.choosing_food_queue =  queue.Queue()

    def serve_ticket(self, env, consumer, arrival_time):
        with self.server_ticket.request() as req:
            yield req
            consumer.arrival_time = arrival_time
            print(f'Customer {consumer.id:3} entered ticket at {env.now:7.3f}')
            serve_time = random.expovariate(self.TIME_TICKET_SERVICE)
            yield env.timeout(serve_time)
            consumer.set_waiting_time(env.now - consumer.arrival_time)
            print(f'Customer {consumer.id:3} left ticket at {env.now:7.3f}')
            self.choose_food(env,consumer)
     
    def choose_food(self,env,customer ):
        chosen_food = customer.pick_food_to_queue()      
        if chosen_food == 0:
            env.process(self.serve_drinks(env,customer))
        elif chosen_food == 1:
            env.process(self.serve_appetizer(env,customer))
        elif chosen_food == 2:
            env.process(self.serve_mainCourses(env,customer))
        elif chosen_food == 3:
            env.process(self.serve_desserts(env,customer))
        elif customer.is_full_desired_dish():
            env.process(self.serve_seat_eat(env,customer))
        elif customer.doesnt_want_to_eat():
            self.leave_n_rate(env,customer)
        else:
            print("Something went wrong!")

    def serve_drinks(self, env, consumer):
        with  self.server_drinks.request() as req:
            yield req
            consumer.arrival_time = env.now
            print(f'Customer {consumer.id:3} entered drinks at {env.now:7.3f}')
            serve_time = random.expovariate(self.TIME_DRINKS_SERVICE)
            yield env.timeout(serve_time)
            consumer.set_waiting_time(env.now - consumer.arrival_time)
            self.choosing_food_queue.put(consumer)
            consumer.taking_food[0] = 0
            print(f'Customer {consumer.id:3} left drinks at {env.now:7.3f}')
            self.choose_food(env,consumer)
    
    def serve_appetizer(self, env, consumer):
        with  self.server_appetizer.request() as req:
            yield req
            consumer.arrival_time = env.now
            print(f'Customer {consumer.id:3} entered appetizer at {env.now:7.3f}')
            serve_time = random.expovariate(self.TIME_OF_APPETIZER_SERVICE)
            yield env.timeout(serve_time)
            consumer.set_waiting_time(env.now - consumer.arrival_time)
            self.choosing_food_queue.put(consumer)
            consumer.taking_food[1] = 0
            print(f'Customer {consumer.id:3} left appetizer at {env.now:7.3f}')
            self.choose_food(env,consumer)

    def serve_mainCourses(self, env, consumer):
        with  self.server_mainCourses.request() as req:
            yield req
            consumer.arrival_time = env.now
            print(f'Customer {consumer.id:3} entered mainCourse at {env.now:7.3f}')
            serve_time = random.expovariate(self.TIME_OF_MAINCOURSE_SERVICE)
            yield env.timeout(serve_time)
            consumer.set_waiting_time(env.now - consumer.arrival_time)
            self.choosing_food_queue.put(consumer)
            consumer.taking_food[2] = 0
            print(f'Customer {consumer.id:3} left mainCourse at {env.now:7.3f}')
            self.choose_food(env,consumer)
    
    def serve_desserts(self, env, consumer):
        with  self.server_desserts.request() as req:
            yield req
            consumer.arrival_time = env.now
            print(f'Customer {consumer.id:3} entered desserts at {env.now:7.3f}')
            serve_time = random.expovariate(self.TIME_DESSERTS_SERVICE)
            yield env.timeout(serve_time)
            consumer.set_waiting_time(env.now - consumer.arrival_time)
            self.choosing_food_queue.put(consumer)
            consumer.taking_food[3] = 0
            print(f'Customer {consumer.id:3} left desserts at {env.now:7.3f}')
            self.choose_food(env,consumer)

    def serve_seat_eat(self,env,consumer):
        with self.server_Seat_eat.request() as req:
            yield req
            #consumer.set_waiting_time(env.now - consumer.arrival_time)
            print(f'Customer {consumer.id:3} entered seat to eat at {env.now:7.3f}')
            serve_time = random.expovariate(self.TIME_SEAT)
            yield env.timeout(serve_time)
            print(f'Customer {consumer.id:3} has finished their dinner at {env.now:7.3f}')
            self.leave_n_rate(env,consumer)

    def leave_n_rate(self,env,consumer):
        print(f"Customer {consumer.id:3} left the restaurant at {env.now:7.3f} and rated {consumer.rating} stars")


def generate(env, customers, TIME_INTERVAL, server_generator, restaurant):
    with server_generator.request() as req:
        yield req
        i = 0
        while True:
            consumer = Customer(i, arrival_time=env.now)
            consumer.classify()
            customers.append(consumer)
            print(
                f'Customer {consumer.id:3} arrived at {consumer.arrival_time:7.3f}')
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


env = simpy.Environment()
customers = list(())
restaurant = Restaurant(env)
server_generator = simpy.Resource(env, 1)

env.process(generate(env, customers, TIME_INTERVAL,
            server_generator, restaurant))

env.run(until=60*5)