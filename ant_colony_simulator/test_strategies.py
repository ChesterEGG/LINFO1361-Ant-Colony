from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy
from common import Direction
from collections import deque

import random


class NonCooperativeStrategy(AntStrategy):
    """
    # TODO: Insert your code here
    """

    def __init__(self):
        """Initialize the strategy with last action tracking"""


        # Mémoire pour chaque fourmi {ant_id: value}
        self.is_carrying_food = {}
        self.position = {}
        self.visited_cells = {}
        self.walls = {}
        self.target_food = {}
        self.return_path = {}
        self.frontiers = {}
        self.target_frontier = {}
        self.food_location = {}

    def init_ant(self, ant_id):
        """Init de la mémoire pour un ant qui n'a pas encore de mémoire"""
        if ant_id not in self.position:
            self.is_carrying_food[ant_id] = False
            self.position[ant_id] = (0,0)
            self.visited_cells[ant_id] = {(0, 0)}
            self.walls[ant_id] = set()
            self.target_food[ant_id] = None
            self.return_path[ant_id] = []
            self.frontiers[ant_id] = set()
            self.target_frontier[ant_id] = None
            self.food_location[ant_id] = set()

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
            dot = (x * direction_x + y * direction_y)/ mag
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


        # Si on a la nourriture et que on est sur la colonie
        if self.is_carrying_food[ant_id]:
            cells = perception.visible_cells
            if (0, 0) in cells and cells[(0, 0)] == TerrainType.COLONY:
                self.is_carrying_food[ant_id] = False
                return AntAction.DROP_FOOD

        # Si on cherche la nourriture et que on est sur la nourriture
        if not self.is_carrying_food[ant_id]:
            cells = perception.visible_cells
            if (0, 0) in cells and cells[(0, 0)] == TerrainType.FOOD:
                self.is_carrying_food[ant_id] = True
                self.target_food[ant_id] = None

                current_position = self.position[ant_id]
                self.return_path[ant_id] = self.bfs(current_position, (0, 0), self.walls[ant_id])
                return AntAction.PICK_UP_FOOD

        # Si on ne peut pas ramasser ou déposer, on bouge
        return self._decide_movement(perception)



    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""

        ant_id = perception.ant_id
        x, y = self.position[ant_id]

        # Cartographier les endroits où nous sommes déjà passés
        for (dx, dy), terrain in perception.visible_cells.items():
            if terrain == TerrainType.WALL:
                self.walls[ant_id].add((x + dx, y + dy))

            elif terrain == TerrainType.FOOD:
                self.food_location[ant_id].add((x + dx, y + dy))
            elif terrain == TerrainType.EMPTY or terrain == TerrainType.COLONY:
                self.food_location[ant_id].discard((x + dx, y + dy))

        # Chercher le chemin de retour
        if self.is_carrying_food[ant_id]:
            if self.return_path[ant_id]:
                destination_x, destination_y = self.return_path[ant_id][0]
                if x == destination_x and y == destination_y:
                    self.return_path[ant_id].pop(0)
                    if not self.return_path[ant_id]:
                        # Arriver à la colony (0,0)
                        return AntAction.TURN_LEFT
                    destination_x, destination_y = self.return_path[ant_id][0]

                action = self.get_direction((x, y), (destination_x, destination_y), perception.direction)
                if action == AntAction.MOVE_FORWARD:
                    next_x, next_y = Direction.get_delta(perception.direction)
                    if (next_x, next_y) not in perception.visible_cells or perception.visible_cells[(next_x, next_y)] == TerrainType.WALL:
                        self.walls[ant_id].add((x + next_x, y + next_y))
                        self.return_path[ant_id] = self.bfs((x, y), (0, 0), self.walls[ant_id])
                        return random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT])

                    self.position[ant_id] = (x + next_x, y+next_y)

                return action
            # Si la fourmi n'arrive pas à retrouver le chemin, actions random (évite les crash)
            else:
                return random.choice([AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT])

        # Exploration, chercher la nourriture
        else:

            # Si la cible à déjà été mangé par une autre fourmi, on annule la cible
            if self.target_food[ant_id] is not None:
                destination_x, destination_y = self.target_food[ant_id]
                if x == destination_x and y == destination_y:
                    self.target_food[ant_id] = None

            # Si on a pas trouvé de cible, on scanne la vision
            if self.target_food[ant_id] is None:
                for (dx, dy), terrain in perception.visible_cells.items():
                    if terrain == TerrainType.FOOD:
                        self.target_food[ant_id] = (x + dx, y + dy)
                        self.target_frontier[ant_id] = None
                        break

            # Mise à jour des frontières
            for (dx, dy) , terrain in perception.visible_cells.items():
                if terrain == TerrainType.EMPTY or terrain == TerrainType.FOOD:
                    nx, ny = x + dx, y + dy
                    if (nx, ny) not in self.visited_cells[ant_id]:
                        self.frontiers[ant_id].add((nx, ny))

            self.frontiers[ant_id].discard((x, y))

            target = None
            # Si on trouve une cible, on fonce dessus
            if self.target_food[ant_id] is not None:
                target = self.target_food[ant_id]
            else:
                if self.target_frontier[ant_id] == (x, y) or self.target_frontier[ant_id] not in self.frontiers[ant_id]:
                    self.target_frontier[ant_id] = None

                if self.food_location[ant_id]:
                    self.target_food[ant_id] = next(iter(self.food_location[ant_id]))
                    self.target_frontier[ant_id] = None
                    target = self.target_food[ant_id]

                elif self.target_frontier[ant_id] is None and self.frontiers[ant_id]:
                    frontiers = list(self.frontiers[ant_id])
                    sample = random.sample(frontiers, min(20, len(frontiers)))
                    self.target_frontier[ant_id] = max(sample, key=lambda f: f[0]**2 + f[1]**2)
                    target = self.target_frontier[ant_id]

            if self.target_food[ant_id] is None:
                front_dx, front_dy = Direction.get_delta(perception.direction)
                front_x, front_y = x + front_dx, y + front_dy

                if (front_dx, front_dy) in perception.visible_cells and perception.visible_cells[(front_dx, front_dy)] != TerrainType.WALL:
                    if (front_x, front_y) not in self.visited_cells[ant_id]:
                        self.position[ant_id] = (front_x, front_y)
                        self.visited_cells[ant_id].add((front_x, front_y))
                        self.frontiers[ant_id].discard((front_x, front_y))
                        return AntAction.MOVE_FORWARD

            if target is not None:
                target_x, target_y = target
                action = self.get_direction((x, y), (target_x, target_y), perception.direction)
                if action == AntAction.MOVE_FORWARD:
                    front_x, front_y = Direction.get_delta(perception.direction)
                    if (front_x, front_y) not in perception.visible_cells or perception.visible_cells[(front_x, front_y)] == TerrainType.WALL:
                        if self.target_food[ant_id] is None:
                            self.target_frontier[ant_id] = None
                        action = random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT])

                if action == AntAction.MOVE_FORWARD:
                    next_x, next_y = Direction.get_delta(perception.direction)
                    self.position[ant_id] = (x + next_x, y+next_y)
                    self.visited_cells[ant_id].add(self.position[ant_id])
                    self.frontiers[ant_id].discard(self.position[ant_id])
                return action


            # Sécurité (map exploré à 100% et pas de nourriture trouvé)
            action = random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT, AntAction.MOVE_FORWARD])
            if action == AntAction.MOVE_FORWARD:
                front_x ,front_y = Direction.get_delta(perception.direction)
                if (front_x, front_y) not in perception.visible_cells or perception.visible_cells[(front_x, front_y)] == TerrainType.WALL:
                    action = AntAction.TURN_LEFT
                else:
                    self.position[ant_id] = (x + front_x, y + front_y)
            return action


