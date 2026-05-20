"""
ITCH 5.0 full specification as a DiscriminatedProtocol.

All messages share an 11-byte common header:
  message_type     : 1 byte,  offset 0  (discriminator)
  stock_locate     : 2 bytes, offset 1
  tracking_number  : 2 bytes, offset 3
  timestamp        : 6 bytes, offset 5  (nanoseconds since midnight)

The 22 message types and their total lengths:
  'S' (0x53)  System Event                   12 bytes
  'R' (0x52)  Stock Directory                39 bytes
  'H' (0x48)  Stock Trading Action           25 bytes
  'Y' (0x59)  Reg SHO Short Sale             20 bytes
  'L' (0x4C)  Market Participant Position    26 bytes
  'V' (0x56)  MWCB Decline Level             35 bytes
  'W' (0x57)  MWCB Status Level              12 bytes
  'K' (0x4B)  IPO Quoting Period Update      28 bytes
  'J' (0x4A)  LULD Auction Collar            35 bytes
  'h' (0x68)  Operational Halt               21 bytes
  'A' (0x41)  Add Order (no MPID)            36 bytes
  'F' (0x46)  Add Order (MPID Attribution)   40 bytes
  'E' (0x45)  Order Executed                 31 bytes
  'C' (0x43)  Order Executed with Price      36 bytes
  'X' (0x58)  Order Cancel                   23 bytes
  'D' (0x44)  Order Delete                   19 bytes
  'U' (0x55)  Order Replace                  35 bytes
  'P' (0x50)  Trade Message (Non-Cross)      44 bytes
  'Q' (0x51)  Cross Trade                    40 bytes
  'B' (0x42)  Broken Trade                   19 bytes
  'I' (0x49)  NOII                           50 bytes
  'N' (0x4E)  Retail Interest Message        20 bytes

Field naming convention: when the same semantic concept occupies different
byte offsets in different message types, distinct field names are used so
each gets its own output port. Fields at the same offset and width across
multiple message types share a single Field object.

Price fields use a fixed-point representation with 4 implied decimal places
(divide by 10000 to get the actual price in dollars).

Stock symbol fields (8 bytes) are right-padded with ASCII spaces (0x20).
"""

from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.discriminated_protocol import DiscriminatedProtocol

# Common header (all variants, offsets 0-10)

MSG_TYPE        = Field("message_type",    offset=0, width=8)
STOCK_LOCATE    = Field("stock_locate",    offset=1, width=16)
TRACKING_NUMBER = Field("tracking_number", offset=3, width=16)
# Nanoseconds since midnight Eastern Time
TIMESTAMP       = Field("timestamp",       offset=5, width=48)

# Shared variant fields reused across multiple message types

# offset 11, 64 bits: stock symbol (8 ASCII chars) in admin/reference messages
STOCK = Field("stock", offset=11, width=64)

# offset 11, 64 bits: order reference number for order-management messages
# Unique identifier assigned by NASDAQ for each new order
ORDER_REFERENCE_NUMBER = Field("order_reference_number", offset=11, width=64)

# offset 19, 8 bits: 'B' = Buy Order, 'S' = Sell Order
BUY_SELL_INDICATOR = Field("buy_sell_indicator", offset=19, width=8)

# offset 19, 32 bits: shares executed (Order Executed / Order Executed w/ Price)
EXECUTED_SHARES = Field("executed_shares", offset=19, width=32)

# offset 20, 32 bits: order share quantity (Add Order / Trade Message)
SHARES = Field("shares", offset=20, width=32)

# offset 23, 64 bits: match/execution identifier (Executed / Executed w/ Price)
MATCH_NUMBER = Field("match_number", offset=23, width=64)

# offset 24, 64 bits: stock symbol in order/trade messages (8 ASCII chars, space-padded)
ORDER_STOCK = Field("order_stock", offset=24, width=64)

# offset 32, 32 bits: limit price with 4 implied decimal places
PRICE = Field("price", offset=32, width=32)

# 'S' System Event (12 bytes)
# event_code values: 'O'=Start of Messages, 'S'=Start of System Hours,
# 'Q'=Start of Market Hours, 'M'=End of Market Hours,
# 'E'=End of System Hours, 'C'=End of Messages
EVENT_CODE = Field("event_code", offset=11, width=8)

# 'R' Stock Directory (39 bytes)
# market_category: 'N'=NYSE, 'G'=NASDAQ Global Select Market,
#   'S'=NASDAQ Global Market, 'M'=NASDAQ Capital Market,
#   'E'=NYSE MKT, 'A'=NYSE Alternext, 'P'=NYSE Arca, ' '=Not Available
MARKET_CATEGORY               = Field("market_category",                offset=19, width=8)
# financial_status_indicator: 'D'=Deficient, 'E'=Delinquent,
#   'Q'=Bankrupt, 'S'=Suspended, 'G'=Deficient and Bankrupt,
#   'H'=Deficient and Delinquent, 'J'=Delinquent and Bankrupt,
#   'K'=Deficient, Delinquent, and Bankrupt, 'C'=Creations/Redemptions Suspended,
#   'N'=Normal (Internal), ' '=Normal (NASDAQ Global Select Market only)
FINANCIAL_STATUS_INDICATOR    = Field("financial_status_indicator",     offset=20, width=8)
# Minimum number of shares required for a round lot
ROUND_LOT_SIZE                = Field("round_lot_size",                 offset=21, width=32)
# round_lots_only: 'Y'=Only round lot orders accepted, 'N'=Odd lots allowed
ROUND_LOTS_ONLY               = Field("round_lots_only",                offset=25, width=8)
# issue_classification: SIC code per NASDAQ specification
ISSUE_CLASSIFICATION          = Field("issue_classification",           offset=26, width=8)
# Two-character issue sub-type field
ISSUE_SUB_TYPE                = Field("issue_sub_type",                 offset=27, width=16)
# authenticity: 'P'=Live/Production, 'T'=Test
AUTHENTICITY                  = Field("authenticity",                   offset=29, width=8)
# short_sale_threshold_indicator: 'Y'=Restricted, 'N'=Not Restricted, ' '=Not Available
SHORT_SALE_THRESHOLD          = Field("short_sale_threshold_indicator", offset=30, width=8)
# ipo_flag: 'Y'=NASDAQ IPO, 'N'=Not NASDAQ IPO, ' '=Not Available
IPO_FLAG                      = Field("ipo_flag",                       offset=31, width=8)
# luld_reference_price_tier: '1'=Tier 1 NMS Stock, '2'=Tier 2 NMS Stock, ' '=Not Available
LULD_REFERENCE_PRICE_TIER     = Field("luld_reference_price_tier",      offset=32, width=8)
# etp_flag: 'Y'=Exchange Traded Product, 'N'=Not ETP, ' '=Not Available
ETP_FLAG                      = Field("etp_flag",                       offset=33, width=8)
# Leverage factor for Exchange Traded Products
ETP_LEVERAGE_FACTOR           = Field("etp_leverage_factor",            offset=34, width=32)
# inverse_indicator: 'Y'=Inverse ETP, 'N'=Not Inverse ETP
INVERSE_INDICATOR             = Field("inverse_indicator",              offset=38, width=8)

# 'H' Stock Trading Action (25 bytes)
# trading_state: 'H'=Halted across all US equity markets,
#   'P'=Paused across all US equity markets (NASDAQ-listed only),
#   'Q'=Quotation Only Period, 'T'=Trading on NASDAQ
TRADING_STATE = Field("trading_state", offset=19, width=8)
# Reserved byte, not used
RESERVED      = Field("reserved",      offset=20, width=8)
# 4-character reason code for the trading action (see NASDAQ specification)
REASON        = Field("reason",        offset=21, width=32)

# 'Y' Reg SHO Short Sale Price Test Restricted Indicator (20 bytes)
# reg_sho_action: '0'=No price test in effect,
#   '1'=Reg SHO Short Sale Price Test Restriction activated,
#   '2'=Reg SHO Short Sale Price Test Restriction continued,
#   '3'=Reg SHO Short Sale Price Test Restriction deactivated
REG_SHO_ACTION = Field("reg_sho_action", offset=19, width=8)

# 'L' Market Participant Position (26 bytes)
# mpid: 4-character NASDAQ market participant identifier (ASCII)
MPID                     = Field("mpid",                     offset=11, width=32)
# 8-character stock symbol for the participant position entry
PARTICIPANT_STOCK        = Field("participant_stock",        offset=15, width=64)
# primary_market_maker: 'Y'=Primary Market Maker, 'N'=Non-Primary Market Maker
PRIMARY_MARKET_MAKER     = Field("primary_market_maker",     offset=23, width=8)
# market_maker_mode: 'N'=Normal, 'P'=Passive, 'S'=Syndicate,
#   'R'=Pre-Syndicate, 'L'=Penalty
MARKET_MAKER_MODE        = Field("market_maker_mode",        offset=24, width=8)
# market_participant_state: 'A'=Active, 'E'=Excused Withdrawn,
#   'W'=Withdrawn, 'S'=Suspended, 'D'=Deleted
MARKET_PARTICIPANT_STATE = Field("market_participant_state", offset=25, width=8)

# 'V' MWCB Decline Level Message (35 bytes)
# Price levels defining Market-Wide Circuit Breaker thresholds (fixed-point, 4 decimals)
LEVEL_1 = Field("level_1", offset=11, width=64)
LEVEL_2 = Field("level_2", offset=19, width=64)
LEVEL_3 = Field("level_3", offset=27, width=64)

# 'W' MWCB Status Level Message (12 bytes)
# breached_level: '1'=Level 1, '2'=Level 2, '3'=Level 3
BREACHED_LEVEL = Field("breached_level", offset=11, width=8)

# 'K' IPO Quoting Period Update (28 bytes)
# Seconds since midnight when IPO quotation period is expected to begin
IPO_QUOTATION_RELEASE_TIME      = Field("ipo_quotation_release_time",      offset=19, width=32)
# ipo_quotation_release_qualifier: 'A'=Anticipated Quotation Time,
#   'C'=IPO Release Canceled/Postponed
IPO_QUOTATION_RELEASE_QUALIFIER = Field("ipo_quotation_release_qualifier", offset=23, width=8)
# Anticipated IPO price (fixed-point, 4 implied decimal places)
IPO_PRICE                       = Field("ipo_price",                       offset=24, width=32)

# 'J' LULD Auction Collar Message (35 bytes)
# All prices are fixed-point with 4 implied decimal places
AUCTION_COLLAR_REFERENCE_PRICE = Field("auction_collar_reference_price", offset=19, width=32)
UPPER_AUCTION_COLLAR_PRICE     = Field("upper_auction_collar_price",     offset=23, width=32)
LOWER_AUCTION_COLLAR_PRICE     = Field("lower_auction_collar_price",     offset=27, width=32)
# Extension time in seconds for the LULD auction collar
AUCTION_COLLAR_EXTENSION       = Field("auction_collar_extension",       offset=31, width=32)

# 'h' Operational Halt (21 bytes)
# market_code: 'Q'=NASDAQ, 'B'=BX, 'X'=PSX
MARKET_CODE             = Field("market_code",             offset=19, width=8)
# operational_halt_action: 'H'=Operationally Halted, 'T'=Trading Resumed
OPERATIONAL_HALT_ACTION = Field("operational_halt_action", offset=20, width=8)

# 'F' Add Order with MPID Attribution (40 bytes, extends 'A')
# 4-character MPID of the market participant who submitted the order
ATTRIBUTION = Field("attribution", offset=36, width=32)

# 'C' Order Executed with Price (36 bytes, extends 'E')
# printable: 'Y'=Printable (appears in NASDAQ Time and Sales), 'N'=Non-Printable
PRINTABLE       = Field("printable",       offset=31, width=8)
# Execution price (fixed-point, 4 implied decimal places)
EXECUTION_PRICE = Field("execution_price", offset=32, width=32)

# 'X' Order Cancel (23 bytes)
# Number of shares cancelled from an existing order
CANCELLED_SHARES = Field("cancelled_shares", offset=19, width=32)

# 'U' Order Replace (35 bytes)
ORIGINAL_ORDER_REFERENCE_NUMBER = Field("original_order_reference_number", offset=11, width=64)
NEW_ORDER_REFERENCE_NUMBER      = Field("new_order_reference_number",      offset=19, width=64)
REPLACE_SHARES                  = Field("replace_shares",                  offset=27, width=32)
# New limit price (fixed-point, 4 implied decimal places)
REPLACE_PRICE                   = Field("replace_price",                   offset=31, width=32)

# 'P' Trade Message, Non-Cross (44 bytes)
# Unique match number assigned to the executed trade
TRADE_MATCH_NUMBER = Field("trade_match_number", offset=36, width=64)

# 'Q' Cross Trade (40 bytes)
# Number of shares matched in the NASDAQ cross
CROSS_SHARES       = Field("cross_shares",       offset=11, width=64)
# Stock symbol (8 ASCII chars, space-padded) for the cross trade
CROSS_STOCK        = Field("cross_stock",        offset=19, width=64)
# Crossing price (fixed-point, 4 implied decimal places)
CROSS_PRICE        = Field("cross_price",        offset=27, width=32)
CROSS_MATCH_NUMBER = Field("cross_match_number", offset=31, width=64)
# cross_type: 'O'=Opening Cross, 'C'=Closing Cross,
#   'H'=IPO/Halt/Resumption Cross, 'I'=Intraday Cross
CROSS_TYPE         = Field("cross_type",         offset=39, width=8)

# 'B' Broken Trade / Order Execution (19 bytes)
# Match number of the execution being broken
BROKEN_MATCH_NUMBER = Field("broken_match_number", offset=11, width=64)

# 'I' Net Order Imbalance Indicator / NOII (50 bytes)
# paired_shares: number of shares matched at the current reference price
PAIRED_SHARES             = Field("paired_shares",             offset=11, width=64)
# imbalance_shares: number of shares not paired at the reference price
IMBALANCE_SHARES          = Field("imbalance_shares",          offset=19, width=64)
# imbalance_direction: 'B'=Buy Imbalance, 'S'=Sell Imbalance,
#   'N'=No Imbalance, 'O'=Insufficient Orders to Calculate
IMBALANCE_DIRECTION       = Field("imbalance_direction",       offset=27, width=8)
# 8-character stock symbol (space-padded)
NOII_STOCK                = Field("noii_stock",                offset=28, width=64)
# Far price: expected price when the NASDAQ cross opens (4 decimals)
FAR_PRICE                 = Field("far_price",                 offset=36, width=32)
# Near price: price at which the imbalance can be resolved (4 decimals)
NEAR_PRICE                = Field("near_price",                offset=40, width=32)
# Reference price used to calculate the imbalance (4 decimals)
CURRENT_REFERENCE_PRICE   = Field("current_reference_price",   offset=44, width=32)
# noii_cross_type: 'O'=Opening Cross, 'C'=Closing Cross,
#   'H'=IPO/Halt/Resumption Cross, 'I'=Intraday Cross
NOII_CROSS_TYPE           = Field("noii_cross_type",           offset=48, width=8)
# price_variation_indicator: 'L'=Less than 1%,
#   '1'-'9'=1% through 9%, 'G'=Greater than 10%
PRICE_VARIATION_INDICATOR = Field("price_variation_indicator", offset=49, width=8)

# 'N' Retail Interest Message (20 bytes)
# interest_flag: 'B'=Retail Buy Interest, 'S'=Retail Sell Interest,
#   'A'=Retail Buy and Sell Interest
INTEREST_FLAG = Field("interest_flag", offset=19, width=8)

# Protocol object

ITCH_PARSER = DiscriminatedProtocol(
    name="itch",
    discriminator=MSG_TYPE,
    forward=False,
    fields=[MSG_TYPE, STOCK_LOCATE, TRACKING_NUMBER, TIMESTAMP],
    variants={
        0x53: [EVENT_CODE],                                                         # 'S' System Event
        0x52: [                                                                     # 'R' Stock Directory
            STOCK, MARKET_CATEGORY, FINANCIAL_STATUS_INDICATOR,
            ROUND_LOT_SIZE, ROUND_LOTS_ONLY, ISSUE_CLASSIFICATION,
            ISSUE_SUB_TYPE, AUTHENTICITY, SHORT_SALE_THRESHOLD,
            IPO_FLAG, LULD_REFERENCE_PRICE_TIER, ETP_FLAG,
            ETP_LEVERAGE_FACTOR, INVERSE_INDICATOR,
        ],
        0x48: [STOCK, TRADING_STATE, RESERVED, REASON],                             # 'H' Stock Trading Action
        0x59: [STOCK, REG_SHO_ACTION],                                              # 'Y' Reg SHO
        0x4C: [                                                                     # 'L' Market Participant
            MPID, PARTICIPANT_STOCK, PRIMARY_MARKET_MAKER,
            MARKET_MAKER_MODE, MARKET_PARTICIPANT_STATE,
        ],
        0x56: [LEVEL_1, LEVEL_2, LEVEL_3],                                          # 'V' MWCB Decline Level
        0x57: [BREACHED_LEVEL],                                                     # 'W' MWCB Status Level
        0x4B: [STOCK, IPO_QUOTATION_RELEASE_TIME,                                   # 'K' IPO Quoting Period
               IPO_QUOTATION_RELEASE_QUALIFIER, IPO_PRICE],
        0x4A: [STOCK, AUCTION_COLLAR_REFERENCE_PRICE, UPPER_AUCTION_COLLAR_PRICE,  # 'J' LULD Auction Collar
               LOWER_AUCTION_COLLAR_PRICE, AUCTION_COLLAR_EXTENSION],
        0x68: [STOCK, MARKET_CODE, OPERATIONAL_HALT_ACTION],                        # 'h' Operational Halt
        0x41: [ORDER_REFERENCE_NUMBER, BUY_SELL_INDICATOR, SHARES,                  # 'A' Add Order (no MPID)
               ORDER_STOCK, PRICE],
        0x46: [ORDER_REFERENCE_NUMBER, BUY_SELL_INDICATOR, SHARES,                  # 'F' Add Order MPID
               ORDER_STOCK, PRICE, ATTRIBUTION],
        0x45: [ORDER_REFERENCE_NUMBER, EXECUTED_SHARES, MATCH_NUMBER],              # 'E' Order Executed
        0x43: [ORDER_REFERENCE_NUMBER, EXECUTED_SHARES, MATCH_NUMBER,               # 'C' Executed w/ Price
               PRINTABLE, EXECUTION_PRICE],
        0x58: [ORDER_REFERENCE_NUMBER, CANCELLED_SHARES],                           # 'X' Order Cancel
        0x44: [ORDER_REFERENCE_NUMBER],                                             # 'D' Order Delete
        0x55: [ORIGINAL_ORDER_REFERENCE_NUMBER, NEW_ORDER_REFERENCE_NUMBER,         # 'U' Order Replace
               REPLACE_SHARES, REPLACE_PRICE],
        0x50: [ORDER_REFERENCE_NUMBER, BUY_SELL_INDICATOR, SHARES,                  # 'P' Trade Message
               ORDER_STOCK, PRICE, TRADE_MATCH_NUMBER],
        0x51: [CROSS_SHARES, CROSS_STOCK, CROSS_PRICE,                             # 'Q' Cross Trade
               CROSS_MATCH_NUMBER, CROSS_TYPE],
        0x42: [BROKEN_MATCH_NUMBER],                                                # 'B' Broken Trade
        0x49: [PAIRED_SHARES, IMBALANCE_SHARES, IMBALANCE_DIRECTION, NOII_STOCK,   # 'I' NOII
               FAR_PRICE, NEAR_PRICE, CURRENT_REFERENCE_PRICE,
               NOII_CROSS_TYPE, PRICE_VARIATION_INDICATOR],
        0x4E: [STOCK, INTEREST_FLAG],                                               # 'N' Retail Interest
    },
    variant_length={
        0x53: 12,   # 'S'
        0x52: 39,   # 'R'
        0x48: 25,   # 'H'
        0x59: 20,   # 'Y'
        0x4C: 26,   # 'L'
        0x56: 35,   # 'V'
        0x57: 12,   # 'W'
        0x4B: 28,   # 'K'
        0x4A: 35,   # 'J'
        0x68: 21,   # 'h'
        0x41: 36,   # 'A'
        0x46: 40,   # 'F'
        0x45: 31,   # 'E'
        0x43: 36,   # 'C'
        0x58: 23,   # 'X'
        0x44: 19,   # 'D'
        0x55: 35,   # 'U'
        0x50: 44,   # 'P'
        0x51: 40,   # 'Q'
        0x42: 19,   # 'B'
        0x49: 50,   # 'I'
        0x4E: 20,   # 'N'
    },
)
