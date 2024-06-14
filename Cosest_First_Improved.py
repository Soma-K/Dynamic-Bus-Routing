#Control Centre has delay argument, default delay = 1, equal to recalculation based on next stop

import pygame
import random
import cv2 as cv
import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, floyd_warshall, bellman_ford
import time
import matplotlib
import seaborn as sns
import matplotlib.backends.backend_agg as agg
import pylab
import warnings
import pandas as pd
matplotlib.use("Agg")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


from pygame.locals import (
    K_ESCAPE,
    KEYDOWN,
    MOUSEBUTTONDOWN,
    DOUBLEBUF
)

SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 840
MAPNAME = "absMap.jpg"
BUSNUM = 5
GRANULARITY = 5
PASSENGERNUM = 500
PASSCHANCE =  0.00004
SPEED = 1
CAPACITY = 30
SHOW_CONNECTIONS = False
SHOW_STOPS = False
CLUSTERING = True
DELAY = 1000
NUM_CLUSTERS = 10
STD = 25
MAX_DISTANCE = 100000


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

    def getPath(self):
        if pred[self.endStop.id][self.prevStop.id] != -9999:
            self.path = [self.endStop.id]
            while pred[self.path[-1]][self.prevStop.id] != self.path[-1]:
                self.path.append(pred[self.prevStop.id][self.path[-1]])
            self.path.append(self.prevStop.id)

    def getLog(self):
        self.newLog = False
        return self.log

    def getEndStop(self):
        dist = 10000
        getOn = True
        closestPass = None
        for passenger in self.assignedPass:
            if not passenger.onBus:
                if dijkstra[passenger.start.id][self.prevStop.id] < dist:
                    dist = dijkstra[passenger.start.id][self.nextStop.id]
                    closestPass = passenger
                    getOn = True
            else:
                if dijkstra[passenger.end.id][self.prevStop.id] < dist:
                    dist = dijkstra[passenger.end.id][self.nextStop.id]
                    closestPass = passenger
                    getOn = False
        if getOn:
            self.endStop = closestPass.start
        else:
            self.endStop = closestPass.end
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
            for stop in busStops:
                if stop.id == self.path[-1]:
                    self.nextStop = stop
            if self.newPass:
                self.newPass = False
        else:
            self.path = self.path[:-1]
            for stop in busStops:
                if stop.id == self.path[-1]:
                    self.nextStop = stop


    def update(self):
        xdiff = self.nextStop.loc[0] - self.rect.x
        ydiff = self.nextStop.loc[1] - self.rect.y
        if abs(xdiff) < 2 and abs(ydiff) < 2:
            if not self.assignedPass == []:
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
        if not CLUSTERING:
            startnum = random.randint(0, len(busStops)-1)
            endnum = random.randint(0, len(busStops)-1)
        else:
            startnum = int(np.random.normal(random.choice(clusters), STD, 1))
            if startnum < 0 or startnum > len(busStops)-1:
                startnum = random.randint(0, len(busStops) - 1)
            endnum = int(np.random.normal(random.choice(clusters), STD, 1))
            if endnum < 0 or endnum > len(busStops)-1:
                endnum = random.randint(0, len(busStops) - 1)
        while dijkstra[startnum][endnum] > 10000:
            if not CLUSTERING:
                startnum = random.randint(0, len(busStops) - 1)
                endnum = random.randint(0, len(busStops) - 1)
            else:
                startnum = int(np.random.normal(random.choice(clusters), STD, 1))
                if startnum < 0 or startnum > len(busStops) - 1:
                    startnum = random.randint(0, len(busStops) - 1)
                endnum = int(np.random.normal(random.choice(clusters), STD, 1))
                if endnum < 0 or endnum > len(busStops) - 1:
                    endnum = random.randint(0, len(busStops) - 1)
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
                    normWaitTimes.append(self.waitTime / dijkstra[self.start.id][self.end.id])
                    normTravelTimes.append(self.travelTime / dijkstra[self.start.id][self.end.id])
                    normTotalTimes.append((self.travelTime / dijkstra[self.start.id][self.end.id]) + (self.waitTime / dijkstra[self.start.id][self.end.id]))
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
                        if toStart + route < MAX_DISTANCE:
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


control = controlCentre(delay=DELAY)

busStops = pygame.sprite.Group()
getStops(GRANULARITY)


tempStop = BusStop(-1, 99999, 99999, (0,0))
busStops.add(tempStop)

clusters = []
for i in range(NUM_CLUSTERS):
    clusters.append(random.randint(0, len(busStops)-1))



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

buttonBus = button(1175, 700, 260, 40, ("Number of Buses: " + str(BUSNUM)))
buttonPlusBus = button(1150, 750, 40, 40, "+")
buttonMinusBus= button(1200, 750, 40, 40, "-")


buttonPause = button(1350, 550, 40, 40, "||")

buttonResetGraph = button(1125, 425, 80, 40, "Reset")
buttonSwitchGraph = button(1275, 425, 80, 40, "Switch")

buttons = pygame.sprite.Group()
buttons.add(buttonPlusSpeed, buttonMinusSpeed, buttonSpeed)
buttons.add(buttonPassenger, buttonPlusPassenger, buttonMinusPassenger)
buttons.add(buttonBus, buttonPlusBus, buttonMinusBus)
buttons.add(buttonPause)
buttons.add(buttonResetGraph)
buttons.add(buttonSwitchGraph)

clockVar = 120
totalTimes = []
travelTimes = []
waitTimes = []
normTotalTimes = []
normWaitTimes = []
normTravelTimes = []
capacities = []


fig = pylab.figure(figsize=[4.5, 4], dpi=100)
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

baverage = font.render("No Average Data", True, (0, 0, 0), (255, 255, 255))
baveragerect = baverage.get_rect()
baveragecent = (325, 850)

while running:
    ax.cla()
    if graphVar == 0:
        waitTravelTimes = pd.DataFrame(list(zip(waitTimes, travelTimes)), columns=["Waiting Time", "Travel Time"])
        sns.histplot(waitTravelTimes, ax=ax)
        ax.set_title("Wait and Travel Times")
        ax.set_xlabel("Clock Ticks")
        ax.set_ylabel("Frequency")
        ax.legend(["Travel time", "Wait time"], loc="upper right")
    elif graphVar == 1:
        if times != []:
            sns.histplot(totalTimes, ax=ax)
        ax.set_title("Total Journey Time")
        ax.set_xlabel("Clock Ticks")
        ax.set_ylabel("Frequency")
    if graphVar == 2:
        normWaitTravelTimes = pd.DataFrame(list(zip(normWaitTimes, normTravelTimes)),
                                           columns=["Waiting Time", "Travel Time"])
        sns.histplot(normWaitTravelTimes, ax=ax)
        ax.set_title("Normalised Wait and Travel Times")
        ax.set_xlabel("Clock Ticks / Pixel")
        ax.set_ylabel("Frequency")
        ax.legend(["Travel time", "Wait time"], loc="upper right")
    elif graphVar == 3:
        if times != []:
            sns.histplot(normTotalTimes, ax=ax)
        ax.set_title("Normalised Total Journey Time")
        ax.set_xlabel("Clock Ticks / Pixel")
        ax.set_ylabel("Frequency")
    elif graphVar == 4:
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
    screen.blit(surf, (1050, 0))
    if not paused:
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
                    clockVar = clockPaused
                else:
                    clockPaused = clockVar
                    clockVar = 1
                pasued = not paused
            if buttonPlusPassenger.rect.collidepoint(event.pos):
                if PASSCHANCE < 100:
                    PASSCHANCE = PASSCHANCE * 2
                    PASSCHANCE = np.round(PASSCHANCE, 5)
                    buttonPassenger.text = "Passenger Spawn Rate: " + str(PASSCHANCE)
            if buttonMinusPassenger.rect.collidepoint(event.pos):
                if PASSCHANCE > 0:
                    PASSCHANCE = PASSCHANCE / 2
                    PASSCHANCE = np.round(PASSCHANCE, 5)
                    buttonPassenger.text = "Passenger Spawn Rate: " + str(PASSCHANCE)
            if buttonSwitchGraph.rect.collidepoint(event.pos):
                if graphVar == 4:
                    graphVar = 0
                else:
                    graphVar += 1
            if buttonResetGraph.rect.collidepoint(event.pos):
                totalTimes = []
                travelTimes = []
                waitTimes = []
                normTotalTimes = []
                normTravelTimes = []
                normWaitTimes = []
    mapPicture = pygame.image.load(MAPNAME).convert()
    screen.fill((255, 255, 255))
    screen.blit(mapPicture, (0, 0))
    for entity in buttons:
        entity.update()
        screen.blit(entity.surf, entity.rect)
    baveragetext = str(
        "Average Waiting Time: " + str(np.round(np.mean(waitTimes), 2)) + ", Average Travel time: " + str(
            np.round(np.mean(travelTimes), 2)) + ", Average Travel time: " + str(np.round(np.mean(totalTimes), 2)))
    baverage = font.render(baveragetext, True, (0, 0, 0), (255, 255, 255))
    baveragerect = baverage.get_rect()
    baveragerect.center = (620, 800)
    screen.blit(baverage, baveragerect)
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
        if entity.newLog:
            pt = entity.getLog()
            pr = pt.get_rect()
            pr.center = (620, 700)
        if control.newLog:
            ct = control.getLog()
            cr = ct.get_rect()
            cr.center = (620, 735)
        screen.blit(entity.surf, entity.rect)
    screen.blit(pt, pr)
    screen.blit(ct, cr)
    for entity in busStops:
        entity.update()
        screen.blit(entity.surf, entity.rect)
    if SHOW_CONNECTIONS:
        for stop in busStops:
            for next in busStops:
                if adjMatrix[stop.id][next.id] == 1:
                    pygame.draw.line(screen, (255, 130, 255), (next.loc[0], next.loc[1]), (stop.loc[0], stop.loc[1]), 2)
    clock.tick(clockVar)
