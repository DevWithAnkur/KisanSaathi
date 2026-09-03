import pytest
from src.core.security import contains_profanity
from src.integrations.translation import TranslationClient

def test_profanity_filter():
    assert contains_profanity("This is a stupid question") is True
    assert contains_profanity("What is the price of tomatoes?") is False
    assert contains_profanity("pagal kisan") is True
    # Test boundary
    assert contains_profanity("curse") is True
    assert contains_profanity("cursor") is False # Should not match substring if \b is used correctly

@pytest.mark.asyncio
async def test_translation_success():
    client = TranslationClient()
    result = await client.translate("hello", "hi")
    # Our mock appends [HI]
    assert "[HI]" in result
    assert "hello" in result

@pytest.mark.asyncio
async def test_translation_fallback():
    client = TranslationClient()
    # Trigger mock failure
    result = await client.translate("simulate_failure error", "mr")
    # Should fallback to original english string
    assert "simulate_failure error" in result
    assert "[MR]" not in result

@pytest.mark.asyncio
async def test_translation_glossary():
    client = TranslationClient()
    # "fertilizer" should be translated to "खत" in Marathi
    result = await client.translate("We need fertilizer", "mr")
    assert "खत" in result
    assert "fertilizer" not in result.lower()
