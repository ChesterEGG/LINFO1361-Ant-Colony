from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy
from common import Direction

import random


class CooperativeStrategy(AntStrategy):
    """
    # TODO: Insert your code here
    """

    def __init__(self):
        """Initialize the strategy with last action tracking"""

        self.is_carrying_food = {}
        self.pheromone_timer = {}

    def init_ant(self, ant_id):
        if ant_id not in self.is_carrying_food:
            self.is_carrying_food[ant_id] = False
            self.pheromone_timer[ant_id] = 0

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
                return AntAction.PICK_UP_FOOD

        self.pheromone_timer[ant_id] += 1
        # S'arrêter tous les 3 tours pour déposer une phéromone
        if self.pheromone_timer[ant_id] >= 3:
            self.pheromone_timer[ant_id] = 0
            if self.is_carrying_food[ant_id]:
                return AntAction.DEPOSIT_FOOD_PHEROMONE
            else:
                return AntAction.DEPOSIT_HOME_PHEROMONE

        return self._decide_movement(perception)

    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""
        ant_id = perception.ant_id
        target_x, target_y = None, None

        for (x, y),  terrain in perception.visible_cells.items():
            if x == 0 and y == 0:
                continue
            if not self.is_carrying_food[ant_id] and terrain == TerrainType.FOOD:
                target_x, target_y = x, y
                break
            elif self.is_carrying_food[ant_id] and terrain == TerrainType.COLONY:
                target_x, target_y = x, y
                break

        if target_x is None and target_y is None:
            if self.is_carrying_food[ant_id]:
                pheromone = perception.home_pheromone
            else:
                pheromone = perception.food_pheromone

            max_smell = 0
            if pheromone:
                for (x, y), smell in pheromone.items():
                    if x == 0 and y == 0:
                        continue
                    if perception.visible_cells.get((x, y)) != TerrainType.WALL:
                        if smell > max_smell:
                            max_smell = smell
                            target_x, target_y = x, y

        if target_x is not None and target_y is not None:
            best_direction = None
            max_dot = -float('inf')
            for direction in Direction:
                vx, vy = Direction.get_delta(direction)
                mag = (vx**2 + vy**2)**0.5
                dot = (vx * target_x + vy * target_y) / mag
                if dot > max_dot:
                    max_dot = dot
                    best_direction = direction

            if perception.direction == best_direction:
                front_x, front_y = Direction.get_delta(perception.direction)
                if perception.visible_cells.get((front_x, front_y)) == TerrainType.WALL:
                    return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])
                return AntAction.MOVE_FORWARD

            current_x, current_y = Direction.get_delta(perception.direction)
            best_x, best_y = Direction.get_delta(best_direction)
            cross = (current_x * best_y) - (current_y * best_x)

            if cross > 0:
                return AntAction.TURN_RIGHT
            else:
                return AntAction.TURN_LEFT

        # Exploration
        front_x, front_y = Direction.get_delta(perception.direction)
        if (front_x, front_y) in perception.visible_cells and perception.visible_cells.get((front_x, front_y)) != TerrainType.WALL:
            if random.random() < 0.1:
                return random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT])
            return AntAction.MOVE_FORWARD
        else:
            return random.choice([AntAction.TURN_RIGHT, AntAction.TURN_LEFT])