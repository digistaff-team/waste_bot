# -*- coding: utf-8 -*-
"""
Unit-тесты для services/fkko_service.py
"""
import pytest
from services.fkko_service import (
    search_fkko,
    get_fkko_by_code,
    get_popular_fkko,
    FKKO_CATALOG,
)


class TestSearchFkko:
    """Тесты поиска по справочнику ФКО"""
    
    def test_search_by_name_exact(self):
        results = search_fkko("макулатура бумажная")
        assert len(results) > 0
        assert results[0]["code"] == "1 81 010 01 20 5"
    
    def test_search_by_name_partial(self):
        results = search_fkko("полиэтилен")
        assert len(results) > 0
        # Проверяем, что хотя бы один результат содержит "полиэтилен"
        assert any("полиэтилен" in r["name"].lower() for r in results)
    
    def test_search_by_code(self):
        results = search_fkko("1 81 010 01 20 5")
        assert len(results) > 0
        assert results[0]["code"] == "1 81 010 01 20 5"
    
    def test_search_by_code_partial(self):
        results = search_fkko("1 81")
        assert len(results) > 0
    
    def test_search_not_found(self):
        results = search_fkko("абсолютно_неизвестный_отход")
        assert len(results) == 0
    
    def test_search_case_insensitive(self):
        results1 = search_fkko("МАКУЛАТУРА")
        results2 = search_fkko("макулатура")
        assert len(results1) == len(results2)
    
    def test_search_limit(self):
        results = search_fkko("о", limit=5)
        assert len(results) <= 5


class TestGetFkkoByCode:
    """Тесты получения записи по коду"""
    
    def test_existing_code(self):
        result = get_fkko_by_code("1 81 010 01 20 5")
        assert result is not None
        assert result["name"] == "Макулатура бумажная"
    
    def test_existing_code_no_spaces(self):
        result = get_fkko_by_code("18101001205")
        assert result is None  # Код с пробелами
    
    def test_non_existing_code(self):
        result = get_fkko_by_code("9 99 999 99 99 9")
        assert result is None
    
    def test_empty_code(self):
        result = get_fkko_by_code("")
        assert result is None


class TestGetPopularFkko:
    """Тесты получения популярных категорий"""
    
    def test_returns_list(self):
        result = get_popular_fkko()
        assert isinstance(result, list)
    
    def test_default_limit(self):
        result = get_popular_fkko()
        assert len(result) <= 8
    
    def test_custom_limit(self):
        result = get_popular_fkko(limit=3)
        assert len(result) == 3
    
    def test_all_valid_codes(self):
        result = get_popular_fkko()
        for item in result:
            # Проверяем, что все записи имеют нужные поля
            assert "code" in item
            assert "name" in item
            # Проверяем, что код существует в каталоге
            assert get_fkko_by_code(item["code"]) is not None


class TestFkkoCatalog:
    """Тесты справочника ФКО"""
    
    def test_catalog_not_empty(self):
        assert len(FKKO_CATALOG) > 0
    
    def test_all_items_have_code_and_name(self):
        for item in FKKO_CATALOG:
            assert "code" in item
            assert "name" in item
            assert isinstance(item["code"], str)
            assert isinstance(item["name"], str)
    
    def test_all_codes_unique(self):
        codes = [item["code"] for item in FKKO_CATALOG]
        assert len(codes) == len(set(codes))
    
    def test_contains_waste_types(self):
        """Проверяем наличие основных типов отходов"""
        names = [item["name"].lower() for item in FKKO_CATALOG]
        
        # Проверяем наличие ключевых слов в каталоге
        # "макулатура" есть в каталоге
        assert any("макулатура" in name for name in names), \
            "Тип отхода 'макулатура' не найден в каталоге"
        # "полиэтилен" есть в каталоге (пластик)
        assert any("полиэтилен" in name for name in names), \
            "Тип отхода 'полиэтилен' не найден в каталоге"
        # "металл" есть в каталоге
        assert any("металл" in name for name in names), \
            "Тип отхода 'металл' не найден в каталоге"
        # "стекло" есть в каталоге
        assert any("стекл" in name for name in names), \
            "Тип отхода 'стекло' не найден в каталоге"
        # "резина" есть в каталоге
        assert any("резин" in name for name in names), \
            "Тип отхода 'резина' не найден в каталоге"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])