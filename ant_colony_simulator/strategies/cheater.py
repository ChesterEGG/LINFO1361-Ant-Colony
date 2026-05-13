from environment import TerrainType, AntPerception, Environment
from ant import AntAction, AntStrategy
from common import Direction
from collections import deque

import random


class CheaterStrategy(AntStrategy):
    def __init__(self):
        """Initialisation de la mémoire du tricheur"""
        self.env = None
        self.paths = {}
        self.pheromone_timer = {}

    def set_environment(self, environment: Environment):
        """L'accès interdit : On stocke l'environnement global !"""
        self.env = environment

    def global_bfs(self, start_pos, target_positions):
        """
        Un BFS Omniscient : Il scanne la vraie grille complète du jeu
        pour trouver le chemin le plus court absolu.
        """
        queue = deque([[start_pos]])
        visited = {start_pos}
        deltas = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

        while queue:
            path = queue.popleft()
            curr = path[-1]

            if curr in target_positions:
                return path[1:]  # On retourne le chemin sans la case de départ

            for dx, dy in deltas:
                nx, ny = curr[0] + dx, curr[1] + dy
                # On vérifie les limites de la VRAIE carte
                if 0 <= nx < self.env.width and 0 <= ny < self.env.height:
                    # On évite les VRAIS murs directement
                    if self.env.grid[ny][nx] != TerrainType.WALL.value:
                        if (nx, ny) not in visited:
                            visited.add((nx, ny))
                            queue.append(path + [(nx, ny)])
        return []

    def get_direction(self, current_pos, dest_pos, current_direction):
        """Pilote automatique mathématique classique"""
        cx, cy = current_pos
        dx, dy = dest_pos
        direction_x, direction_y = dx - cx, dy - cy

        if direction_x == 0 and direction_y == 0:
            return AntAction.MOVE_FORWARD

        best_direction = None
        max_dot = -float('inf')
        for direction in Direction:
            x, y = Direction.get_delta(direction)
            mag = (x ** 2 + y ** 2) ** 0.5
            if mag > 0:
                dot = (x * direction_x + y * direction_y) / mag
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
        dot_rotation = (current_x * best_x) + (current_y * best_y)

        if cross > 0 or (cross == 0 and dot_rotation < 0):
            return AntAction.TURN_RIGHT
        else:
            return AntAction.TURN_LEFT

    def decide_action(self, perception: AntPerception) -> AntAction:
        ant_id = perception.ant_id

        # Initialisation du timer pour cette fourmi
        if ant_id not in self.pheromone_timer:
            self.pheromone_timer[ant_id] = 0
            self.paths[ant_id] = []

        # TRICHE 1 : On trouve notre vraie fourmi dans la simulation
        my_ant = next((a for a in self.env.ants if a.id == ant_id), None)
        if not my_ant:
            return AntAction.NO_ACTION  # Sécurité

        current_pos = (int(my_ant.x), int(my_ant.y))

        # --- 1. Actions automatiques (Ramasser / Déposer) ---
        if my_ant.has_food and current_pos in self.env.colony_positions:
            return AntAction.DROP_FOOD

        if not my_ant.has_food and current_pos in self.env.food_positions:
            return AntAction.PICK_UP_FOOD

        # --- 2. Phéromones (Pour aider les fourmis "honnêtes" si on les mixe) ---
        self.pheromone_timer[ant_id] += 1
        if self.pheromone_timer[ant_id] >= 3:
            self.pheromone_timer[ant_id] = 0
            if my_ant.has_food:
                return AntAction.DEPOSIT_FOOD_PHEROMONE
            else:
                return AntAction.DEPOSIT_HOME_PHEROMONE

        # --- 3. La Navigation Omnisciente ---
        # Si on n'a pas de chemin, ou que la nourriture visée a disparu, on recalcule !
        if not self.paths[ant_id] or (not my_ant.has_food and self.paths[ant_id][-1] not in self.env.food_positions):
            if my_ant.has_food:
                # Retour absolu vers la colonie
                self.paths[ant_id] = self.global_bfs(current_pos, set(self.env.colony_positions))
            else:
                # Cible absolue vers n'importe quelle nourriture de la carte
                self.paths[ant_id] = self.global_bfs(current_pos, self.env.food_positions)

        # Suivre le chemin parfait
        if self.paths[ant_id]:
            next_pos = self.paths[ant_id][0]
            action = self.get_direction(current_pos, next_pos, my_ant.direction)

            # Si on avance avec succès, on retire l'étape du chemin
            if action == AntAction.MOVE_FORWARD:
                self.paths[ant_id].pop(0)
            return action

        # Sécurité ultime (théoriquement inatteignable pour un tricheur)
        return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])