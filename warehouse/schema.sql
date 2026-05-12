CREATE TABLE IF NOT EXISTS dim_time (
    time_id BIGINT PRIMARY KEY,
    date DATE NOT NULL,
    hour INTEGER NOT NULL,
    day INTEGER NOT NULL,
    month INTEGER NOT NULL,
    weekday VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_region (
    region_id BIGINT PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_usage (
    usage_id BIGINT PRIMARY KEY,
    time_id BIGINT NOT NULL,
    region_id BIGINT NOT NULL,
    call_count INTEGER NOT NULL,
    sms_count INTEGER NOT NULL,
    internet_mb DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (time_id) REFERENCES dim_time(time_id),
    FOREIGN KEY (region_id) REFERENCES dim_region(region_id)
);

