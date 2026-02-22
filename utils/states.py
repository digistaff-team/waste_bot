"""
FSM-состояния для всех диалогов бота.
"""
from aiogram.fsm.state import State, StatesGroup


# ─────────────────────────────────────────────────────────────────────────────
# Регистрация
# ─────────────────────────────────────────────────────────────────────────────
class RegistrationStates(StatesGroup):
    choosing_role = State()
    entering_org_name = State()
    entering_inn = State()
    entering_region = State()
    entering_phone = State()
    entering_email = State()
    # Только для перевозчика
    entering_vehicle_types = State()
    entering_capacity = State()
    entering_carrier_regions = State()
    confirming = State()


# ─────────────────────────────────────────────────────────────────────────────
# Размещение лота (Продавец)
# ─────────────────────────────────────────────────────────────────────────────
class LotCreationStates(StatesGroup):
    choosing_fkko = State()
    entering_fkko_search = State()
    entering_volume = State()
    choosing_unit = State()
    entering_price = State()
    choosing_price_format = State()
    choosing_condition = State()
    entering_address_from = State()
    entering_address_to = State()
    entering_valid_until = State()
    uploading_photo = State()
    confirming = State()


# ─────────────────────────────────────────────────────────────────────────────
# Поиск лотов (Покупатель)
# ─────────────────────────────────────────────────────────────────────────────
class BuyerSearchStates(StatesGroup):
    choosing_filter = State()
    entering_region = State()
    entering_radius = State()
    entering_fkko_filter = State()
    entering_volume_min = State()
    entering_volume_max = State()
    entering_price_min = State()
    entering_price_max = State()
    viewing_results = State()
    viewing_lot_detail = State()
    confirming_purchase = State()


# ─────────────────────────────────────────────────────────────────────────────
# Перевозчик
# ─────────────────────────────────────────────────────────────────────────────
class CarrierStates(StatesGroup):
    viewing_requests = State()
    viewing_request_detail = State()
    confirming_accept = State()
    updating_status = State()
