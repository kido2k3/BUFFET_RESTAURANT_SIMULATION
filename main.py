import simpy
import random


TIME_INTERVAL = [30/60, 100/60, 30/60, 15/60, 5/60]
# --> the lambda of exponential distribution
TIME_CAN_WAIT = 8
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

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
'''


class Customer:
    def __init__(self, id, arrival_time=0):
        self.id = id
        self.arrival_time = arrival_time
        self.waiting_time = 0
        self.rating = 5
        self.left_time = 0
        self.take_food = [1, 1, 1, 1]

    def set_waiting_time(self, waiting_time):
        self.waiting_time = waiting_time
        # update rating
        if waiting_time > TIME_CAN_WAIT:
            self.rating = self.rating - (self.waiting_time//TIME_CAN_WAIT)*0.5

    def reset_waiting_time(self):
        self.waiting_time = 0


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
        self.TIME_TICKET_SERVICE = 2
        self.server_ticket = simpy.Resource(env, self.NUMBER_OF_TICKET_SERVERS)

    def serve_ticket(self, env, consumer, arrival_time):
        with self.server_ticket.request() as req:
            yield req
            consumer.set_waiting_time(env.now - arrival_time)
            print(f'Customer {consumer.id:3} entered ticket at {env.now:7.3f}')
            serve_time = random.expovariate(self.TIME_TICKET_SERVICE)
            yield env.timeout(serve_time)
            print(f'Customer {consumer.id:3} left ticket at {env.now:7.3f}')


def generate(env, customers, TIME_INTERVAL, server_generator, restaurant):
    with server_generator.request() as req:
        yield req
        i = 0
        while True:
            consumer = Customer(i, arrival_time=env.now)
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
