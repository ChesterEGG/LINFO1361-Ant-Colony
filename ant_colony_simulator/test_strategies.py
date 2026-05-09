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
        self.path = {}
        self.reverse = {}
        self.position = {}
        self.visited_cells = {}
        self.walls = {}
        self.target_food = {}
        self.return_path = {}

    def init_ant(self, ant_id):
        """Init de la mémoire pour un ant qui n'a pas encore de mémoire"""
        if ant_id not in self.path:
            self.is_carrying_food[ant_id] = False
            self.path[ant_id] = []
            self.reverse[ant_id] = 0
            self.position[ant_id] = (0,0)
            self.visited_cells[ant_id] = {(0, 0)}
            self.walls[ant_id] = set()
            self.target_food[ant_id] = None
            self.return_path[ant_id] = []

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

        # Effectue un demi-tour
        if self.reverse[ant_id] > 0:
            self.reverse[ant_id] -= 1
            return AntAction.TURN_LEFT


        # Si on a la nourriture et que on est sur la colonie
        if self.is_carrying_food[ant_id]:
            cells = perception.visible_cells
            if (0, 0) in cells and cells[(0, 0)] == TerrainType.COLONY:
                self.is_carrying_food[ant_id] = False
                self.path[ant_id].clear()
                return AntAction.DROP_FOOD

        # Si on cherche la nourriture et que on est sur la nourriture
        if not self.is_carrying_food[ant_id]:
            cells = perception.visible_cells
            if (0, 0) in cells and cells[(0, 0)] == TerrainType.FOOD:
                self.is_carrying_food[ant_id] = True
                self.reverse[ant_id] = 4
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
                        break

            # Si on trouve une cible, on fonce dessus
            if self.target_food[ant_id] is not None:
                destination_x, destination_y = self.target_food[ant_id]

                action = self.get_direction((x, y), (destination_x, destination_y), perception.direction)
                self.path[ant_id].append(action)
                if action == AntAction.MOVE_FORWARD:
                    next_x, next_y = Direction.get_delta(perception.direction)
                    self.position[ant_id] = (x + next_x, y+next_y)
                    self.visited_cells[ant_id].add(self.position[ant_id])

                return action

            # Visiter avec priorité les cases pas encore visitées
            next_x, next_y = Direction.get_delta(perception.direction)
            front_x = x + next_x
            front_y = y + next_y
            actions = [AntAction.TURN_LEFT, AntAction.TURN_RIGHT]
            can_move_forward = True

            # Vérifier si on peut avancer
            if (next_x, next_y) not in perception.visible_cells:
                can_move_forward = False
            elif perception.visible_cells[(next_x, next_y)] == TerrainType.WALL:
                can_move_forward = False

            if can_move_forward:
                if (front_x, front_y) not in self.visited_cells[ant_id]:
                    # Pas encore visité, on avance mais on garde une chance de tourner pour éviter les boucles infinis
                    actions = actions = [AntAction.MOVE_FORWARD, AntAction.MOVE_FORWARD, AntAction.MOVE_FORWARD, AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT]
                else:
                    # Déja visité, on garde toutes les actions pour éviter d'être bloqué
                    actions = [AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT]

        random_action = random.choice(actions)
        self.path[ant_id].append(random_action)
        if random_action == AntAction.MOVE_FORWARD:
            self.position[ant_id] = (front_x, front_y)
            self.visited_cells[ant_id].add(self.position[ant_id])

        return random_action


