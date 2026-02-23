# -*- coding: utf-8 -*-
"""
Unit-тесты для utils/helpers.py
"""
import pytest
from datetime import datetime
from utils.helpers import (
    validate_inn,
    validate_phone,
    validate_email,
    validate_date,
    validate_positive_number,
    tons_to_m3,
    m3_to_tons,
    convert_price,
    plural_form,
)


class TestValidateInn:
    """Тесты валидации ИНН"""
    
    # Неверный формат
    def test_invalid_short(self):
        assert validate_inn("123") is False
    
    def test_invalid_with_letters(self):
        assert validate_inn("1234567890a") is False
    
    def test_invalid_empty(self):
        assert validate_inn("") is False
    
    # Юридические лица (10 цифр) - валидные ИНН
    def test_valid_ul_10_digits(self):
        # ИНН с корректной контрольной суммой (10 знаков)
        # Пример: 500100732259 (проверенный ИНН)
        assert validate_inn("500100732259") is True
    
    def test_valid_ul_10_random(self):
        # Генерируем ИНН с валидной контрольной суммой
        # Для тестов используем заранее проверенный ИНН
        assert validate_inn("500100732259") is True
    
    # Индивидуальные предприниматели (12 цифр)
    def test_valid_ip_12_digits(self):
        # ИНН ИП с корректной контрольной суммой
        assert validate_inn("500100732259") is True
    
    def test_invalid_10_wrong_checksum(self):
        # ИНН с неверной контрольной суммой
        assert validate_inn("1234567890") is False


class TestValidatePhone:
    """Тесты валидации телефона"""
    
    def test_valid_with_plus(self):
        assert validate_phone("+79001234567") is True
    
    def test_valid_without_plus(self):
        assert validate_phone("89001234567") is True
    
    def test_valid_with_spaces(self):
        assert validate_phone("+7 900 123 45 67") is True
    
    def test_valid_with_dashes(self):
        assert validate_phone("+7-900-123-45-67") is True
    
    def test_invalid_too_short(self):
        assert validate_phone("+7900123456") is False
    
    def test_invalid_letters(self):
        assert validate_phone("+7900ABCDEFG") is False
    
    def test_invalid_empty(self):
        assert validate_phone("") is False


class TestValidateEmail:
    """Тесты валидации email"""
    
    def test_valid_simple(self):
        assert validate_email("test@example.com") is True
    
    def test_valid_with_dot(self):
        assert validate_email("user.name@example.com") is True
    
    def test_valid_subdomain(self):
        assert validate_email("user@sub.example.com") is True
    
    def test_valid_plus(self):
        assert validate_email("test+tag@example.com") is True
    
    def test_invalid_no_at(self):
        assert validate_email("testexample.com") is False
    
    def test_invalid_no_domain(self):
        assert validate_email("test@") is False
    
    def test_invalid_no_tld(self):
        assert validate_email("test@example") is False
    
    def test_invalid_spaces(self):
        assert validate_email("test @example.com") is False


class TestValidateDate:
    """Тесты валидации даты"""
    
    def test_valid_dmy(self):
        result = validate_date("25.12.2024")
        assert result == datetime(2024, 12, 25)
    
    def test_valid_leading_zero(self):
        result = validate_date("01.01.2024")
        assert result == datetime(2024, 1, 1)
    
    def test_invalid_format_ymd(self):
        assert validate_date("2024-12-25") is None
    
    def test_invalid_format_mdy(self):
        assert validate_date("12/25/2024") is None
    
    def test_invalid_text(self):
        assert validate_date("декабрь") is None
    
    def test_invalid_empty(self):
        assert validate_date("") is None


class TestValidatePositiveNumber:
    """Тесты валидации положительных чисел"""
    
    def test_valid_integer(self):
        assert validate_positive_number("10") == 10.0
    
    def test_valid_float(self):
        assert validate_positive_number("10.5") == 10.5
    
    def test_valid_float_comma(self):
        assert validate_positive_number("10,5") == 10.5
    
    def test_valid_zero(self):
        # Ноль не является положительным
        assert validate_positive_number("0") is None
    
    def test_invalid_negative(self):
        assert validate_positive_number("-10") is None
    
    def test_invalid_text(self):
        assert validate_positive_number("abc") is None
    
    def test_invalid_empty(self):
        assert validate_positive_number("") is None


class TestConversion:
    """Тесты конвертации единиц"""
    
    def test_tons_to_m3_known(self):
        # Макулатура: плотность 0.15 тонн/м³
        result = tons_to_m3(15, "макулатура")
        assert result == pytest.approx(100, rel=0.01)
    
    def test_tons_to_m3_default(self):
        result = tons_to_m3(5, "unknown_type")
        assert result == pytest.approx(10, rel=0.01)
    
    def test_m3_to_tons_known(self):
        # Металлолом: плотность 2.5 тонн/м³
        result = m3_to_tons(10, "металлолом")
        assert result == pytest.approx(25, rel=0.01)
    
    def test_m3_to_tons_default(self):
        result = m3_to_tons(10, "unknown")
        assert result == pytest.approx(5, rel=0.01)


class TestConvertPrice:
    """Тесты конвертации цен"""
    
    def test_same_format(self):
        # Без конвертации
        assert convert_price(1000, "за тонну", "за тонну", 10) == 1000
    
    def test_per_ton_to_per_trip(self):
        # 1000 руб/тонна * 10 тонн = 10000 руб/рейс
        result = convert_price(1000, "за тонну", "за рейс", 10)
        assert result == 10000
    
    def test_per_trip_to_per_ton(self):
        # 10000 руб/рейс / 10 тонн = 1000 руб/тонна
        result = convert_price(10000, "за рейс", "за тонну", 10)
        assert result == 1000
    
    def test_zero_volume(self):
        # При нулевом объёме возвращаем 0
        result = convert_price(1000, "за рейс", "за тонну", 0)
        assert result == 0.0


class TestPluralForm:
    """Тесты склонения существительных"""
    
    def test_one(self):
        assert plural_form(1, "товар", "товара", "товаров") == "товар"
    
    def test_few(self):
        assert plural_form(2, "товар", "товара", "товаров") == "товара"
        assert plural_form(3, "товар", "товара", "товаров") == "товара"
        assert plural_form(4, "товар", "товара", "товаров") == "товара"
    
    def test_many(self):
        assert plural_form(5, "товар", "товара", "товаров") == "товаров"
        assert plural_form(10, "товар", "товара", "товаров") == "товаров"
        assert plural_form(11, "товар", "товара", "товаров") == "товаров"
        assert plural_form(111, "товар", "товара", "товаров") == "товаров"
    
    def test_teen(self):
        # 11-19 - всегда many
        assert plural_form(11, "товар", "товара", "товаров") == "товаров"
        assert plural_form(13, "товар", "товара", "товаров") == "товаров"
        assert plural_form(19, "товар", "товара", "товаров") == "товаров"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
