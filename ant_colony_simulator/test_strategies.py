from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy
from common import Direction

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

    def init_ant(self, ant_id):
        """Init de la mémoire pour un ant qui n'a pas encore de mémoire"""
        if ant_id not in self.path:
            self.is_carrying_food[ant_id] = False
            self.path[ant_id] = []
            self.reverse[ant_id] = 0

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
                return AntAction.PICK_UP_FOOD

        # Si on ne peut pas ramasser ou déposer, on bouge
        return self._decide_movement(perception)



    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""

        ant_id = perception.ant_id

        # Chercher le chemin de retour
        if self.is_carrying_food[ant_id]:
            if len(self.path[ant_id]) > 0:
                last_move = self.path[ant_id].pop()
                if last_move == AntAction.MOVE_FORWARD:
                    return AntAction.MOVE_FORWARD
                elif last_move == AntAction.TURN_LEFT:
                    return AntAction.TURN_RIGHT
                elif last_move == AntAction.TURN_RIGHT:
                    return AntAction.TURN_LEFT
            # Si la fourmi n'arrive pas à retrouver le chemin, actions random (évite les crash)
            else:
                return random.choice([AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT])

        # Exploration, chercher la nourriture
        else:
            actions = ([AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT])

            # Eviter les murs et le bord de la carte
            x, y = Direction.get_delta(perception.direction)
            if (x, y) not in perception.visible_cells or perception.visible_cells[(x, y)] == TerrainType.WALL:
                actions = [AntAction.TURN_LEFT, AntAction.TURN_RIGHT]

            random_action = random.choice(actions)
            self.path[ant_id].append(random_action)

            return random_action