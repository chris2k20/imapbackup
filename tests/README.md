# IMAP Backup Tests

Comprehensive test suite for the IMAP Backup tool.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [CI/CD Integration](#cicd-integration)
- [Writing Tests](#writing-tests)

## 🎯 Overview

This test suite provides comprehensive coverage for the IMAP Backup tool, including:

- **Unit Tests**: Test individual functions and components
- **Integration Tests**: Test interactions between components
- **Batch Processing Tests**: Verify memory optimization features
- **Retry Logic Tests**: Ensure network resilience
- **Progress Tracking Tests**: Validate user feedback features

## 📁 Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── test_spinner.py          # Tests for progress tracking (Spinner class)
├── test_retry_logic.py      # Tests for network retry mechanism
├── test_batch_processing.py # Tests for memory optimization
├── test_imapbackup.py       # General unit and integration tests
└── README.md                # This file
```

## 🚀 Running Tests

### Prerequisites

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

**Unit tests only:**
```bash
pytest -m unit
```

**Integration tests only:**
```bash
pytest -m integration
```

**Specific test file:**
```bash
pytest tests/test_spinner.py
```

**Specific test function:**
```bash
pytest tests/test_spinner.py::TestSpinner::test_spinner_initialization
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Tests with Coverage Report

```bash
pytest --cov=imapbackup --cov-report=term-missing
```

Generate HTML coverage report:
```bash
pytest --cov=imapbackup --cov-report=html
# Open htmlcov/index.html in your browser
```

### Run Tests in Parallel

For faster execution (requires pytest-xdist):
```bash
pip install pytest-xdist
pytest -n auto
```

## 📊 Test Coverage

The test suite covers:

### Core Functionality (test_imapbackup.py)
- ✅ Utility functions (pretty_byte_count, string_from_file)
- ✅ Message ID handling and regex
- ✅ IMAP LIST response parsing
- ✅ File scanning (scan_file)
- ✅ Folder name retrieval (get_names)
- ✅ Configuration parsing
- ✅ Directory creation

### Progress Tracking (test_spinner.py)
- ✅ Spinner initialization
- ✅ Progress updates
- ✅ Percentage calculations
- ✅ Terminal output formatting
- ✅ nospinner mode

### Retry Logic (test_retry_logic.py)
- ✅ Successful operations
- ✅ Network error recovery
- ✅ Exponential backoff
- ✅ Maximum retry limits
- ✅ Non-network error handling
- ✅ Socket timeout handling
- ✅ IMAP error handling

### Batch Processing (test_batch_processing.py)
- ✅ Batch size configuration
- ✅ Single batch processing
- ✅ Multiple batch processing
- ✅ Batch range calculation
- ✅ Memory cleanup (gc.collect)
- ✅ Large mailbox handling

## 🔄 CI/CD Integration

Tests run automatically on:

- **Push** to main/master/develop branches
- **Pull requests** to main/master/develop branches
- **Manual trigger** via workflow_dispatch

### GitHub Actions Workflow

The CI pipeline (`.github/workflows/ci-tests.yml`) runs:

1. **Test Matrix**: Tests across multiple Python versions (3.8-3.12) and OS (Ubuntu, macOS)
2. **Unit Tests**: Fast, isolated tests
3. **Integration Tests**: Tests with mocked external dependencies
4. **Code Quality**: Linting with flake8 and pylint
5. **Coverage Report**: Uploads to Codecov

### Local CI Simulation

Run the same tests locally:

```bash
# Run all tests with coverage
pytest --cov=imapbackup --cov-report=term-missing

# Run linting
flake8 imapbackup.py --count --max-line-length=127 --statistics
pylint imapbackup.py --exit-zero --max-line-length=127
```

## ✍️ Writing Tests

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_my_function():
    """Unit test for my_function"""
    pass

@pytest.mark.integration
def test_integration_feature():
    """Integration test for feature"""
    pass

@pytest.mark.slow
def test_long_running_operation():
    """Test that takes a long time"""
    pass

@pytest.mark.network
def test_external_api():
    """Test that requires network access"""
    pass
```

### Using Fixtures

Common fixtures are defined in `conftest.py`:

```python
def test_with_temp_directory(temp_dir):
    """Use temp_dir fixture for temporary directory"""
    file_path = os.path.join(temp_dir, "test.txt")
    # temp_dir is automatically cleaned up

def test_with_mock_imap(mock_imap_server):
    """Use mock_imap_server fixture"""
    result = imapbackup.scan_folder(mock_imap_server, "INBOX", True)
    # mock_imap_server is pre-configured
```

### Testing Best Practices

1. **Test one thing at a time**: Each test should verify a single behavior
2. **Use descriptive names**: Test names should explain what is being tested
3. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   def test_example():
       # Arrange
       input_data = "test"

       # Act
       result = function_under_test(input_data)

       # Assert
       assert result == expected_output
   ```
4. **Mock external dependencies**: Use mocks for IMAP, S3, GPG operations
5. **Test edge cases**: Empty inputs, large inputs, error conditions
6. **Keep tests fast**: Unit tests should run in milliseconds

### Example Test

```python
import pytest
import imapbackup

@pytest.mark.unit
class TestMyFeature:
    """Tests for my feature"""

    def test_feature_with_valid_input(self):
        """Test feature with valid input"""
        # Arrange
        input_value = "valid"

        # Act
        result = imapbackup.my_function(input_value)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_feature_with_invalid_input(self):
        """Test feature handles invalid input"""
        with pytest.raises(ValueError):
            imapbackup.my_function(None)
```

## 🐛 Debugging Tests

### Run a single test in verbose mode:
```bash
pytest tests/test_spinner.py::TestSpinner::test_spinner_initialization -v
```

### Show print statements:
```bash
pytest -s
```

### Drop into debugger on failure:
```bash
pytest --pdb
```

### Show local variables on failure:
```bash
pytest -l
```

## 📈 Coverage Goals

Target coverage metrics:
- **Overall**: > 80%
- **Critical functions**: > 95%
  - scan_folder
  - download_messages
  - upload_messages
  - retry_on_network_error

Current coverage can be viewed:
```bash
pytest --cov=imapbackup --cov-report=term-missing
```

## 🤝 Contributing Tests

When adding new features:

1. Write tests first (TDD approach recommended)
2. Ensure all tests pass: `pytest`
3. Check coverage: `pytest --cov=imapbackup`
4. Run linting: `flake8 imapbackup.py`
5. Update this README if adding new test categories

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Coverage Plugin](https://pytest-cov.readthedocs.io/)
- [Python Mocking Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)

## ❓ Troubleshooting

### Tests fail due to missing dependencies
```bash
pip install -r requirements-dev.txt
```

### Import errors
Make sure you're in the project root directory:
```bash
cd /path/to/imapbackup
pytest
```

### Permission errors
Some tests create temporary files. Ensure write permissions:
```bash
chmod +w tests/
```

### Slow tests
Run only fast unit tests:
```bash
pytest -m "unit and not slow"
```

---

**Questions or Issues?**
Please open an issue on GitHub: https://github.com/chris2k20/imapbackup/issues
