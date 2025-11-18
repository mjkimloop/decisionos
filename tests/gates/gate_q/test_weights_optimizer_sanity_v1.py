"""
Gate Q — Weights optimizer sanity tests
"""
from jobs.weights_optimize import WeightsOptimizer

def test_optimizer_loads_priors():
    """Test optimizer loads prior distributions"""
    optimizer = WeightsOptimizer()
    assert optimizer.priors is not None
    assert "infra" in optimizer.priors

def test_optimize_returns_posteriors():
    """Test optimize returns posterior weights"""
    optimizer = WeightsOptimizer()
    observations = []  # Empty for now

    posteriors = optimizer.optimize(observations)

    assert "infra" in posteriors
    assert isinstance(posteriors["infra"], float)

def test_validate_safe_range():
    """Test weight validation enforces bounds"""
    optimizer = WeightsOptimizer()

    # Valid weights
    valid_weights = {"infra": 1.0, "perf": 0.8}
    is_valid, issues = optimizer.validate_safe_range(valid_weights)
    assert is_valid
    assert len(issues) == 0

    # Invalid weights (out of bounds)
    invalid_weights = {"infra": 1.5}  # Bounds: [0.8, 1.2]
    is_valid, issues = optimizer.validate_safe_range(invalid_weights)
    assert not is_valid
    assert len(issues) > 0

def test_priors_have_bounds():
    """Test all priors have bounds defined"""
    optimizer = WeightsOptimizer()

    for label, prior in optimizer.priors.items():
        assert "bounds" in prior
        assert len(prior["bounds"]) == 2
        assert prior["bounds"][0] < prior["bounds"][1]
