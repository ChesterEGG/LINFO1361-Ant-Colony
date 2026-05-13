from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy
from common import Direction
from collections import deque

import random


class SmartStrategy(AntStrategy):

    def __init__(self):
        """Initialize the strategy with last action tracking"""
        self.is_carrying_food = {}
        self.position = {}
        self.walls = {}
        self.visited_cells = {}
        self.food_location = {}
        self.return_path = {}
        self.pheromone_timer = {}
        self.frontiers = {}
        self.target_frontier = {}
        self.target_food = {}
        self.last_position = {}

    def init_ant(self, ant_id):
        if ant_id not in self.position:
            self.is_carrying_food[ant_id] = False
            self.position[ant_id] = (0, 0)
            self.walls[ant_id] = set()
            self.visited_cells[ant_id] = {(0, 0)}
            self.food_location[ant_id] = set()
            self.return_path[ant_id] = []
            self.pheromone_timer[ant_id] = 0
            self.frontiers[ant_id] = set()
            self.target_frontier[ant_id] = None
            self.target_food[ant_id] = None
            self.last_position[ant_id] = None

    def bfs(self, start, destination, walls):
        """Calcule du chemin le plus court en évitant les murs"""
        queue = deque([[start]])
        visited = {start}
        deltas = [(0,1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

        while queue:
            path = queue.popleft()
            current = path[-1]
            if current == destination:
                return path[1:]

            for x, y in deltas:
                neighbor = (current[0] + x, current[1] + y)
                if neighbor not in visited and neighbor not in walls:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return []

    def get_direction(self, current_pos, destnation_pos, current_direction):
        cx, cy = current_pos
        dx, dy = destnation_pos
        direction_x, direction_y = dx - cx, dy - cy

        if direction_x == 0 and direction_y == 0:
            return AntAction.MOVE_FORWARD

        # Trouver la meilleur direction
        best_direction = None
        max_dot = -float('inf')
        for direction in Direction:
            x, y = Direction.get_delta(direction)
            # Produit scalaire
            mag = (x**2 + y**2)**0.5
            if mag > 0:
                dot = (x * direction_x + y * direction_y)/ mag
            else:
                dot = 0
            if dot > max_dot:
                max_dot = dot
                best_direction = direction

        if current_direction == best_direction:
            return AntAction.MOVE_FORWARD

        current_x, current_y = Direction.get_delta(current_direction)
        best_x, best_y = Direction.get_delta(best_direction)
        cross = (current_x * best_y) - (current_y * best_x)

        if cross > 0:
            return AntAction.TURN_RIGHT
        else:
            return AntAction.TURN_LEFT

    def decide_action(self, perception: AntPerception) -> AntAction:
        """Decide an action based on current perception"""
        ant_id = perception.ant_id
        self.init_ant(ant_id)

        # Règles de base
        if self.is_carrying_food[ant_id]:
            if (0, 0) in perception.visible_cells and perception.visible_cells[(0, 0)] == TerrainType.COLONY:
                self.is_carrying_food[ant_id] = False
                return AntAction.DROP_FOOD

        elif not self.is_carrying_food[ant_id]:
            if (0, 0) in perception.visible_cells and perception.visible_cells[(0, 0)] == TerrainType.FOOD:
                self.is_carrying_food[ant_id] = True
                self.return_path[ant_id] = self.bfs(self.position[ant_id], (0, 0), self.walls[ant_id])
                return AntAction.PICK_UP_FOOD

        # Phéromones
        self.pheromone_timer[ant_id] += 1
        if self.pheromone_timer[ant_id] >= 3:
            self.pheromone_timer[ant_id] = 0
            if self.is_carrying_food[ant_id]:
                return AntAction.DEPOSIT_FOOD_PHEROMONE

        return self._decide_movement(perception)

    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""
        ant_id = perception.ant_id
        x , y = self.position[ant_id]

        # Cartographier les endroits où nous sommes déjà passés
        for (dx, dy), terrain in perception.visible_cells.items():
            if terrain == TerrainType.WALL:
                self.walls[ant_id].add((x + dx, y + dy))

            elif terrain == TerrainType.FOOD:
                self.food_location[ant_id].add((x + dx, y + dy))
            elif terrain == TerrainType.EMPTY or terrain == TerrainType.COLONY:
                self.food_location[ant_id].discard((x + dx, y + dy))
                if self.target_food.get(ant_id) == (x + dx, y +dy):
                    self.target_food[ant_id] = None
                if ((x + dx, y+ dy)) not in self.visited_cells[ant_id]:
                    self.frontiers[ant_id].add((x + dx, y + dy))

        self.frontiers[ant_id].discard((x, y))

        # Retour
        if self.is_carrying_food[ant_id]:
            if not self.return_path[ant_id]:
                self.return_path[ant_id] = self.bfs((x, y), (0, 0), self.walls[ant_id])

            if self.return_path[ant_id]:
                destination_x, destination_y = self.return_path[ant_id][0]
                if x == destination_x and y == destination_y:
                    self.return_path[ant_id].pop(0)
                    if not self.return_path[ant_id]:
                        return AntAction.TURN_LEFT
                    destination_x, destination_y = self.return_path[ant_id][0]

                action = self.get_direction((x, y ), (destination_x, destination_y), perception.direction)
                if action == AntAction.MOVE_FORWARD:
                    fx, fy = Direction.get_delta((perception.direction))
                    if (fx, fy) not in perception.visible_cells or perception.visible_cells.get((fx, fy))== TerrainType.WALL :
                        self.walls[ant_id].add((x + fx, y + fy))
                        self.return_path[ant_id] = self.bfs((x, y), (0, 0), self.walls[ant_id])
                        return random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT])
                    self.last_position[ant_id] = self.position[ant_id]
                    self.position[ant_id] = (x + fx, y+ fy)
                return action
            # Si la fourmi n'arrive pas à retrouver le chemin, actions random (évite les crash)
            else:
                action = random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT, AntAction.MOVE_FORWARD])
                if action == AntAction.MOVE_FORWARD:
                    fx, fy = Direction.get_delta((perception.direction))
                    if (fx, fy) not in perception.visible_cells or perception.visible_cells.get((fx, fy)) == TerrainType.WALL :
                        return random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT])

                    self.last_position[ant_id] = self.position[ant_id]
                    self.position[ant_id] = (x + fx, y+ fy)
                return action


        # Recherche
        target_x, target_y = None, None

        # 1) Vision directe
        if self.target_food[ant_id] is None:
            for (dx, dy), terrain in perception.visible_cells.items():
                if terrain == TerrainType.FOOD:
                    self.target_food[ant_id] = (x + dx, y + dy)
                    self.target_frontier[ant_id] = None
                    break

        # 2) Explorer la mémoire
        if self.target_food[ant_id] is None:
            if self.food_location[ant_id]:
                self.target_food[ant_id] = next(iter(self.food_location[ant_id]))
                self.target_frontier[ant_id] = None
        if self.target_food[ant_id] is not None:
            target_x, target_y = self.target_food[ant_id]

        # 3) Suivre la piste des autres (phéromones)
        if target_x is None and target_y is None:
            if perception.food_pheromone:
                max_smell = 0
                for (px, py), smell in perception.food_pheromone.items():
                    if px == 0 and py == 0:
                        continue
                    if perception.visible_cells.get((px, py)) != TerrainType.WALL:
                        if self.last_position.get(ant_id) != (x+ px, y + py):
                            if smell > max_smell:
                                max_smell = smell
                                target_x, target_y = px + x, y + py

        # 4) Explorer les zones non-explorées
        if target_x is None and target_y is None:
            if self.target_frontier[ant_id] == (x, y) or self.target_frontier[ant_id] not in self.frontiers[ant_id]:
                self.target_frontier[ant_id] = None

            if self.target_frontier[ant_id] is None and self.frontiers[ant_id]:
                sample = random.sample(list(self.frontiers[ant_id]), min(20, len(self.frontiers[ant_id])))
                # Choisir ICI les paramètre d'exploration
                if random.random() < 0.5:
                    self.target_frontier[ant_id] = max(sample, key=lambda f: f[0] ** 2 + f[1] ** 2)
                    #self.target_frontier[ant_id] = min(sample, key=lambda f: (f[0] - x)**2 + (f[1] - y)**2)
                else:
                    self.target_frontier[ant_id] = random.choice(sample)

            if self.target_frontier[ant_id]:
                target_x, target_y = self.target_frontier[ant_id]


        # Navigation
        if self.target_food[ant_id] is None:
            front_dx, front_dy = Direction.get_delta(perception.direction)
            front_x, front_y = x + front_dx, y + front_dy
            if (front_dx, front_dy) in perception.visible_cells and perception.visible_cells.get((front_dx, front_dy)) != TerrainType.WALL:
                if (front_x, front_y) not in self.visited_cells[ant_id]:
                    self.last_position[ant_id] = self.position[ant_id]
                    self.position[ant_id] = (front_x, front_y)
                    self.visited_cells[ant_id].add((front_x, front_y))
                    self.frontiers[ant_id].discard((front_x, front_y))
                    return AntAction.MOVE_FORWARD

        if target_x is not None and target_y is not None:
            action = self.get_direction((x, y), (target_x, target_y), perception.direction)
            if action == AntAction.MOVE_FORWARD:
                next_x, next_y = Direction.get_delta(perception.direction)
                if (next_x, next_y) not in perception.visible_cells or perception.visible_cells.get((next_x, next_y)) == TerrainType.WALL:
                    action = random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT])
        else:
            action = AntAction.MOVE_FORWARD
            next_x, next_y = Direction.get_delta(perception.direction)
            if (next_x, next_y) not in perception.visible_cells or perception.visible_cells.get((next_x, next_y)) == TerrainType.WALL:
                action = random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT])

        # Mise à jour de la position
        if action == AntAction.MOVE_FORWARD:
            next_x, next_y = Direction.get_delta(perception.direction)
            self.last_position[ant_id] = self.position[ant_id]
            self.position[ant_id] = (next_x + x, next_y + y)
            self.visited_cells[ant_id].add(self.position[ant_id])
            self.frontiers[ant_id].discard(self.position[ant_id])

        return action






