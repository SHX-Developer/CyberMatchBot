from aiogram.fsm.state import State, StatesGroup


class MlbbProfileStates(StatesGroup):
    game_player_id = State()
    profile_image = State()
    main_lane = State()
    extra_lanes = State()
    description = State()


class ProfileStates(StatesGroup):
    waiting_for_avatar = State()
    waiting_for_full_name = State()


class ProfilesSectionStates(StatesGroup):
    creating_profile = State()
    editing_profile_field = State()
    mlbb_waiting_photo = State()
    mlbb_waiting_game_id = State()
    mlbb_waiting_rank = State()
    mlbb_waiting_main_lane = State()
    mlbb_waiting_extra_lanes = State()
    mlbb_waiting_server = State()
    mlbb_waiting_about = State()


class SearchStates(StatesGroup):
    waiting_for_message_text = State()
