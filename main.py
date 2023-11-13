import simpy
import random


TIME_INTERVAL = 100
NUMBER_OF_CUSTOMERS = 20
TIME_WAITING_DECREASE_RATING = 0.01
RANDOM_SEED = 42
random.seed(RANDOM_SEED)


class Customer:
    def __init__(self, id, arrival_time=0):
        self.id = id
        self.arrival_time = arrival_time
        self.waiting_time = 0
        self.rating = 5
        self.left_time = 0

    def set_waiting_time(self, waiting_time):
        self.waiting_time = waiting_time
        # update rating
        self.rating = self.rating - self.waiting_time//TIME_WAITING_DECREASE_RATING

    def reset_waiting_time(self):
        self.waiting_time = 0


class Restaurant:
    def __init__(self, env):
        self.NUMBER_OF_TICKET_SERVERS = 1
        self.TIME_TICKET_SERVICE = 25
        self.server_ticket = simpy.Resource(env, self.NUMBER_OF_TICKET_SERVERS)

    def serve_ticket(self, env, consumer, arrival_time):
        with self.server_ticket.request() as req:
            yield req
            consumer.set_waiting_time(env.now - arrival_time)
            print(f'Customer {consumer.id:3} entered ticket at {env.now:7.3f}')
            serve_time = random.expovariate(self.TIME_TICKET_SERVICE)
            yield env.timeout(serve_time)
            print(f'Customer {consumer.id:3} left ticket at {env.now:7.3f}')


def generate(env, customers, NUMBER_OF_CUSTOMERS, TIME_INTERVAL, server_generator, restaurant):
    with server_generator.request() as req:
        yield req
        for i in range(NUMBER_OF_CUSTOMERS):
            consumer = Customer(i, arrival_time=env.now)
            customers.append(consumer)
            print(
                f'Customer {consumer.id:3} arrived at {consumer.arrival_time:7.3f}')
            env.process(restaurant.serve_ticket(
                env, consumer, consumer.arrival_time))
            arrival_between = random.expovariate(TIME_INTERVAL)
            yield env.timeout(arrival_between)


env = simpy.Environment()
customers = list(())
restaurant = Restaurant(env)
server_generator = simpy.Resource(env, 1)

env.process(generate(env, customers, NUMBER_OF_CUSTOMERS,
            TIME_INTERVAL, server_generator, restaurant))

env.run(until=60*5)
