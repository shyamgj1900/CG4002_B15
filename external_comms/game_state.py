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

    def detected_game_state(self, new_action):
        """
        This function updates the players game state based on the action it has received from the client side. (For now
        this function only updates game state based on 1 player mode).
        """
        player1_valid = self.player1.action_is_valid(new_action)
        # player2_valid = self.player2.action_is_valid(new_action)
        self.player1.update(new_action, 'none', player1_valid, False)
        self.player2.update('none', new_action, False, player1_valid)

    def update_game_state(self, updated_state):
        player1_dict = updated_state['p1']
        player2_dict = updated_state['p2']
        self.player1.initialize_from_dict(player1_dict)
        self.player2.initialize_from_dict(player2_dict)
