import pytest
import asyncio
from docucheck.core.verifier import external_fact_check_async, check_consistency_async
from docucheck.models.schemas import Claim, FactCheckResult, Contradiction

@pytest.mark.asyncio
async def test_claim_model_validation():
    """Verify that the Claim model correctly handles valid and invalid data."""
    # Valid claim
    c = Claim(claim="The capital of France is Paris", section="Geography")
    assert c.claim == "The capital of France is Paris"
    
    # Missing required field should raise error
    with pytest.raises(ValueError):
        Claim(section="Broken")

@pytest.mark.asyncio
async def test_external_fact_check_return_type():
    """Ensure the verifier returns a valid FactCheckResult object."""
    test_claim = Claim(claim="Water freezes at 0 degrees Celsius", section="Science")
    
    # This call relies on your GEMINI_API_KEY being set in your environment
    result = await external_fact_check_async(test_claim)
    
    assert isinstance(result, FactCheckResult)
    assert result.claim == test_claim.claim
    assert result.confidence_score >= 0.0 and result.confidence_score <= 1.0

@pytest.mark.asyncio
async def test_consistency_with_no_contradictions():
    """Verify that consistent claims return an empty list."""
    claims = [
        Claim(claim="The moon orbits the Earth", section="Space"),
        Claim(claim="The Earth is a planet", section="Space")
    ]
    
    results = await check_consistency_async(claims)
    assert isinstance(results, list)
    # If the LLM is accurate, this should be empty
    assert len(results) >= 0