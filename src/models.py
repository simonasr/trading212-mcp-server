"""Pydantic models for Trading212 API responses and requests.

This module contains all the data models used by the Trading212 API client,
including enums for various status types and Pydantic models for API
request/response serialization.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

__all__ = [
    # Enums
    "DividendCashActionEnum",
    "Environment",
    "InstrumentIssueNameEnum",
    "InstrumentIssueSeverityEnum",
    "AccountBucketResultStatusEnum",
    "HistoricalOrderExecutorEnum",
    "HistoricalOrderFillTypeEnum",
    "HistoricalOrderStatusEnum",
    "HistoricalOrderTimeValidityEnum",
    "HistoricalOrderTypeEnum",
    "TaxNameEnum",
    "HistoryTransactionTypeEnum",
    "LimitRequestTimeValidityEnum",
    "OrderStatusEnum",
    "OrderStrategyEnum",
    "OrderTypeEnum",
    "PlaceOrderErrorCodeEnum",
    "PositionFrontendEnum",
    "ReportResponseStatusEnum",
    "StopLimitRequestTimeValidityEnum",
    "StopRequestTimeValidityEnum",
    "TimeEventTypeEnum",
    "TradeableInstrumentTypeEnum",
    # Models
    "Account",
    "AccountBucketDetailedResponse",
    "InstrumentIssue",
    "InvestmentResult",
    "AccountBucketInstrumentResult",
    "AccountBucketInstrumentsDetailedResponse",
    "DividendDetails",
    "AccountBucketResultResponse",
    "Cash",
    "DuplicateBucketRequest",
    "EnqueuedReportResponse",
    "TimeEvent",
    "WorkingSchedule",
    "Exchange",
    "Tax",
    "HistoricalOrder",
    "HistoryDividendItem",
    "HistoryTransactionItem",
    "LimitRequest",
    "MarketRequest",
    "Order",
    "PaginatedResponseHistoricalOrder",
    "PaginatedResponseHistoryDividendItem",
    "PaginatedResponseHistoryTransactionItem",
    "PieRequest",
    "PlaceOrderError",
    "Position",
    "PositionRequest",
    "ReportDataIncluded",
    "PublicReportRequest",
    "ReportResponse",
    "StopLimitRequest",
    "StopRequest",
    "TradeableInstrument",
]


# --- ENUMS ---


class DividendCashActionEnum(str, Enum):
    """Action to take with dividend payments."""

    REINVEST = "REINVEST"
    TO_ACCOUNT_CASH = "TO_ACCOUNT_CASH"


class Environment(str, Enum):
    """Trading212 environment type."""

    DEMO = "demo"
    LIVE = "live"


class InstrumentIssueNameEnum(str, Enum):
    """Types of instrument issues."""

    DELISTED = "DELISTED"
    SUSPENDED = "SUSPENDED"
    NO_LONGER_TRADABLE = "NO_LONGER_TRADABLE"
    MAX_POSITION_SIZE_REACHED = "MAX_POSITION_SIZE_REACHED"
    APPROACHING_MAX_POSITION_SIZE = "APPROACHING_MAX_POSITION_SIZE"
    COMPLEX_INSTRUMENT_APP_TEST_REQUIRED = "COMPLEX_INSTRUMENT_APP_TEST_REQUIRED"


class InstrumentIssueSeverityEnum(str, Enum):
    """Severity level of instrument issues."""

    IRREVERSIBLE = "IRREVERSIBLE"
    REVERSIBLE = "REVERSIBLE"
    INFORMATIVE = "INFORMATIVE"


class AccountBucketResultStatusEnum(str, Enum):
    """Status of pie progress towards goal."""

    AHEAD = "AHEAD"
    ON_TRACK = "ON_TRACK"
    BEHIND = "BEHIND"


class HistoricalOrderExecutorEnum(str, Enum):
    """Platform that executed the order."""

    API = "API"
    IOS = "IOS"
    ANDROID = "ANDROID"
    WEB = "WEB"
    SYSTEM = "SYSTEM"
    AUTOINVEST = "AUTOINVEST"


class HistoricalOrderFillTypeEnum(str, Enum):
    """Type of order fill."""

    TOTV = "TOTV"
    OTC = "OTC"


class HistoricalOrderStatusEnum(str, Enum):
    """Status of a historical order."""

    LOCAL = "LOCAL"
    UNCONFIRMED = "UNCONFIRMED"
    CONFIRMED = "CONFIRMED"
    NEW = "NEW"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    REPLACING = "REPLACING"
    REPLACED = "REPLACED"


class HistoricalOrderTimeValidityEnum(str, Enum):
    """Time validity for historical orders."""

    DAY = "DAY"
    GOOD_TILL_CANCEL = "GOOD_TILL_CANCEL"


class HistoricalOrderTypeEnum(str, Enum):
    """Type of historical order."""

    LIMIT = "LIMIT"
    STOP = "STOP"
    MARKET = "MARKET"
    STOP_LIMIT = "STOP_LIMIT"


class TaxNameEnum(str, Enum):
    """Types of taxes and fees."""

    COMMISSION_TURNOVER = "COMMISSION_TURNOVER"
    CURRENCY_CONVERSION_FEE = "CURRENCY_CONVERSION_FEE"
    FINRA_FEE = "FINRA_FEE"
    FRENCH_TRANSACTION_TAX = "FRENCH_TRANSACTION_TAX"
    PTM_LEVY = "PTM_LEVY"
    STAMP_DUTY = "STAMP_DUTY"
    STAMP_DUTY_RESERVE_TAX = "STAMP_DUTY_RESERVE_TAX"
    TRANSACTION_FEE = "TRANSACTION_FEE"


class HistoryTransactionTypeEnum(str, Enum):
    """Type of account transaction."""

    WITHDRAW = "WITHDRAW"
    DEPOSIT = "DEPOSIT"
    FEE = "FEE"
    TRANSFER = "TRANSFER"


class LimitRequestTimeValidityEnum(str, Enum):
    """Time validity for limit orders."""

    DAY = "DAY"
    GOOD_TILL_CANCEL = "GOOD_TILL_CANCEL"


class OrderStatusEnum(str, Enum):
    """Status of an active order."""

    LOCAL = "LOCAL"
    UNCONFIRMED = "UNCONFIRMED"
    CONFIRMED = "CONFIRMED"
    NEW = "NEW"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    REPLACING = "REPLACING"
    REPLACED = "REPLACED"


class OrderStrategyEnum(str, Enum):
    """Order execution strategy."""

    QUANTITY = "QUANTITY"
    VALUE = "VALUE"


class OrderTypeEnum(str, Enum):
    """Type of order."""

    LIMIT = "LIMIT"
    STOP = "STOP"
    MARKET = "MARKET"
    STOP_LIMIT = "STOP_LIMIT"


class PlaceOrderErrorCodeEnum(str, Enum):
    """Error codes for order placement failures."""

    SellingEquityNotOwned = "SellingEquityNotOwned"
    CantLegalyTradeException = "CantLegalyTradeException"
    InsufficientResources = "InsufficientResources"
    InsufficientValueForStocksSell = "InsufficientValueForStocksSell"
    TargetPriceTooFar = "TargetPriceTooFar"
    TargetPriceTooClose = "TargetPriceTooClose"
    NotEligibleForISA = "NotEligibleForISA"
    ShareLendingAgreementNotAccepted = "ShareLendingAgreementNotAccepted"
    InstrumentNotFound = "InstrumentNotFound"
    MaxEquityBuyQuantityExceeded = "MaxEquityBuyQuantityExceeded"
    MaxEquitySellQuantityExceeded = "MaxEquitySellQuantityExceeded"
    LimitPriceMissing = "LimitPriceMissing"
    StopPriceMissing = "StopPriceMissing"
    TickerMissing = "TickerMissing"
    QuantityMissing = "QuantityMissing"
    MaxQuantityExceeded = "MaxQuantityExceeded"
    InvalidValue = "InvalidValue"
    InsufficientFreeForStocksException = "InsufficientFreeForStocksException"
    MinValueExceeded = "MinValueExceeded"
    MinQuantityExceeded = "MinQuantityExceeded"
    PriceTooFar = "PriceTooFar"
    UNDEFINED = "UNDEFINED"
    NotAvailableForRealMoneyAccounts = "NotAvailableForRealMoneyAccounts"


class PositionFrontendEnum(str, Enum):
    """Platform origin of a position."""

    API = "API"
    IOS = "IOS"
    ANDROID = "ANDROID"
    WEB = "WEB"
    SYSTEM = "SYSTEM"
    AUTOINVEST = "AUTOINVEST"


class ReportResponseStatusEnum(str, Enum):
    """Status of a report export."""

    Queued = "Queued"
    Processing = "Processing"
    Running = "Running"
    Canceled = "Canceled"
    Failed = "Failed"
    Finished = "Finished"


class StopLimitRequestTimeValidityEnum(str, Enum):
    """Time validity for stop-limit orders."""

    DAY = "DAY"
    GOOD_TILL_CANCEL = "GOOD_TILL_CANCEL"


class StopRequestTimeValidityEnum(str, Enum):
    """Time validity for stop orders."""

    DAY = "DAY"
    GOOD_TILL_CANCEL = "GOOD_TILL_CANCEL"


class TimeEventTypeEnum(str, Enum):
    """Type of exchange time event."""

    OPEN = "OPEN"
    CLOSE = "CLOSE"
    BREAK_START = "BREAK_START"
    BREAK_END = "BREAK_END"
    PRE_MARKET_OPEN = "PRE_MARKET_OPEN"
    AFTER_HOURS_OPEN = "AFTER_HOURS_OPEN"
    AFTER_HOURS_CLOSE = "AFTER_HOURS_CLOSE"
    OVERNIGHT_OPEN = "OVERNIGHT_OPEN"


class TradeableInstrumentTypeEnum(str, Enum):
    """Type of tradeable instrument."""

    CRYPTOCURRENCY = "CRYPTOCURRENCY"
    ETF = "ETF"
    FOREX = "FOREX"
    FUTURES = "FUTURES"
    INDEX = "INDEX"
    STOCK = "STOCK"
    WARRANT = "WARRANT"
    CRYPTO = "CRYPTO"
    CVR = "CVR"
    CORPACT = "CORPACT"


# --- MODELS ---


class Account(BaseModel):
    """Account metadata information."""

    currencyCode: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code",
        examples=["USD", "EUR", "GBP"],
    )
    id: int = Field(..., description="Account identifier")


class AccountBucketDetailedResponse(BaseModel):
    """Detailed pie/bucket configuration."""

    creationDate: datetime | None = None
    dividendCashAction: DividendCashActionEnum | None = None
    endDate: datetime | None = None
    goal: float | None = None
    icon: str | None = None
    id: int | None = None
    initialInvestment: float | None = None
    instrumentShares: dict[str, float] | None = None
    name: str | None = None
    publicUrl: str | None = None


class InstrumentIssue(BaseModel):
    """Issue affecting an instrument."""

    name: InstrumentIssueNameEnum
    severity: InstrumentIssueSeverityEnum


class InvestmentResult(BaseModel):
    """Investment performance result."""

    priceAvgInvestedValue: float | None = None
    priceAvgResult: float | None = None
    priceAvgResultCoef: float | None = None
    priceAvgValue: float | None = None


class AccountBucketInstrumentResult(BaseModel):
    """Instrument result within a pie."""

    currentShare: float | None = None
    expectedShare: float | None = None
    issues: list[InstrumentIssue] | None = None
    ownedQuantity: float | None = None
    result: InvestmentResult | None = None
    ticker: str | None = None


class AccountBucketInstrumentsDetailedResponse(BaseModel):
    """Detailed pie response with instruments."""

    instruments: list[AccountBucketInstrumentResult] | None = None
    settings: AccountBucketDetailedResponse | None = None


class DividendDetails(BaseModel):
    """Dividend payment details."""

    gained: float | None = None
    inCash: float | None = None
    reinvested: float | None = None


class AccountBucketResultResponse(BaseModel):
    """Pie result summary."""

    cash: float | None = None
    dividendDetails: DividendDetails | None = None
    id: int | None = None
    progress: float | None = None
    result: InvestmentResult | None = None
    status: AccountBucketResultStatusEnum | None = None


class Cash(BaseModel):
    """Account cash balance information."""

    blocked: float | None = None
    free: float | None = None
    invested: float | None = None
    pieCash: float | None = None
    ppl: float | None = None
    result: float | None = None
    total: float | None = None


class DuplicateBucketRequest(BaseModel):
    """Request to duplicate a pie."""

    icon: str | None = None
    name: str | None = None


class EnqueuedReportResponse(BaseModel):
    """Response when a report export is queued."""

    reportId: int


class TimeEvent(BaseModel):
    """Exchange time event."""

    date: datetime
    type: TimeEventTypeEnum


class WorkingSchedule(BaseModel):
    """Exchange working schedule."""

    id: int
    timeEvents: list[TimeEvent]


class Exchange(BaseModel):
    """Exchange information with working schedules."""

    id: int
    name: str
    workingSchedules: list[WorkingSchedule]


class Tax(BaseModel):
    """Tax or fee charge."""

    fillId: str | None = None
    name: TaxNameEnum | None = None
    quantity: float | None = None
    timeCharged: datetime | None = None


class HistoricalOrder(BaseModel):
    """Historical order record."""

    dateCreated: datetime | None = None
    dateExecuted: datetime | None = None
    dateModified: datetime | None = None
    executor: HistoricalOrderExecutorEnum | None = None
    fillCost: float | None = None
    fillId: int | None = None
    fillPrice: float | None = None
    fillResult: float | None = None
    fillType: HistoricalOrderFillTypeEnum | None = None
    filledQuantity: float | None = None
    filledValue: float | None = None
    id: int | None = None
    limitPrice: float | None = None
    orderedQuantity: float | None = None
    orderedValue: float | None = None
    parentOrder: int | None = None
    status: HistoricalOrderStatusEnum | None = None
    stopPrice: float | None = None
    taxes: list[Tax] | None = None
    ticker: str | None = None
    timeValidity: HistoricalOrderTimeValidityEnum | None = None
    type: HistoricalOrderTypeEnum | None = None


class HistoryDividendItem(BaseModel):
    """Historical dividend payment."""

    amount: float | None = None
    amountInEuro: float | None = None
    grossAmountPerShare: float | None = None
    paidOn: datetime | None = None
    quantity: float | None = None
    reference: str | None = None
    ticker: str | None = None
    type: str | None = None


class HistoryTransactionItem(BaseModel):
    """Historical account transaction."""

    amount: float | None = None
    dateTime: datetime | None = None
    reference: str | None = None
    type: HistoryTransactionTypeEnum | None = None


class LimitRequest(BaseModel):
    """Request to place a limit order."""

    limitPrice: float
    quantity: float
    ticker: str
    timeValidity: LimitRequestTimeValidityEnum


class MarketRequest(BaseModel):
    """Request to place a market order."""

    quantity: float
    ticker: str


class Order(BaseModel):
    """Active order information."""

    creationTime: datetime | None = None
    filledQuantity: float | None = None
    filledValue: float | None = None
    id: int | None = None
    limitPrice: float | None = None
    quantity: float | None = None
    status: OrderStatusEnum | None = None
    stopPrice: float | None = None
    strategy: OrderStrategyEnum | None = None
    ticker: str | None = None
    type: OrderTypeEnum | None = None
    value: float | None = None


class PaginatedResponseHistoricalOrder(BaseModel):
    """Paginated response for historical orders."""

    items: list[HistoricalOrder]
    nextPagePath: str | None = None


class PaginatedResponseHistoryDividendItem(BaseModel):
    """Paginated response for dividend history."""

    items: list[HistoryDividendItem]
    nextPagePath: str | None = None


class PaginatedResponseHistoryTransactionItem(BaseModel):
    """Paginated response for transaction history."""

    items: list[HistoryTransactionItem]
    nextPagePath: str | None = None


class PieRequest(BaseModel):
    """Request to create or update a pie."""

    dividendCashAction: DividendCashActionEnum | None = Field(
        default=None,
        description="How dividends are handled",
        examples=[
            DividendCashActionEnum.REINVEST,
            DividendCashActionEnum.TO_ACCOUNT_CASH,
        ],
    )
    endDate: datetime | None = Field(default=None)
    goal: float | None = Field(
        default=None,
        description="Total desired value of the pie in account currency",
    )
    icon: str | None = Field(default=None)
    instrumentShares: dict[str, float] | None = Field(
        default=None,
        examples=[{"AAPL_US_EQ": 0.5, "MSFT_US_EQ": 0.5}],
        description="The shares of each instrument in the pie",
    )
    name: str | None = Field(default=None)


class PlaceOrderError(BaseModel):
    """Error response when placing an order fails."""

    clarification: str | None = None
    code: PlaceOrderErrorCodeEnum | None = None


class Position(BaseModel):
    """Open position information."""

    averagePrice: float | None = None
    currentPrice: float | None = None
    frontend: PositionFrontendEnum | None = None
    fxPpl: float | None = None
    initialFillDate: datetime | None = None
    maxBuy: float | None = None
    maxSell: float | None = None
    pieQuantity: float | None = None
    ppl: float | None = None
    quantity: float | None = None
    ticker: str | None = None


class PositionRequest(BaseModel):
    """Request to search for a position."""

    ticker: str


class ReportDataIncluded(BaseModel):
    """Data to include in a report export."""

    includeDividends: bool | None = True
    includeInterest: bool | None = True
    includeOrders: bool | None = True
    includeTransactions: bool | None = True


class PublicReportRequest(BaseModel):
    """Request to generate a report export."""

    dataIncluded: ReportDataIncluded | None = None
    timeFrom: datetime | None = None
    timeTo: datetime | None = None


class ReportResponse(BaseModel):
    """Report export response."""

    dataIncluded: ReportDataIncluded | None = None
    downloadLink: str | None = None
    reportId: int | None = None
    status: ReportResponseStatusEnum | None = None
    timeFrom: datetime | None = None
    timeTo: datetime | None = None


class StopLimitRequest(BaseModel):
    """Request to place a stop-limit order."""

    limitPrice: float
    quantity: float
    stopPrice: float
    ticker: str
    timeValidity: StopLimitRequestTimeValidityEnum


class StopRequest(BaseModel):
    """Request to place a stop order."""

    quantity: float
    stopPrice: float
    ticker: str
    timeValidity: StopRequestTimeValidityEnum


class TradeableInstrument(BaseModel):
    """Tradeable instrument information."""

    addedOn: datetime | None = None
    currencyCode: str | None = None
    isin: str | None = None
    maxOpenQuantity: float | None = None
    minTradeQuantity: float | None = None
    name: str | None = None
    shortName: str | None = None
    ticker: str | None = None
    type: TradeableInstrumentTypeEnum | None = None
    workingScheduleId: int | None = None


# Fix forward references if needed
WorkingSchedule.model_rebuild()
