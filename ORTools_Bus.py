import pygame
import random
import cv2 as cv
import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, floyd_warshall, bellman_ford
import time
import matplotlib
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
matplotlib.use("Agg")
import matplotlib.backends.backend_agg as agg
import pylab
import warnings
import ortools
from functools import lru_cache
warnings.filterwarnings("ignore", category=DeprecationWarning)


from pygame.locals import (
    K_ESCAPE,
    KEYDOWN,
    MOUSEBUTTONDOWN,
    DOUBLEBUF
)

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 840
MAPNAME = "absMap.jpg"
BUSNUM = 2
GRANULARITY = 30
PASSENGERNUM = 10
PASSCHANCE = 1 # 0.00005
SPEED = 1
CAPACITY = 60
SHOW_CONNECTIONS = False
SHOW_STOPS = False

color1 = (0, 0, 0)
color2 = (0, 0, 0)
def getStops(granul):
    pixels = cv.imread(MAPNAME)
    condRO = np.logical_and(pixels[:, :, 2] > color1[0]-30, pixels[:, :, 2] < color1[0]+30)
    condGO = np.logical_and(pixels[:, :, 1] > color1[1]-30, pixels[:, :, 1] < color1[1]+30)
    condBO = np.logical_and(pixels[:, :, 0] > color1[2]-30, pixels[:, :, 0] < color1[2]+30)
    cond1O = np.logical_and(condRO, condGO)
    condOrange = np.logical_and(cond1O, condBO)


    condRY = np.logical_and(pixels[:, :, 2] > color2[0]-30, pixels[:, :, 2] < color2[0]+30)
    condGY = np.logical_and(pixels[:, :, 1] > color2[1]-30, pixels[:, :, 1] < color2[1]+30)
    condBY = np.logical_and(pixels[:, :, 0] > color2[2]-30, pixels[:, :, 0] < color2[2]+30)
    cond1Y = np.logical_and(condRY, condGY)
    condYellow = np.logical_and(cond1Y, condBY)

    cond = np.logical_or(condOrange, condYellow)

    coords = np.column_stack(np.where(cond))

    temp = []
    for a in coords:
        close = False
        for b in temp:
            if np.sqrt((a[0]-b[0])**2+(a[1]-b[1])**2) < granul:
                close = True
        if not close:
            temp.append(a)
    ID = 0
    if SHOW_STOPS:
        size = (7,7)
    else:
        size = (0,0)
    for i in temp:
        busStops.add(BusStop(ID, i[1], i[0], size))
        ID += 1



class button(pygame.sprite.Sprite):
    def __init__(self, startX, startY, sizeX, sizeY, text):
        pygame.sprite.Sprite.__init__(self)
        self.surf = pygame.Surface((sizeX, sizeY))
        self.surf.fill((175, 175, 175))
        self.rect = self.surf.get_rect(center=(startX, startY))
        self.text = text

    def update(self):
        self.surf.fill((175, 175, 175))
        text = font.render(self.text, True, (0, 0, 0))
        text_rect = text.get_rect(center=(self.surf.get_width() / 2, self.surf.get_height() / 2))
        self.surf.blit(text, text_rect)



class BusStop(pygame.sprite.Sprite):
    def __init__(self, stopid, x, y, size):
        pygame.sprite.Sprite.__init__(self)
        self.id = stopid
        self.loc = (x, y)
        self.surf = pygame.Surface(size)
        self.surf.fill((0, 0, 0))
        self.rect = self.surf.get_rect(center=(x, y))
    def update(self):
        pass

class Bus(pygame.sprite.Sprite):
    def __init__(self, id,  size, startStop, speed, gran):
        super(Bus, self).__init__()
        self.id = id
        self.surf = pygame.Surface((size, size))
        self.color = list(np.random.choice(range(256), size=3))
        self.surf.fill(self.color)
        self.rect = self.surf.get_rect(center=(startStop.loc[0], startStop.loc[1]))
        self.endStop = startStop
        self.nextStop = startStop
        self.prevStop = startStop
        self.loc = startStop.loc
        self.speed = speed
        self.granularity = gran
        self.path = []
        self.assignedPass = []
        self.newPass = False
        self.newLog = False
        self.log = None
        self.plan = []
        self.manager = None
        self.data = None
        self.routing = None
        self.lastSol = None
        self.search_parameters = None
        self.newPass = False
        self.solution = None
        self.calctimes = []
        self.newPass = True

    def getPath(self):
        if pred[self.endStop.id][self.prevStop.id] != -9999:
            self.path = [self.endStop.id]
            while pred[self.path[-1]][self.prevStop.id] != self.path[-1]:
                self.path.append(pred[self.prevStop.id][self.path[-1]])
            self.path.append(self.prevStop.id)

    def getLog(self):
        self.newLog = False
        return self.log

    def stopFromId(self, id):
        for stop in busStops:
            if stop.id == id:
                return stop

    def getEndStop(self):
        if len(self.plan) > 1:
            self.plan = self.plan[1:]
            self.endStop = self.stopFromId(self.plan[0])
        self.getPath()

    def getNextStop(self):
        self.prevStop = self.nextStop
        if self.prevStop == self.endStop or self.newPass:
            self.endStop.surf = pygame.transform.scale(self.prevStop.surf, (0, 0))
            self.endStop.surf.fill((0,0,0))
            self.getEndStop()
            controlText = "Bus " + str(self.id) + " is now heading to " + str(self.endStop.loc)
            self.log = font.render(controlText, True, (0, 0, 0), (255, 255, 255))
            self.newLog = True
            self.endStop.surf = pygame.transform.scale(self.nextStop.surf,(5,5))
            self.endStop.surf.fill(self.color)
            if self.path != []:
                for stop in busStops:
                    if stop.id == self.path[-1]:
                        self.nextStop = stop
            self.newPass = False
        else:
            self.path = self.path[:-1]
            for stop in busStops:
                if stop.id == self.path[-1]:
                    self.nextStop = stop

    def create_data_model(self, distances, busnum, passengers, buses, capacity):
        fullStops = []
        emptyStops = []
        capacities = []
        starts = []
        ends = []
        pickDeliver = []
        passengerData = {}
        orderedPass = []
        for bus in buses:
            fullStops.append(bus.prevStop.id)
            capacities.append(capacity)
            starts.append(bus.id + 1)
            ends.append(0)
        for passenger in passengers:
            if passenger.start.id != -1:
                fullStops.append(passenger.start.id)
                fullStops.append(passenger.end.id)
                passengerData[passenger.start.id] = 0
                passengerData[passenger.end.id] = 0
                pickDeliver.append([passenger.start.id, passenger.end.id])
                orderedPass.append(passenger.start.id)
                orderedPass.append(passenger.end.id)
        orderedPass.sort()
        for i in range(len(pickDeliver)):
            passengerData[pickDeliver[i][0]] = orderedPass.index(pickDeliver[i][0]) + busnum + 1
            passengerData[pickDeliver[i][1]] = orderedPass.index(pickDeliver[i][1]) + busnum + 1
            pickDeliver[i][0] = orderedPass.index(pickDeliver[i][0]) + busnum + 1
            pickDeliver[i][1] = orderedPass.index(pickDeliver[i][1]) + busnum + 1
        for i in range(len(busStops)):
            if i not in fullStops:
                emptyStops.append(i)
        solDistances = np.delete(distances, emptyStops, axis=0)
        solDistances = np.delete(solDistances, emptyStops, axis=1)
        solDistances = np.vstack([np.zeros(len(solDistances[0])), solDistances])
        solDistances = np.hstack([np.zeros((len(solDistances[0]) + 1, 1)), solDistances])
        data = {'distance_matrix': solDistances, "num_vehicles": busnum, 'depot': 0, 'vehicle_capacities': capacities,
                'starts': starts, 'ends': ends, 'passengerData': passengerData, 'pickups_deliveries': pickDeliver,
                "initial_routes": self.lastSol}
        return data

    def distance_callback(self, from_index, to_index):
        from_node = self.manager.IndexToNode(from_index)
        to_node = self.manager.IndexToNode(to_index)
        return self.data["distance_matrix"][from_node][to_node]

    def demand_callback(self, from_index):
        return 1

    def print_solution(self, data, manager, routing, solution):
        print(f"Objective: {solution.ObjectiveValue()}")
        max_route_distance = 0
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            plan_output = f"Route for vehicle {vehicle_id}:\n"
            route_distance = 0
            while not routing.IsEnd(index):
                plan_output += f" {manager.IndexToNode(index)} -> "
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            plan_output += f"{manager.IndexToNode(index)}\n"
            plan_output += f"Distance of the route: {route_distance}m\n"
            print(plan_output)
            max_route_distance = max(route_distance, max_route_distance)
        print(f"Maximum of the route distances: {max_route_distance}m")

    def getRoute(self):
        self.data = self.create_data_model(dijkstra, BUSNUM, passengers, buses, CAPACITY)
        self.manager = pywrapcp.RoutingIndexManager(len(self.data["distance_matrix"]), self.data["num_vehicles"], self.data["starts"], self.data["ends"])
        self.routing = pywrapcp.RoutingModel(self.manager)
        demand_callback_index = self.routing.RegisterUnaryTransitCallback(self.demand_callback)
        self.routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, self.data["vehicle_capacities"], True, "Capacity")
        transit_callback_index = self.routing.RegisterTransitCallback(self.distance_callback)
        self.routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        self.search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        self.search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        dimension_name = "Distance"
        self.routing.AddDimension(transit_callback_index, 0, 10000, True, dimension_name)
        distance_dimension = self.routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100)
        for request in self.data["pickups_deliveries"]:
            pickup_index = self.manager.NodeToIndex(request[0])
            delivery_index = self.manager.NodeToIndex(request[1])
            self.routing.AddPickupAndDelivery(pickup_index, delivery_index)
            self.routing.solver().Add(self.routing.VehicleVar(pickup_index) == self.routing.VehicleVar(delivery_index))
            self.routing.solver().Add(distance_dimension.CumulVar(pickup_index) <= distance_dimension.CumulVar(delivery_index))

    def routeToList(self, solution, routing, manager):
        routes = []
        for route_nbr in range(routing.vehicles()):
            index = routing.Start(route_nbr)
            route = [manager.IndexToNode(index)]
            while not routing.IsEnd(index):
                index = solution.Value(routing.NextVar(index))
                route.append(manager.IndexToNode(index))
            routes.append(route)
        return routes


    def update(self):
        if self.newPass:
            self.getRoute()
            self.solution = self.routing.SolveWithParameters(self.search_parameters)
            self.lastSol = self.routeToList(self.solution, self.routing, self.manager)
            self.plan = []
            self.plan.append(1)
            for i in self.lastSol[0][1:-1]:
                self.plan.append(list(self.data['passengerData'].keys())[list(self.data['passengerData'].values()).index(i)])
            self.plan.append(0)
            self.newPass = False
        xdiff = self.nextStop.loc[0] - self.rect.x
        ydiff = self.nextStop.loc[1] - self.rect.y
        if abs(xdiff) < 2 and abs(ydiff) < 2:
            self.getNextStop()
        if xdiff > 0:
            self.rect.move_ip(self.speed, 0)
        if ydiff > 0:
            self.rect.move_ip(0, self.speed)
        if xdiff < 0:
            self.rect.move_ip(-self.speed, 0)
        if ydiff < 0:
            self.rect.move_ip(0, -self.speed)
        self.loc = (self.rect.center[0], self.rect.center[1])

class Passenger(pygame.sprite.Sprite):
    def __init__(self, id):
        pygame.sprite.Sprite.__init__(self)
        self.id = id
        self.surf = pygame.Surface((7, 7))
        self.surf.fill((0, 0, 255))
        self.rect = self.surf.get_rect(center=(tempStop.loc[0], tempStop.loc[1]))
        self.waitTime = 0
        self.travelTime = 0
        self.start = tempStop
        self.bus = None
        self.end = tempStop
        self.onBus = False
        self.newLog = False
        self.initial_solution = None


    def getLog(self):
        passText = "Passenger "+ str(self.id) +" arrived at destination after " + str(np.round(self.waitTime, 3)) + " seconds of time waiting and " + str(np.round(self.travelTime, 3)) +" seconds of Travel"
        passengerLog = font.render(passText, True, (0, 0, 0), (255, 255, 255))
        self.newLog = False
        return passengerLog


    def despawn(self):
        self.start = tempStop
        self.end = tempStop
        if self.bus is not None:
            for passenger in self.bus.assignedPass:
                if passenger.id == self.id:
                    self.bus.assignedPass.remove(passenger)
        self.bus = None


    def resetPassenger(self):
        self.travelTime = 0
        self.waitTime = 0
        self.rect.inflate(5, 5)
        startnum = random.randint(0, len(busStops)-1)
        endnum = random.randint(0, len(busStops)-1)
        while dijkstra[startnum][endnum] > 10000:
            startnum = random.randint(0, len(busStops)-1)
            endnum = random.randint(0, len(busStops)-1)
        for stop in busStops:
            if stop.id == startnum:
                start = stop
            if stop.id == endnum:
                end = stop
        self.start = start
        self.end = end
        if self.bus is not None:
            for passenger in self.bus.assignedPass:
                if passenger.id == self.id:
                    self.bus.assignedPass.remove(passenger)
        self.bus = None

    def update(self):
        spawn = False
        if self.start.id == -1:
            if random.random() < PASSCHANCE:
                spawn = True
        elif dijkstra[self.start.id][self.end.id] > 10000:
            self.resetPassenger()
        if spawn:
            self.resetPassenger()
            control.newPass = True
        if self.bus is not None:
            if not self.onBus:
                self.rect.top = self.start.rect.top
                self.rect.left = self.start.rect.left
                if abs(self.start.loc[0] - self.bus.rect.centerx) <= 5 and abs(self.start.loc[1] - self.bus.rect.centery) <= 5:
                    self.onBus = True
                self.waitTime += 1
            else:
                self.travelTime += 1
                self.rect.top = 9999
                self.rect.left = 9999
                if abs(self.end.loc[0] - self.bus.rect.centerx) <= 5 and abs(self.end.loc[1] - self.bus.rect.centery) <= 5:
                    self.onBus = False
                    #self.waitTime = self.waitTime / dijkstra[self.start.id][self.end.id]
                    #self.travelTime = self.travelTime / dijkstra[self.start.id][self.end.id]
                    self.despawn()
                    self.newLog = True
                    totalTimes.append(self.travelTime + self.waitTime)
                    travelTimes.append(self.travelTime)
                    waitTimes.append(self.waitTime)
        else:
            self.rect.top = self.start.rect.top
            self.rect.left = self.start.rect.left

class controlCentre(pygame.sprite.Sprite):
    def __init__(self, delay=1):
        pygame.sprite.Sprite.__init__(self)
        self.newLog = False
        self.log = None
        self.delay = delay

    def assignBus(self, passenger):
        if passenger.start.id != -1:
            dist = 100000
            route = dijkstra[passenger.start.id][passenger.end.id]
            while route > dist:
                passenger.resetPassenger()
                route = dijkstra[passenger.start.id][passenger.end.id]
            assignedBus = None
            for bus in buses:
                if len(bus.path) > self.delay:
                    toStart = dijkstra[passenger.start.id][bus.path[-self.delay]]
                else:
                    toStart = dijkstra[passenger.start.id][bus.endStop.id]
                if toStart + route < dist:
                    if len(bus.assignedPass) < CAPACITY:
                        dist = toStart + route
                        assignedBus = bus
            if assignedBus is not None:
                assignedBus.assignedPass.append(passenger)
                assignedBus.newPass = True
                controlText = "Passenger " + str(passenger.id) + " has been assigned bus " + str(assignedBus.id)
                self.log = font.render(controlText, True, (0, 0, 0), (255, 255, 255))
                self.newLog = True
            passenger.bus = assignedBus

    def getLog(self):
        self.newLog = False
        return self.log

    def update(self, passenger):
        if passenger.bus is None:
            self.assignBus(passenger)






clock = pygame.time.Clock()

pygame.init()

font = pygame.font.Font(None, 24)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)


start_time = time.time()


control = controlCentre()

busStops = pygame.sprite.Group()
getStops(GRANULARITY)


tempStop = BusStop(-1, 99999, 99999, (0,0))
busStops.add(tempStop)

buses = pygame.sprite.Group()
ID = 0
def getStart(Id):
    for stop in busStops:
        if stop.id == Id:
            return stop
def getStop(pos):
    for stop in busStops:
        if (abs(stop.loc[0]-pos[0]) < 10) and (abs(stop.loc[1]-pos[1]) < 10):
            return stop



for i in range(BUSNUM):
    start = getStart(random.randint(0, len(busStops)-1))
    buses.add(Bus(ID, 10, start, SPEED, GRANULARITY))
    ID += 1

passengers = pygame.sprite.Group()
ID = 0
for i in range(PASSENGERNUM):
    startnum = random.randint(0, len(busStops)-1)
    endnum = random.randint(0, len(busStops)-1)
    for stop in busStops:
        if stop.id == startnum:
            start = stop
        if stop.id == endnum:
            end = stop
    passengers.add(Passenger(ID))
    ID += 1



distanceMatrix = []
adjMatrix = []
for stop in busStops:
    temp = []
    for stop2 in busStops:
        temp.append(0)
    distanceMatrix.append(temp)

for stop in busStops:
    temp = []
    for stop2 in busStops:
        temp.append(0)
    adjMatrix.append(temp)

for stop in busStops:
    for next in busStops:
        dist = np.round(np.sqrt((stop.loc[0]-next.loc[0])**2+(stop.loc[1]-next.loc[1])**2))
        if dist < GRANULARITY*1.5:
            if stop.id != next.id:
                distanceMatrix[stop.id][next.id] = dist
                adjMatrix[stop.id][next.id] = 1




graph = csr_matrix(distanceMatrix)
dijkstra, pred = dijkstra(graph, return_predecessors=True)

print("-------------")
print("--- %s seconds ---" % (time.time() - start_time))




# Control Button Setup

buttonSpeed = button(1175, 500, 160, 40, "Clock Speed: 120")
buttonPlusSpeed = button(1150, 550, 40, 40, "+")
buttonMinusSpeed = button(1200, 550, 40, 40, "-")

buttonPassenger = button(1175, 600, 260, 40, ("Passenger Spawn Rate: " + str(PASSCHANCE*100) + "%"))
buttonPlusPassenger = button(1150, 650, 40, 40, "+")
buttonMinusPassenger = button(1200, 650, 40, 40, "-")


buttonPause = button(1350, 550, 40, 40, "||")

buttonResetGraph = button(1125, 425, 80, 40, "Reset")
buttonSwitchGraph = button(1275, 425, 80, 40, "Switch")

buttons = pygame.sprite.Group()
buttons.add(buttonPlusSpeed, buttonMinusSpeed, buttonSpeed)
buttons.add(buttonPassenger, buttonPlusPassenger, buttonMinusPassenger)
buttons.add(buttonPause)
buttons.add(buttonResetGraph)
buttons.add(buttonSwitchGraph)

clockVar = 120
totalTimes = []
travelTimes = []
waitTimes = []
capacities = []


fig = pylab.figure(figsize=[4, 4], dpi=100)
ax = fig.gca()

canvas = agg.FigureCanvasAgg(fig)
window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF)
screen = pygame.display.get_surface()
size = canvas.get_width_height()

graphVar = 0

times = [waitTimes, travelTimes]


clockPaused = clockVar
paused = False
running = True

pt = font.render("No Passenger Data", True, (0, 0, 0), (255, 255, 255))
pr = pt.get_rect()
pr.center = (325, 700)

ct = font.render("No Conrol Data", True, (0, 0, 0), (255, 255, 255))
cr = ct.get_rect()
cr.center = (325, 750)

bt = font.render("No Bus Data", True, (0, 0, 0), (255, 255, 255))
br = bt.get_rect()
br.center = (325, 800)

while running:
    counts, bins = np.histogram(travelTimes)
    ax.cla()
    if graphVar == 0:
        ax.hist(travelTimes, color="#1f3b87", histtype='step')
        ax.hist(waitTimes, color="#55bd15", histtype='step')
        ax.axvline(np.mean(travelTimes), color="#1f3b87")
        ax.axvline(np.mean(waitTimes), color="#55bd15")
        ax.set_title("Wait and Travel Times")
        ax.set_xlabel("Clock Ticks")
        ax.set_ylabel("Frequency")
        ax.legend(["Travel time", "Wait time"], loc="upper right")
    elif graphVar == 1:
        if times != []:
            sns.histplot(totalTimes, ax=ax, multiple='stack')
        ax.set_title("Total Transportation Time")
        ax.set_xlabel("Clock Ticks")
        ax.set_ylabel("Frequency")
    if graphVar == 2:
        capacities = []
        for bus in buses:
            capacities.append(len(bus.assignedPass))
        sns.barplot(capacities, ax=ax, orient='y', color='red')
        ax.set_ylim([-0.5, BUSNUM - 0.5])
        ax.set_title("Number of Passengers on a Bus")
        ax.set_xlabel("Passengers")
        ax.set_xlim([0, CAPACITY])
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    screen.blit(surf, (1000,0))
    pygame.display.flip()
    for event in pygame.event.get():
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if buttonPlusSpeed.rect.collidepoint(event.pos):
                clockVar += 1
                buttonSpeed.text = "Clock Speed: " + str(clockVar)
            if buttonMinusSpeed.rect.collidepoint(event.pos):
                clockVar -= 1
                buttonSpeed.text = "Clock Speed: " + str(clockVar)
            if buttonPause.rect.collidepoint(event.pos):
                if paused:
                    paused = False
                    clockVar = clockPaused
                else:
                    clockPaused = clockVar
                    clockVar = 1
                    paused = True
            if buttonPlusPassenger.rect.collidepoint(event.pos):
                if PASSCHANCE < 100:
                    PASSCHANCE = PASSCHANCE*2
                    PASSCHANCE = np.round(PASSCHANCE, 5)
                    buttonPassenger.text = "Passenger Spawn Rate: " + str(PASSCHANCE)
            if buttonMinusPassenger.rect.collidepoint(event.pos):
                if PASSCHANCE > 0:
                    PASSCHANCE = PASSCHANCE/2
                    PASSCHANCE = np.round(PASSCHANCE, 5)
                    buttonPassenger.text = "Passenger Spawn Rate: " + str(PASSCHANCE)
            if buttonSwitchGraph.rect.collidepoint(event.pos):
                if graphVar == 2:
                    graphVar = 0
                else:
                    graphVar += 1
            if buttonResetGraph.rect.collidepoint(event.pos):
                totalTimes =[]
                travelTimes = []
                waitTimes = []
    mapPicture = pygame.image.load(MAPNAME).convert()
    screen.fill((255, 255, 255))
    screen.blit(mapPicture, (0, 0))
    for entity in buttons:
        entity.update()
        screen.blit(entity.surf, entity.rect)
    for entity in buses:
        entity.update()
        screen.blit(entity.surf, entity.rect)
        if entity.newLog:
            bt = entity.getLog()
            br = bt.get_rect()
            br.center = (620, 770)
        screen.blit(entity.surf, entity.rect)
        screen.blit(bt, br)
    for entity in passengers:
        control.update(entity)
        screen.blit(entity.surf, entity.rect)
        entity.update()
        if control.newLog:
            ct = control.getLog()
            cr = ct.get_rect()
            cr.center = (620, 735)
        if entity.newLog:
            pt = entity.getLog()
            pr = pt.get_rect()
            pr.center = (620, 700)
        screen.blit(entity.surf, entity.rect)
    screen.blit(ct, cr)
    screen.blit(pt, pr)
    for entity in busStops:
        entity.update()
        screen.blit(entity.surf, entity.rect)
    if SHOW_CONNECTIONS:
        for stop in busStops:
            for next in busStops:
                if adjMatrix[stop.id][next.id] == 1:
                    pygame.draw.line(screen, (255, 130, 255), (next.loc[0], next.loc[1]), (stop.loc[0], stop.loc[1]), 2)
    clock.tick(clockVar)