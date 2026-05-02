"""Data schema definitions — what valid data looks like at each pipeline stage."""
import pandera as pa
from pandera import Column, Check, DataFrameSchema


# Schema for the raw merged train+store data, BEFORE preprocessing
RAW_MERGED_SCHEMA = DataFrameSchema(
    {
        "Store": Column(int, Check.greater_than(0)),
        "DayOfWeek": Column(int, Check.in_range(1, 7)),
        "Date": Column(object),  # string at this stage; parsed later
        "Sales": Column(int, Check.greater_than_or_equal_to(0)),
        "Customers": Column(int, Check.greater_than_or_equal_to(0)),
        "Open": Column(int, Check.isin([0, 1])),
        "Promo": Column(int, Check.isin([0, 1])),
        "StateHoliday": Column(object),  # mixed types in raw data
        "SchoolHoliday": Column(int, Check.isin([0, 1])),
    },
    strict=False,  # allow extra columns
    coerce=True,
)


# Schema for cleaned data, READY for feature building
CLEANED_SCHEMA = DataFrameSchema(
    {
        "Store": Column(int, Check.greater_than(0)),
        "DayOfWeek": Column(int, Check.in_range(1, 7)),
        "Date": Column("datetime64[ns]"),
        "Sales": Column(int, Check.greater_than(0)),  # zeros dropped
        "Customers": Column(int, Check.greater_than_or_equal_to(0)),
        "Open": Column(int, Check.isin([0, 1])),
        "Promo": Column(int, Check.isin([0, 1])),
        "SchoolHoliday": Column(int, Check.isin([0, 1])),
    },
    strict=False,
    coerce=True,
)


# Schema for inference inputs — what the API will accept (Phase 4 will use this)
INFERENCE_INPUT_SCHEMA = DataFrameSchema(
    {
        "Store": Column(int, Check.greater_than(0)),
        "DayOfWeek": Column(int, Check.in_range(1, 7)),
        "Open": Column(int, Check.isin([0, 1])),
        "Promo": Column(int, Check.isin([0, 1])),
        "SchoolHoliday": Column(int, Check.isin([0, 1])),
        "CompetitionDistance": Column(float, Check.greater_than_or_equal_to(0), nullable=True),
    },
    strict=False,
    coerce=True,
)