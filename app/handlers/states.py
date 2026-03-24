from aiogram.fsm.state import State, StatesGroup


class MlbbProfileStates(StatesGroup):
    game_player_id = State()
    profile_image = State()
    main_lane = State()
    extra_lanes = State()
    description = State()
