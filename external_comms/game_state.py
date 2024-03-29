from external_comms.player_state import PlayerState


class GameState:
    """
    class for sending and receiving the game state json object
    """
    def __init__(self):
        self.player1 = PlayerState()
        self.player2 = PlayerState()

    def get_dict(self):
        data = {'p1': self.player1.get_dict(), 'p2': self.player2.get_dict()}
        return data

    def detected_game_state(self, p1_action, p2_action, p1_hit_valid=False, p2_hit_valid=False):
        """
        This function updates the players game state based on the action it has received from the client side.
        """
        player1_action_valid = self.player1.action_is_valid(p1_action)
        player2_action_valid = self.player2.action_is_valid(p2_action)
        if player2_action_valid and (p2_action == "shoot" or p2_action == "grenade"):
            self.player1.update(p1_action, p2_action, player1_action_valid, p2_hit_valid)
        else:
            self.player1.update(p1_action, p2_action, player1_action_valid, player2_action_valid)
        if player1_action_valid and (p1_action == "shoot" or p1_action == "grenade"):
            self.player2.update(p2_action, p1_action, player2_action_valid, p1_hit_valid)
        else:
            self.player2.update(p2_action, p1_action, player2_action_valid, player1_action_valid)

    def update_game_state(self, updated_state):
        player1_dict = updated_state['p1']
        player2_dict = updated_state['p2']
        self.player1.initialize_from_dict(player1_dict)
        self.player2.initialize_from_dict(player2_dict)
