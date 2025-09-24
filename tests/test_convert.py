from datetime import datetime, date, timedelta, UTC

from pytest import mark, raises

from liqpy import to_date, to_datetime, datetime_from_millis


class TestToDate:
    """Test cases for the to_date function."""
    
    @mark.parametrize("input_value,expected", [
        (datetime(2023, 5, 15, 14, 30, 45, tzinfo=UTC), date(2023, 5, 15)),
        (datetime(2023, 12, 31, 23, 59, 59), date(2023, 12, 31)),
        (datetime(2020, 2, 29, 12, 0, 0), date(2020, 2, 29)),  # Leap year
    ])
    def test_to_date_from_datetime(self, input_value, expected):
        """Test converting datetime to date."""
        result = to_date(input_value)
        assert result == expected
        assert isinstance(result, date)
    
    @mark.parametrize("input_value", [
        date(2023, 5, 15),
        date(2020, 2, 29),
        date(1999, 12, 31),
    ])
    def test_to_date_from_date(self, input_value):
        """Test converting date to date (noop)."""
        result = to_date(input_value)
        assert result == input_value
        assert result is input_value  # Should return the same object
        assert isinstance(result, date)
    
    @mark.parametrize("input_value,expected", [
        ("2023-05-15", date(2023, 5, 15)),
        ("2020-02-29", date(2020, 2, 29)),
        ("1999-12-31", date(1999, 12, 31)),
        ("2000-01-01", date(2000, 1, 1)),
    ])
    def test_to_date_from_string(self, input_value, expected):
        """Test converting ISO format string to date."""
        result = to_date(input_value)
        assert result == expected
        assert isinstance(result, date)
    
    @mark.parametrize("invalid_string", [
        "invalid-date",
        "2023-13-01",  # Invalid month
        "2023-02-30",  # Invalid day
        "not-a-date",
        "",
    ])
    def test_to_date_from_string_invalid(self, invalid_string):
        """Test converting invalid string raises ValueError."""
        with raises(ValueError):
            to_date(invalid_string)
    
    @mark.parametrize("delta_days", [5, -3, 0, 14])  # 14 days = 2 weeks
    def test_to_date_from_timedelta(self, delta_days):
        """Test converting timedelta to date (relative to today)."""
        today = date.today()
        delta = timedelta(days=delta_days)
        expected = today + delta
        
        result = to_date(delta)
        assert result == expected
        assert isinstance(result, date)
    
    @mark.parametrize("input_value,expected", [
        (1684166400000, date(2023, 5, 15)),  # 2023-05-15 16:00:00 UTC
        (1684166400.5, date(2023, 5, 15)),  # With fractional seconds
        (0, date(1970, 1, 1)),  # Unix epoch
        (946684800000, date(2000, 1, 1)),  # Y2K
    ])
    def test_to_date_from_timestamp(self, input_value, expected):
        """Test converting timestamp (float/int) to date."""
        result = to_date(input_value)
        assert result == expected
        assert isinstance(result, date)
    
    @mark.parametrize("invalid_input", [
        None,
        [1, 2, 3],
        {"key": "value"},
        object(),
    ])
    def test_to_date_unsupported_type(self, invalid_input):
        """Test that unsupported types raise NotImplementedError."""
        with raises(NotImplementedError):
            to_date(invalid_input)  # type: ignore


class TestToDatetime:
    """Test cases for the to_datetime function."""
    
    @mark.parametrize("input_value", [
        datetime(2023, 5, 15, 14, 30, 45, tzinfo=UTC),
        datetime(2020, 2, 29, 23, 59, 59),
        datetime(1999, 12, 31, 0, 0, 0, tzinfo=UTC),
    ])
    def test_to_datetime_from_datetime(self, input_value):
        """Test converting datetime to datetime (noop)."""
        result = to_datetime(input_value)
        assert result == input_value
        assert result is input_value  # Should return the same object
        assert isinstance(result, datetime)
    
    @mark.parametrize("input_value,expected", [
        ("2023-05-15T14:30:45", datetime(2023, 5, 15, 14, 30, 45)),
        ("2023-05-15T14:30:45+00:00", datetime(2023, 5, 15, 14, 30, 45, tzinfo=UTC)),
        ("2020-02-29T23:59:59", datetime(2020, 2, 29, 23, 59, 59)),
        ("1999-12-31T00:00:00", datetime(1999, 12, 31, 0, 0, 0)),
    ])
    def test_to_datetime_from_string(self, input_value, expected):
        """Test converting ISO format string to datetime."""
        result = to_datetime(input_value)
        assert result == expected
        assert isinstance(result, datetime)
    
    @mark.parametrize("invalid_string", [
        "invalid-datetime",
        "2023-13-01T14:30:45",  # Invalid month
        "2023-02-30T14:30:45",  # Invalid day
        "not-a-datetime",
        "",
        "2023-05-15T25:00:00",  # Invalid hour
    ])
    def test_to_datetime_from_string_invalid(self, invalid_string):
        """Test converting invalid string raises ValueError."""
        with raises(ValueError):
            to_datetime(invalid_string)
    
    @mark.parametrize("input_value,expected", [
        (1684166445000, datetime(2023, 5, 15, 16, 0, 45, tzinfo=UTC)),  # Int timestamp
        (1684166445.5, datetime(2023, 5, 15, 16, 0, 45, 500000, tzinfo=UTC)),  # Float timestamp
        (0, datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)),  # Unix epoch
        (946684800000, datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC)),  # Y2K
    ])
    def test_to_datetime_from_timestamp(self, input_value, expected):
        """Test converting timestamp to datetime."""
        result = to_datetime(input_value)  # type: ignore
        assert result == expected
        assert isinstance(result, datetime)
    
    @mark.parametrize("delta", [
        timedelta(hours=2, minutes=30),
        timedelta(days=1),
        timedelta(seconds=3600),
        timedelta(microseconds=500000),
    ])
    def test_to_datetime_from_timedelta(self, delta):
        """Test converting timedelta to datetime (relative to now)."""
        before = datetime.now(UTC)
        result = to_datetime(delta)
        after = datetime.now(UTC)
        
        # Result should be approximately now + delta
        # Allow for small time differences due to execution time
        expected_min = before + delta
        expected_max = after + delta
        assert expected_min <= result <= expected_max
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC
    
    @mark.parametrize("invalid_input", [
        None,
        [1, 2, 3],
        {"key": "value"},
        object(),
    ])
    def test_to_datetime_unsupported_type(self, invalid_input):
        """Test that unsupported types raise NotImplementedError."""
        with raises(NotImplementedError):
            to_datetime(invalid_input)  # type: ignore


class TestDatetimeFromMillis:
    """Test cases for the datetime_from_millis function."""
    
    @mark.parametrize("input_millis,expected", [
        (1684166445000, datetime(2023, 5, 15, 16, 0, 45, tzinfo=UTC)),  # Basic
        (1684166445500, datetime(2023, 5, 15, 16, 0, 45, 500000, tzinfo=UTC)),  # With microseconds
        (0, datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)),  # Unix epoch
        (946684800000, datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC)),  # Y2K
        (1577836800000, datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)),  # 2020
    ])
    def test_datetime_from_millis_basic(self, input_millis, expected):
        """Test converting milliseconds to datetime."""
        result = datetime_from_millis(input_millis)
        assert result == expected
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC
    
    def test_datetime_from_millis_negative(self):
        """Test converting negative milliseconds (before Unix epoch)."""
        # Use a timestamp that's supported on Windows (after 1970-01-01)
        # Let's test with a small positive value instead, or skip negative on Windows
        import sys
        if sys.platform == "win32":
            # On Windows, test with a small positive timestamp
            millis = 86400000  # One day after epoch
            result = datetime_from_millis(millis)
            expected = datetime(1970, 1, 2, 0, 0, 0, tzinfo=UTC)
            assert result == expected
        else:
            # On Unix systems, test negative timestamp
            millis = -86400000  # One day before epoch
            result = datetime_from_millis(millis)
            expected = datetime(1969, 12, 31, 0, 0, 0, tzinfo=UTC)
            assert result == expected
        
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    @mark.parametrize("original_dt", [
        datetime(2023, 5, 15, 12, 0, 45, 500000, tzinfo=UTC),
        datetime(2020, 2, 29, 23, 59, 59, 123000, tzinfo=UTC),
        datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC),
        datetime(2000, 1, 1, 12, 30, 45, 750000, tzinfo=UTC),
    ])
    def test_round_trip_datetime_millis(self, original_dt):
        """Test converting datetime to millis and back."""
        from liqpy import to_milliseconds
        
        millis = to_milliseconds(original_dt)
        result = datetime_from_millis(millis)
        
        # Should be equal (microseconds might be lost due to millisecond precision)
        assert abs((result - original_dt).total_seconds()) < 0.001
    
    @mark.parametrize("iso_string,expected_attrs", [
        ("2023-05-15T14:30:45+00:00", (2023, 5, 15, 14, 30, 45)),
        ("2020-02-29T23:59:59", (2020, 2, 29, 23, 59, 59)),
        ("1999-12-31T00:00:00", (1999, 12, 31, 0, 0, 0)),
        ("2000-01-01T12:00:00+00:00", (2000, 1, 1, 12, 0, 0)),
    ])
    def test_round_trip_string_datetime(self, iso_string, expected_attrs):
        """Test converting string to datetime and comparing with direct conversion."""
        dt_result = to_datetime(iso_string)
        
        # Should produce a valid datetime
        assert isinstance(dt_result, datetime)
        year, month, day, hour, minute, second = expected_attrs
        assert dt_result.year == year
        assert dt_result.month == month
        assert dt_result.day == day
        assert dt_result.hour == hour
        assert dt_result.minute == minute
        assert dt_result.second == second
    
    @mark.parametrize("input_dt", [
        datetime(2023, 5, 15, 14, 30, 45, tzinfo=UTC),
        datetime(2020, 2, 29, 23, 59, 59),
        datetime(1999, 12, 31, 0, 0, 0, tzinfo=UTC),
    ])
    def test_date_datetime_consistency(self, input_dt):
        """Test that date conversion from datetime is consistent."""
        date_result = to_date(input_dt)
        
        assert date_result.year == input_dt.year
        assert date_result.month == input_dt.month
        assert date_result.day == input_dt.day
