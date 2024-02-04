-- sql scripts to set up Snowflake db, schema, stages, etc
use role accountadmin;
create database sales_db;
create schema sales_db.sales_schema;
use sales_db.sales_schema;
CREATE
OR REPLACE WAREHOUSE etl_wh WITH WAREHOUSE_SIZE = XSMALL;
use warehouse etl_wh;
create
or replace table sales_db.sales_schema.sales_summary (
    trans_dt date,
    store_key integer,
    prod_key integer,
    sum_sales_qty integer,
    load_date date
);
create
or replace stage s3_stage_sales url = 's3://phase-3-airflow-lab-bucket/output/' credentials =(
    aws_key_id = AWS_KEY_ID aws_secret_key = AWS_SECRET_KEY
);
show stages;
list @s3_stage_sales;
create
or replace file format parquet_ff type = 'parquet';
COPY INTO sales_db.sales_schema.sales_summary
FROM
    (
        SELECT
            $1:trans_dt,
            $1:store_key,
            $1:prod_key,
            $1:sum_sales_qty,
            current_date
        FROM
            @s3_stage_sales
    ) Pattern = '.*20240105.*.gz.parquet' file_format = 'parquet_ff';
select
    *
from
    sales_db.sales_schema.sales_summary
limit
    100;