
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
    def __init__(self, id,  size, speed, gran, route):
        super(Bus, self).__init__()
        self.id = id
        self.surf = pygame.Surface((size, size))
        self.color = list(np.random.choice(range(256), size=3))
        self.surf.fill(self.color)
        self.rect = self.surf.get_rect(center=(route[0].loc[0], route[0].loc[1]))
        self.endStop = route[0]
        self.nextStop = route[0]
        self.prevStop = route[0]
        self.speed = speed
        self.granularity = gran
        self.path = []
        self.assignedPass = []
        self.newLog = False
        self.log = None
        self.route = route
        self.stopNum = 0
        self.ret = False

    def getPath(self):
        self.path = [self.endStop.id]
        while pred[self.path[-1]][self.prevStop.id] != self.path[-1]:
            self.path.append(pred[self.prevStop.id][self.path[-1]])
        self.path.append(self.prevStop.id)

    def getLog(self):
        self.newLog = False
        return self.log

    def getEndStop(self):
        if not self.ret:
            if self.stopNum < len(self.route)-1:
                self.stopNum += 1
                self.endStop = self.route[self.stopNum]
            else:
                self.ret = True
                self.stopNum -= 1
                self.endStop = self.route[self.stopNum]
        else:
            if self.stopNum > 0:
                self.stopNum -= 1
                self.endStop = self.route[self.stopNum]
            else:
                self.ret = False
                self.stopNum += 1
                self.endStop = self.route[self.stopNum]
        self.getPath()

    def getNextStop(self):
        self.prevStop = self.nextStop
        if self.prevStop == self.endStop:
            self.getEndStop()
            controlText = "Bus " + str(self.id) + " is now heading to " + str(self.endStop.loc)
            self.log = font.render(controlText, True, (0, 0, 0), (255, 255, 255))
            self.newLog = True
            self.endStop.surf = pygame.transform.scale(self.nextStop.surf,(5,5))
            self.endStop.surf.fill(self.color)
            for stop in busStops:
                if stop.id == self.path[-1]:
                    self.nextStop = stop
        else:
            self.path = self.path[:-1]
            for stop in busStops:
                if stop.id == self.path[-1]:
                    self.nextStop = stop


    def update(self):
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
        self.nextStop = tempStop
        self.onStop = tempStop
        self.speed = 1
        self.path = []
        self.buses = []
        self.onStops = []
        self.endStop = tempStop
        self.prevStop = tempStop


    def getPath(self):
        self.path = [self.endStop.id]
        while pred[self.path[-1]][self.prevStop.id] != self.path[-1]:
            self.path.append(pred[self.prevStop.id][self.path[-1]])
        self.path.append(self.prevStop.id)



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

    def getOnStop(self):
        distOn = 10000
        for bus in buses:
            for stop in bus.route:
                if dijkstra[self.start.id][stop.id] < distOn:
                    distOn = dijkstra[self.start.id][stop.id]
                    self.onStop = stop
        return self.onStop

    def getOffStop(self):
        distOff = 10000
        for bus in buses:
            for stop in bus.route:
                if dijkstra[self.end.id][stop.id] < distOff:
                    distOff = dijkstra[self.end.id][stop.id]
                    self.offStop = stop
        return self.offStop

    def getEndStop(self):
        if self.prevStop == self.offStop:
            self.endStop = self.end
        else:
            self.endStop = self.onStops[0]
        self.getPath()


    def getNextStop(self):
        self.prevStop = self.nextStop
        if self.nextStop != self.onStops[0]:
            if self.prevStop == self.endStop:
                self.onStops.pop(0)
                self.getEndStop()
            else:
                self.path = self.path[:-1]
                for stop in busStops:
                    if stop.id == self.path[-1]:
                        self.nextStop = stop

    def getInterchange(self):
        for stopLoc in self.buses[-1].route:
            if stopLoc.loc == self.offStop.loc:
                return self.offStop
        lastBus = []
        for bus in buses:
            for stopLoc in bus.route:
                if stopLoc.loc == self.offStop.loc:
                    lastBus.append(bus)
        connectBus = []
        for bus1 in lastBus:
            for bus2 in buses:
                for stopLoc1 in bus1.route:
                    for stopLoc2 in bus2.route:
                        if bus2.id not in lastBus:
                            if stopLoc1.id == stopLoc2.id:
                                connectBus.append(bus2)
        for bus in connectBus:
            for stopLoc in bus.route:
                if stopLoc.loc == self.onStop.loc:
                    for bus2 in lastBus:
                        for stopLoc1 in bus.route:
                            for stopLoc2 in bus2.route:
                                if stopLoc1.id == stopLoc2.id:
                                    return stopLoc1



    def getBuses(self):
        self.onStops.append(self.onStop)
        while self.onStops[-1].id != self.offStop.id:
            for bus in buses:
                for stopLoc in bus.route:
                    if stopLoc.loc == self.onStops[-1].loc:
                        self.buses.append(bus)
                        self.onStops.append(self.getInterchange())


    def resetPassenger(self):
        self.travelTime = 0
        self.waitTime = 0
        self.rect.inflate(7, 7)
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
        self.nextStop = start
        self.endStop = start
        self.getOnStop()
        self.getOffStop()
        self.getBuses()

    def update(self):
        spawn = False
        if self.start.id == -1:
            if random.random() < PASSCHANCE:
                spawn = True
        elif dijkstra[self.start.id][self.end.id] > 10000:
            self.resetPassenger()
        if spawn:
            self.resetPassenger()
            if self.buses != []:
                self.bus = self.buses[0]
            self.rect.x = self.start.loc[0]
            self.rect.y = self.start.loc[1]
        if self.bus is not None:
            if not self.onBus:
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
                if abs(self.rect.x - self.bus.rect.x) <= 5 and abs(self.rect.y - self.bus.rect.y) <= 5:
                    if abs(self.onStop.loc[0] - self.bus.rect.x) <= 5 and abs(self.onStop.loc[1] - self.bus.rect.y) <= 5:
                        self.onBus = True
                self.waitTime += 1
                if abs(self.onStop.loc[0] - self.rect.x) <= 5 and abs(self.onStop.loc[1] - self.rect.y) <= 5:
                    self.despawn()
                    self.newLog = True
                    totalTimes.append(self.travelTime + self.waitTime)
                    travelTimes.append(self.travelTime)
                    waitTimes.append(self.waitTime)
            else:
                self.travelTime += 1
                self.rect.top = 9999
                self.rect.left = 9999
                if abs(self.onStops[0].loc[0] - self.bus.rect.centerx) <= 5 and abs(self.onStops[0].loc[1] - self.bus.rect.centery) <= 5:
                    self.onBus = False
                    self.rect.x = self.onStops[0].loc[0]
                    self.rect.y = self.onStops[0].loc[1]
                    if self.onStops[0].id != self.offStop.id:
                        self.onStops.pop(0)
                        self.buses.pop(0)
                        self.bus = self.buses[0]
        else:
            self.rect.top = self.start.rect.top
            self.rect.left = self.start.rect.left

class controlCentre(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.newLog = False
        self.log = None
    def getLog(self):
        self.newLog = False
        return self.log

    def update(self, passenger):
        pass

#Example routes for absMap map
routeLoc = [
    [(65, 190), (225, 257), (323, 220), (432, 175), (580, 110), (635, 200), (687, 309), (775, 490)],
    [(140, 85), (215, 175), (225, 257), (250, 380), (245, 525), (390, 600)],
    [(140, 380), (245, 525), (390, 335), (500, 280), (635, 200), (760, 150)],
    [(570, 655), (600, 525), (500, 390), (390, 335), (432, 175), (400, 90)],
    [(940, 260), (795, 365), (775, 490), (600, 525), (390, 335), (440, 485), (225, 175), (140, 270)]
]
