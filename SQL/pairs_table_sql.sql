CREATE TABLE IF NOT EXISTS Market_Pairs(
    market varchar(100), #종목 이름 !
    collected_at datetime, #데이터베이스에 들어온 시간 !
    korean_name varchar(100), #한국 이름 !
    english_name varchar(100), #영어 이름 !
    market_event BOOLEAN #이벤트의 유무 !
    event_warning BOOLEAN, #종목 경보 여부 !
    event_caution BOOLEAN, #주의 종목 여부
    event_caution_price_fluctuations BOOLEAN, #가격급등락경보 !
    event_caution_trading_volume_soaring BOOLEAN, #거래량급증경보 !
    event_caution_deposit_amount_soaring BOOLEAN, #입금량급증경보 !
    event_caution_global_price_differences BOOLEAN, #국내외가격차이정보 !
    event_caution_concentration_of_small_accounts BOOLEAN #소수계정거래급증정보 !
);